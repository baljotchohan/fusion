# api/main.py
"""
FastAPI application serving REST endpoints and a WebSocket server
to stream real-time agent updates to the Next.js dashboard.
"""
import os
import json
import time
import logging
import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP

from core.event_bus import event_bus
from core.band_client import mock_bus, is_mock_mode
from core.memory_graph import memory_graph
from api.state import sim_state
from api.v1 import router as v1_router
from api.oauth import router as oauth_router
from core.auth import get_uid_optional
from core.pitch_loader import _load_pitch_file
import mcp_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fusion.api")

# MCP security — set MCP_API_KEY in HF Space secrets to require a key.
# Leave unset for public access (e.g. during open hackathon judging).
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
MCP_RATE_LIMIT = int(os.getenv("MCP_RATE_LIMIT", "1000"))  # calls per hour per key/IP
_mcp_rate: dict[str, list[float]] = defaultdict(list)

# ── Remote MCP transport ─────────────────────────────────────────────────────
# Expose the same 5 committee tools as mcp_server.py (stdio) over streamable HTTP,
# mounted at /mcp, so ANY MCP client can connect to the deployed FUSION by URL.
# Tool behavior is shared via mcp_tools.dispatch — stdio and HTTP can't drift.
# streamable_http_path="/" + mount("/mcp") => the endpoint is exactly /mcp.
from mcp.server.transport_security import TransportSecuritySettings
fusion_mcp = FastMCP(
    "fusion-mcp",
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
_MCP_DESC = {t.name: t.description for t in mcp_tools.TOOLS}


@fusion_mcp.tool(description=_MCP_DESC["chat_with_managing_partner"])
async def chat_with_managing_partner(message: str) -> dict:
    return await mcp_tools.dispatch("chat_with_managing_partner", {"message": message})


@fusion_mcp.tool(description=_MCP_DESC["get_deal_record"])
async def get_deal_record(incident_id: str) -> dict:
    return await mcp_tools.dispatch("get_deal_record", {"incident_id": incident_id})


@fusion_mcp.tool(description=_MCP_DESC["get_boardroom_verdict"])
async def get_boardroom_verdict(incident_id: str) -> dict:
    return await mcp_tools.dispatch("get_boardroom_verdict", {"incident_id": incident_id})


@fusion_mcp.tool(description=_MCP_DESC["query_deal_vault"])
async def query_deal_vault(keyword: str, limit: int = 5) -> dict:
    return await mcp_tools.dispatch("query_deal_vault", {"keyword": keyword, "limit": limit})


@fusion_mcp.tool(description=_MCP_DESC["learn_risk_pattern"])
async def learn_risk_pattern(keyword: str, checklist: str, success_rate: float = 0.8) -> dict:
    return await mcp_tools.dispatch(
        "learn_risk_pattern",
        {"keyword": keyword, "checklist": checklist, "success_rate": success_rate},
    )


# Build the streamable-HTTP ASGI app once (this also creates the session manager).
_mcp_http_app = fusion_mcp.streamable_http_app()


# Active WebSocket dashboard connections keyed by uid (or "__public__" for unauthenticated)
active_websockets: dict[str, set] = defaultdict(set)

def _clear_agent_busy_flags():
    if is_mock_mode():
        for room_agents in mock_bus.rooms.values():
            for agent in room_agents:
                agent._is_busy = False


async def run_pipeline_watchdog(incident_id: str):
    """Background task that monitors the active deal and forces a partial verdict if it hangs."""
    from api.state import get_uid_for_incident
    from core.auth import current_uid, current_incident_id
    uid = get_uid_for_incident(incident_id) or "__public__"
    token_uid = current_uid.set(uid)
    token_inc = current_incident_id.set(incident_id)
    try:
        import time
        logger.info(f"Watchdog: Started for incident {incident_id}")
        # Give the simulation some time to startup
        await asyncio.sleep(5)
        while True:
            await asyncio.sleep(2)
            # If the simulation finished, or was reset, or a different deal is running, stop watchdog
            if not sim_state.running or sim_state.active_incident_id != incident_id:
                logger.info(f"Watchdog: Finished for incident {incident_id}")
                break
                
            import time
            idle_time = time.time() - sim_state.last_event_at
            # If 120s pass with no agent activity, trigger recovery. (Fast models
            # finish a partner in seconds; a 2-min idle means a genuine stall.)
            if idle_time > 120.0:
                logger.warning(f"Watchdog: Incident {incident_id} has been idle for {idle_time:.1f}s (limit: 120s). Triggering recovery.")
                await force_partial_verdict(incident_id)
                break
    finally:
        current_uid.reset(token_uid)
        current_incident_id.reset(token_inc)

async def force_partial_verdict(incident_id: str):
    """Fallback mechanism that packages available reports into a partial verdict."""
    from api.state import get_uid_for_incident
    from core.auth import current_uid, current_incident_id
    uid = get_uid_for_incident(incident_id) or "__public__"
    token_uid = current_uid.set(uid)
    token_inc = current_incident_id.set(incident_id)
    try:
        import time
        from core.memory_graph import memory_graph
        
        logger.warning(f"Watchdog: Force-completing incident {incident_id} due to inactivity.")
        
        # 1. Reset simulation running state so trigger is unblocked
        sim_state.running = False
        sim_state.deal_concluded = True
        _clear_agent_busy_flags()
        
        inc = memory_graph.get_incident(incident_id)
        if not inc:
            logger.error(f"Watchdog: Incident {incident_id} not found in memory graph — broadcasting done to unblock frontend.")
            await event_bus.broadcast("managing_partner", "done", {"report": "DECISION: PASS — committee records unavailable for this session."})
            return

        # If final decision already exists, rebroadcast it so the frontend unblocks
        if inc.get("final_decision"):
            logger.info(f"Watchdog: Incident {incident_id} already has a final decision — rebroadcasting to unblock frontend.")
            await event_bus.broadcast("managing_partner", "done", {"report": inc["final_decision"]})
            return

        # Load the pitch file
        try:
            from core.pitch_loader import _load_pitch_file
            pitch_data = _load_pitch_file() or {}
        except Exception as e:
            logger.error(f"Watchdog: Failed to load pitch file: {e}")
            pitch_data = {}

        # Run calculations
        try:
            from core.diligence_engine import run_diligence_calculations
            calc = run_diligence_calculations(pitch_data) if pitch_data else {}
        except Exception as e:
            logger.error(f"Watchdog: Failed to run diligence calculations: {e}")
            calc = {}

        company = sim_state.active_company_name or calc.get("company_name") or "Unknown Startup"
        verdict = calc.get("verdict", "PASS")
        verdict_display = "REJECT" if verdict == "PASS" else verdict
        confidence = calc.get("verdict_confidence", 80)
        evi_quality = calc.get("evidence_quality_score", 75)
        readiness = calc.get("deal_readiness_score", 70)
        readiness_status = calc.get("deal_readiness_status", "AUDITING")
        
        fin_risk = calc.get("fin_score", 5)
        leg_risk = calc.get("leg_score", 5)
        tech_risk = calc.get("tech_score", 5)
        mkt_risk = calc.get("mkt_score", 5)
        weighted_score = calc.get("weighted_score", 5.0)

        # Gather whatever findings we have from the timeline
        findings = {}
        for item in inc.get("timeline", []):
            agent = item.get("agent")
            finding = item.get("finding")
            if agent and finding:
                findings[agent] = finding

        # Build a cohesive summary report from whatever parts we have
        specialists = ["financial_partner", "legal_partner", "technical_partner", "market_partner"]
        missing_partners = [p.replace("_", " ").title() for p in specialists if p not in findings]
        
        summaries = ""
        for p in specialists:
            if p in findings:
                cleaned_name = p.replace("_", " ").title()
                summaries += f"\n#### {cleaned_name} Analysis\n{findings[p]}\n"
        if not summaries:
            summaries = "\n*(No individual partner reports completed in time. Calculated scores are based on grounded metadata)*\n"

        memo_header = ""
        if missing_partners:
            memo_header = (
                f"> [!WARNING]\n"
                f"> due diligence timeline exceeded. Active watchdog recovery forced a "
                f"partial verdict without reports from: {', '.join(missing_partners)}.\n"
            )

        report_text = f"""### FUSION INVESTMENT COMMITTEE DECISION CARD

### {company.upper()} — SERIES A EVALUATION
**DECISION: {verdict_display}**

---

### 1. DECISION SUMMARY
- **Investment Verdict**: {verdict_display}
- **Verdict Confidence**: {confidence}%
- **Evidence Quality**: {evi_quality}% (partial audit due to timeout)
- **Deal Readiness**: {readiness}% ({readiness_status})

**RISK SCORECARD:**
- Financial Risk: {fin_risk}/10
- Legal Risk: {leg_risk}/10
- Technical Risk: {tech_risk}/10
- Market Risk: {mkt_risk}/10
- **WEIGHTED SCORE**:  {weighted_score:.1f}/10

{memo_header}

### 2. PARTNER DILIGENCE SUMMARIES
{summaries}

---
— FUSION Investment Committee OS
"""

        memory_graph.set_final_decision(incident_id, report_text)
        sim_state.final_verdict_card = report_text
        sim_state.completed_agents.add("managing_partner")
        sim_state._mp_verdict_pending = True

        # Persist verdict to Firebase RTDB (fire-and-forget, non-fatal)
        try:
            from core.rtdb import write_deal, write_session
            _rtdb_uid = sim_state.active_uid or "__public__"
            ok1 = write_deal(_rtdb_uid, incident_id, {
                "companyName": company,
                "verdict": verdict_display,
                "weightedScore": weighted_score,
                "confidence": confidence,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "report": report_text[:4000],
            })
            ok2 = write_session(_rtdb_uid, incident_id, {"status": "complete", "verdict": verdict_display})
            if not ok1 or not ok2:
                logger.warning("RTDB verdict write skipped/failed (ok1=%s ok2=%s) — check FIREBASE_DATABASE_URL secret and HF Space logs", ok1, ok2)
        except Exception as e:
            logger.warning("RTDB verdict write exception: %s", e)

        # Broadcast 'done' event for managing_partner to Websockets so the frontend transitions
        await event_bus.broadcast("managing_partner", "done", {"report": report_text})
        logger.info("Watchdog: Partial verdict successfully broadcast and saved.")
    finally:
        current_uid.reset(token_uid)
        current_incident_id.reset(token_inc)


async def _run_debate_phase(incident_id: str):
    """Broadcast a visible inter-partner debate when divergent risk signals are detected."""
    from api.state import get_uid_for_incident
    from core.auth import current_uid, current_incident_id
    uid = get_uid_for_incident(incident_id) or "__public__"
    token_uid = current_uid.set(uid)
    token_inc = current_incident_id.set(incident_id)
    try:
        try:
            from core.pitch_loader import _load_pitch_file
            from core.diligence_engine import run_diligence_calculations
            calc = run_diligence_calculations(_load_pitch_file())
        except Exception:
            return

        fin = calc.get("fin_score") or 0
        leg = calc.get("leg_score") or 0
        tech = calc.get("tech_score") or 0
        mkt = calc.get("mkt_score") or 0
        contradictions = calc.get("contradictions", [])
        company = calc.get("company_name", "the company")

        scores = {"financial_partner": (fin, "Financial"), "legal_partner": (leg, "Legal"),
                  "technical_partner": (tech, "Technical"), "market_partner": (mkt, "Market")}
        sorted_scores = sorted(scores.items(), key=lambda x: x[1][0])
        low_agent, (low_score, low_label) = sorted_scores[0]
        high_agent, (high_score, high_label) = sorted_scores[-1]
        spread = high_score - low_score

        if spread < 2.0 and not contradictions:
            return  # No meaningful conflict — skip debate

        await event_bus.broadcast("managing_partner", "debate", {
            "current_action": f"🔴 INTER-PARTNER CONFLICT DETECTED — {company} shows divergent risk signals across domains. Initiating debate round...",
            "debate_type": "conflict_start",
        })
        await asyncio.sleep(0.7)

        if spread >= 2.0:
            await event_bus.broadcast(high_agent, "debate", {
                "current_action": f"⚠️ {high_label} risk at {high_score:.1f}/10 — I'm flagging material issues that cannot be dismissed. These findings directly affect deal viability.",
                "debate_type": "argument",
            })
            await asyncio.sleep(0.7)
            await event_bus.broadcast(low_agent, "debate", {
                "current_action": f"Acknowledged. {low_label} fundamentals score {low_score:.1f}/10 — sector positioning and execution capacity provide material upside. Risk may be overstated.",
                "debate_type": "rebuttal",
            })
            await asyncio.sleep(0.7)
            await event_bus.broadcast(high_agent, "debate", {
                "current_action": f"Upside noted, but {high_label} risk at this severity has historically preceded deal failures in our portfolio. Requesting conservative weighting in the final scorecard.",
                "debate_type": "counter",
            })
            await asyncio.sleep(0.6)

        if contradictions:
            contra = contradictions[0]
            await event_bus.broadcast("managing_partner", "debate", {
                "current_action": f"⚡ Data conflict logged: {contra.get('message', 'Conflicting evidence across domain reports')}. Adjusting confidence and evidence quality scores.",
                "debate_type": "conflict_detail",
            })
            await asyncio.sleep(0.5)

        await event_bus.broadcast("managing_partner", "debate", {
            "current_action": "✅ DEBATE RESOLVED — applying domain conflict weights and proceeding to final verdict synthesis...",
            "debate_type": "resolution",
        })
        await asyncio.sleep(0.4)
    finally:
        current_uid.reset(token_uid)
        current_incident_id.reset(token_inc)


async def _trigger_mp_verdict(incident_id: str):
    """Deterministically tell the Managing Partner to synthesize the final
    verdict. Fires exactly once, when all 4 specialists have reported — so the
    verdict never depends on the MP's LLM noticing completion on its own."""
    from api.state import get_uid_for_incident
    from core.auth import current_uid, current_incident_id
    uid = get_uid_for_incident(incident_id) or "__public__"
    token_uid = current_uid.set(uid)
    token_inc = current_incident_id.set(incident_id)
    try:
        # Safety net: if the MP doesn't conclude shortly, force a clean verdict.
        # Schedule it BEFORE we do any network awaits, in case the send hangs or fails.
        asyncio.create_task(_mp_verdict_safety_net(incident_id))

        # Visible debate round before synthesis — shows judges inter-agent reasoning
        await _run_debate_phase(incident_id)

        from core.memory_graph import memory_graph
        from agents.managing_partner import VERDICT_TRIGGER

        inc = memory_graph.get_incident(incident_id) or {}
        specialists = {"financial_partner", "legal_partner", "technical_partner", "market_partner"}
        findings = {}
        for item in inc.get("timeline", []):
            a = item.get("agent")
            f = item.get("finding")
            if a in specialists and f:
                findings[a] = str(f)
        summary = "\n".join(
            f"- {a.replace('_', ' ').title()}: {f[:400]}" for a, f in findings.items()
        ) or "(partner findings are logged in deal memory)"
        company = sim_state.active_company_name or "the company"
        msg = (
            f"{VERDICT_TRIGGER} All 4 partners have completed due diligence on {company}.\n\n"
            f"Partner findings:\n{summary}\n\n"
            f"Now call get_calculated_scores() and deliver the FINAL INVESTMENT COMMITTEE "
            f"DECISION card (it MUST contain 'DECISION:'), using the exact scores returned."
        )

        logger.info(f"Orchestrator: triggering Managing Partner verdict for {incident_id}.")
        try:
            if is_mock_mode():
                await mock_bus.send_message(
                    sender="FUSION-Orchestrator",
                    target_room="managing-partner-room",
                    message=msg,
                    incident_id=incident_id,
                )
            else:
                from api.v1 import dispatch_real_band_message
                await dispatch_real_band_message(msg, "managing-partner", sender_agent_name="financial_partner")
        except Exception as e:
            logger.error(f"Orchestrator: failed to trigger MP verdict: {e}")
    finally:
        current_uid.reset(token_uid)
        current_incident_id.reset(token_inc)


async def _mp_verdict_safety_net(incident_id: str):
    """If the Managing Partner hasn't produced a verdict within the window after
    being triggered, force a clean deterministic verdict (engine numbers + all 4
    partner findings are already available), so a deal can never hang."""
    from api.state import get_uid_for_incident
    from core.auth import current_uid, current_incident_id
    uid = get_uid_for_incident(incident_id) or "__public__"
    token_uid = current_uid.set(uid)
    token_inc = current_incident_id.set(incident_id)
    try:
        await asyncio.sleep(20)
        if sim_state.active_incident_id == incident_id and not sim_state.deal_concluded:
            logger.warning(
                f"Orchestrator: MP verdict not rendered within 20s for {incident_id} — forcing clean verdict."
            )
            await force_partial_verdict(incident_id)
    finally:
        current_uid.reset(token_uid)
        current_incident_id.reset(token_inc)


async def broadcast_event_to_websockets(event_data: dict):
    """Callback registered with event_bus to forward agent updates to the dashboard."""
    from core.auth import current_uid, current_incident_id
    from api.state import get_uid_for_incident
    uid = event_data.get("uid")
    incident_id = event_data.get("incident_id")

    # If uid is a system default, resolve the real owner from the incident registry
    _system_defaults = (None, "", "__public__", "__mcp_client__")
    if uid in _system_defaults and incident_id:
        uid = get_uid_for_incident(incident_id) or uid or "__public__"
    if not uid or uid in _system_defaults:
        uid = "__public__"

    token_uid = current_uid.set(uid)
    token_inc = None
    if incident_id:
        token_inc = current_incident_id.set(incident_id)
    try:
        sim_state.touch()
        # Track last-known status per agent for the chat API / MCP clients
        if event_data.get("agent"):
            sim_state.agent_statuses[event_data["agent"]] = event_data.get("status", "idle")

        # Auto-reset simulation lock ONLY when ALL 4 specialists have reported
        # AND the managing partner has delivered the final verdict. This prevents
        # the race condition where the verdict arrives before slower specialists
        # (Legal, Market) finish, killing them mid-flight.
        import re
        specialists = {"financial_partner", "legal_partner", "technical_partner", "market_partner"}

        # When any specialist finishes, check if we can now conclude
        if event_data.get("status") == "done" and event_data.get("agent") in specialists:
            # Mode-agnostic completion tracking: the event-bus 'done' is the ONE
            # chokepoint every mode passes through (mock _handle_single_message,
            # real on_message, and the mock-LLM path all broadcast it). Previously
            # completed_agents was only populated in real mode / the mock-LLM path,
            # so mock-transport + real-LLM runs never concluded and stalled to the
            # watchdog. Adding here makes completion reliable in every mode.
            sim_state.completed_agents.add(event_data["agent"])
            # Enrich the specialist "done" event with partial confidence so the
            # frontend confidence bar fills incrementally as each partner reports.
            _n_done = len(sim_state.completed_agents & specialists)
            event_data.setdefault("output", {})["partial_confidence"] = min(85, _n_done * 21)

            all_specialists_done = specialists.issubset(sim_state.completed_agents)
            mp_has_verdict = getattr(sim_state, '_mp_verdict_pending', False)
            if all_specialists_done and mp_has_verdict:
                sim_state.running = False
                sim_state.deal_concluded = True
                _clear_agent_busy_flags()
                logger.info("FastAPI: Simulation complete — all partners reported + verdict rendered.")
            elif all_specialists_done and not sim_state._mp_verdict_triggered and sim_state.active_incident_id:
                # All 4 specialists reported → deterministically trigger the Managing
                # Partner to synthesize the verdict. Never rely on the MP LLM to
                # notice on its own (that under-fired and stalled deals).
                sim_state._mp_verdict_triggered = True
                logger.info("FastAPI: All 4 specialists done — triggering Managing Partner verdict synthesis.")
                asyncio.create_task(_trigger_mp_verdict(sim_state.active_incident_id))

        if event_data.get("agent") == "managing_partner" and event_data.get("status") == "done":
            output_data = event_data.get("output") or {}
            report_text = output_data.get("report") or ""
            if re.search(r"DECISION:", report_text, re.I):
                # Attach the authoritative score/verdict/confidence as STRUCTURED fields so
                # the dashboard never has to scrape the free-form report text (which a real
                # LLM does not format reliably). This is what makes the weighted risk score
                # show up the moment the committee concludes, in every run mode.
                try:
                    from api.v1 import compute_deal_snapshot
                    snap = compute_deal_snapshot(sim_state.active_uid, sim_state.active_incident_id)
                    output_data["weighted_score"] = snap.get("weighted_score")
                    output_data["verdict"] = snap.get("verdict")
                    output_data["confidence"] = snap.get("confidence")
                    event_data["output"] = output_data
                except Exception as e:
                    logger.warning(f"FastAPI: could not enrich verdict broadcast: {e}")
                # Record that the MP has a verdict ready
                sim_state._mp_verdict_pending = True
                all_specialists_done = specialists.issubset(sim_state.completed_agents)
                if all_specialists_done:
                    sim_state.running = False
                    sim_state.deal_concluded = True
                    _clear_agent_busy_flags()
                    logger.info("FastAPI: Simulation complete — all partners reported + verdict rendered.")
                else:
                    missing = specialists - sim_state.completed_agents
                    logger.info(f"FastAPI: Verdict received but still waiting on: {missing} — NOT concluding yet.")
            else:
                # Awaiting specialist findings, do not clear running state yet
                pass

        # An 'alert' means an agent died even after LLM fallback — release the
        # trigger lock so the next Simulate click starts a fresh run instead of
        # being ignored forever.
        if event_data.get("status") == "alert" and sim_state.running:
            sim_state.running = False
            _clear_agent_busy_flags()
            logger.warning("FastAPI: Agent error broke the chain — simulation lock released.")

        targets = active_websockets.get(uid, set())
        if not targets:
            return

        message = json.dumps(event_data)
        dead = set()
        for ws in list(targets):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                dead.add(ws)
        for ws in dead:
            active_websockets[uid].discard(ws)
    finally:
        current_uid.reset(token_uid)
        if token_inc:
            current_incident_id.reset(token_inc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Register the event bus listener on application startup
    event_bus.register_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener registered.")

    # Probe RTDB so any misconfiguration shows up immediately in HF Space logs
    from core.rtdb import probe as rtdb_probe
    _rtdb_status = rtdb_probe()
    if _rtdb_status == "ok":
        logger.info("Firebase RTDB probe ✓ — writes enabled")
    else:
        logger.warning("Firebase RTDB probe FAILED: %s", _rtdb_status)
    
    # The MCP session manager must run for the mounted /mcp app to serve requests.
    async with fusion_mcp.session_manager.run():
        logger.info("🔌 FUSION MCP streamable-HTTP transport live at /mcp")
        yield
        
    # Unregister the listener on application shutdown
    event_bus.unregister_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener unregistered.")


app = FastAPI(title="FUSION API", version="1.0.0", lifespan=lifespan, redirect_slashes=False)
app.include_router(v1_router)
app.include_router(oauth_router)  # OAuth 2.0 at root: /.well-known/, /oauth/*


@app.api_route("/mcp", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def _mcp_slash_redirect(request: Request):
    # HF Space's built-in redirect goes to http://internal-host — rejected with 421.
    # We intercept /mcp here and issue a 308 to the correct public HTTPS /mcp/ URL.
    # 308 preserves the request method (POST stays POST) so mcp-remote reconnects correctly.
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")
    proto = request.headers.get("x-forwarded-proto", "https" if "localhost" not in host else "http")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{proto}://{host}/mcp/", status_code=308)


app.mount("/mcp", _mcp_http_app)

# Enable CORS for the Next.js War Room dashboard
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def set_request_context(request: Request, call_next):
    """Set the thread-local request context ContextVars for auth and data-isolation."""
    uid = "__public__"
    username = "guest"
    
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        token = request.query_params.get("token", "").strip()

    if token:
        if token.startswith("fus_"):
            # Per-user MCP API key: fus_<firebase_uid> — set by Settings page, passed in MCP client headers
            from core.auth import verify_uid_signature
            verified_uid = verify_uid_signature(token)
            if verified_uid:
                uid = verified_uid
                username = uid
            else:
                uid = "__public__"
                username = "guest"
        elif MCP_API_KEY and token == MCP_API_KEY:
            uid = "global_mcp_user"
            username = "global_mcp_user"
        else:
            try:
                from firebase_admin import auth as fb_auth
                decoded = fb_auth.verify_id_token(token)
                uid = decoded["uid"]
                email = decoded.get("email")
                username = decoded.get("name") or (email.split("@")[0] if email else None) or uid
            except Exception:
                pass
        from core.auth import current_token
        current_token.set(token)
    else:
        from core.auth import _AUTH_DISABLED
        if _AUTH_DISABLED:
            uid = request.headers.get("X-Dev-UID", "dev-user")
            username = uid
        else:
            uid = request.headers.get("X-Dev-UID") or "__public__"
            username = uid

    from core.auth import current_uid, current_username
    current_uid.set(uid)
    current_username.set(username)

    return await call_next(request)


@app.middleware("http")
async def mcp_security(request: Request, call_next):
    """Auth check and rate-limit for every request touching /mcp or /mcp/."""
    if not request.url.path.startswith("/mcp"):
        return await call_next(request)

    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    # Personal fus_<uid> key: signed-in users get unlimited MCP access, no auth gate
    if token.startswith("fus_") and len(token) > 4:
        from core.auth import verify_uid_signature
        if verify_uid_signature(token):
            return await call_next(request)

    # Global API key guard (when MCP_API_KEY is configured)
    if MCP_API_KEY and token != MCP_API_KEY:
        # RFC 9728: point the client at our protected-resource metadata so OAuth
        # clients (mcp-remote, claude.ai, ChatGPT) can discover the auth server.
        _proto = request.headers.get("x-forwarded-proto", "https")
        _host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "baljot07-fusion.hf.space"
        _rm = f"{_proto}://{_host}/.well-known/oauth-protected-resource"
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32001,
                "message": "Unauthorized — sign in at https://baljot07-fusion.hf.space and get your key from Settings → MCP."
            }},
            status_code=401,
            headers={"WWW-Authenticate": f'Bearer realm="FUSION MCP", resource_metadata="{_rm}"'},
        )

    # Rate limit anonymous / global-key callers — doubled from default
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() \
         or (request.client.host if request.client else "unknown")
    bucket = f"key:{token[:12]}" if token else f"ip:{ip}"
    now = time.time()
    window = _mcp_rate[bucket] = [t for t in _mcp_rate[bucket] if now - t < 3600]
    limit = MCP_RATE_LIMIT  # 1,000/hr for anonymous; signed-in users bypass entirely above
    if len(window) >= limit:
        wait = int(3600 - (now - window[0]))
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32029,
                "message": f"Rate limit: {limit} MCP calls/hour. Resets in {wait // 60}m {wait % 60}s. Sign in for unlimited access."
            }},
            status_code=429,
            headers={"Retry-After": str(wait)},
        )
    _mcp_rate[bucket].append(now)

    return await call_next(request)



# ─── REST ENDPOINTS ───────────────────────────────────────────

class TriggerResponse(BaseModel):
    status: str
    message: str
    mode: str

@app.post("/api/trigger-attack", response_model=TriggerResponse)
async def trigger_attack(request: Request):
    """Compatibility wrapper that triggers the FUSION deal review."""
    res = await trigger_deal(request=request)
    return TriggerResponse(
        status=res.get("status", "error"),
        message=res.get("message", ""),
        mode=res.get("mode", "mock")
    )

_last_trigger: dict[str, float] = {}  # uid → epoch seconds of last trigger

@app.post("/api/trigger-deal")
async def trigger_deal(request: Request, company: Optional[str] = None, raise_amount: str = "$10M"):
    """Triggers the FUSION investment committee on a deal."""
    import time as _time

    # ── Set uid into ContextVar FIRST so all sim_state access is per-user ──
    # If uid is set after the running check, all concurrent users share the
    # __mcp_client__ namespace and block each other with already_running.
    uid = await get_uid_optional(request)
    from core.auth import current_uid as _cuid
    _cuid.set(uid or "__public__")

    if sim_state.is_stale(max_idle_seconds=300):
        sim_state.reset()
        _clear_agent_busy_flags()

    if sim_state.running:
        return {"status": "already_running", "message": "Committee already in session.", "mode": "mock" if is_mock_mode() else "real"}

    # Signed-in users: no cooldown, no session limit — full access
    # Anonymous demo users: 2 committee sessions per week
    from api.state import count_sessions_this_week, record_session as _record_session
    if not uid:
        _client_ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (request.client.host if request.client else "unknown")
        _sess_key = f"anon:{_client_ip}"
        _sess_used = count_sessions_this_week(_sess_key)
        if _sess_used >= 14:
            return {"status": "session_limit", "message": "Demo limit reached (14 sessions/week). Sign in for unlimited access.", "used": _sess_used, "limit": 14, "mode": "mock" if is_mock_mode() else "real"}
        _record_session(_sess_key)

    try:
        from core.demo_registry import resolve_pitch_file
        from core.pitch_loader import resolve_uploaded_pitch, _company_name_of, _load_pitch_file
        import uuid

        new_deal_id = f"DEAL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        resolved_pitch = resolve_pitch_file(company) if company else None
        if resolved_pitch:
            deal_id = new_deal_id
            resolved_company = company
            logger.info(f"trigger-deal: resolved demo '{company}' → pitch file {resolved_pitch}")
        else:
            up_file, up_incident = resolve_uploaded_pitch(company)
            if up_file:
                # Reuse the uploaded incident so the report ties back to the upload.
                deal_id = up_incident or new_deal_id
                resolved_pitch = up_file
                resolved_company = company or _company_name_of(_load_pitch_file(up_file)) or "Uploaded Deal"
                logger.info(f"trigger-deal: '{company}' → uploaded pitch {up_file} (incident {deal_id})")
            else:
                deal_id = new_deal_id
                resolved_pitch = None  # loader falls back to the default pitch
                resolved_company = company or "NovaPay Inc"
                logger.info(f"trigger-deal: no demo/upload match for '{company}' → default pitch")
    except Exception as e:
        logger.error(f"trigger-deal: failed to resolve pitch: {e}")
        import uuid
        deal_id = f"DEAL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        resolved_pitch = None
        resolved_company = company or "NovaPay Inc"

    # Set ContextVar for incident ID BEFORE any sim_state write
    from core.auth import current_incident_id as _cinc
    _cinc.set(deal_id)

    # Register incident → uid mapping so event broadcasts resolve the correct
    # user namespace even when ContextVars are lost across asyncio task boundaries.
    from api.state import register_incident_uid as _reg_inc
    _reg_inc(deal_id, uid or "__public__")

    # Reset simulation state and agent flags for a fresh run (writes to "{uid}:{deal_id}")
    sim_state.reset()
    _clear_agent_busy_flags()

    sim_state.active_uid = uid
    sim_state.running = True
    sim_state.touch()
    sim_state.active_pitch_file = resolved_pitch
    sim_state.active_company_name = resolved_company
    sim_state.active_incident_id = deal_id

    # Extract display name from Firebase token for agent context + Firestore profile
    if uid:
        try:
            import firebase_admin.auth as _fb_auth
            tok = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            _decoded = _fb_auth.verify_id_token(tok)
            sim_state.active_user_name = _decoded.get("name") or (_decoded.get("email", "").split("@")[0] or None)
            # Fire-and-forget Firestore update (non-blocking, non-fatal)
            from core.firestore_profile import upsert_user, increment_deal_count
            upsert_user(uid, sim_state.active_user_name, _decoded.get("email"), _decoded.get("picture"))
            increment_deal_count(uid)
            from core.rtdb import upsert_profile
            upsert_profile(uid, sim_state.active_user_name, _decoded.get("email"), _decoded.get("picture"))
        except Exception:
            pass

    try:
        from core.pitch_loader import clear_pitch_cache
        company = sim_state.active_company_name
        memory_graph.create_incident(deal_id, {"trigger": "pitch_submission", "company": company})
        sim_state.dispatched_deals.clear()   # fresh run — nothing dispatched yet
        clear_pitch_cache()

        # Memory match: if prior completed deals exist, surface the pattern match
        try:
            _past_inc = memory_graph._read_file(memory_graph.incidents_file)
            _completed = [(pid, pinc) for pid, pinc in _past_inc.items()
                          if pid != deal_id and pinc.get("final_decision")]
            if _completed:
                _best = max(_completed, key=lambda x: x[1].get("created_at", ""))
                _past_co = _best[1].get("metadata", {}).get("company", "a prior evaluation")
                async def _emit_mm(_co=_past_co, _did=_best[0]):
                    await asyncio.sleep(1.5)
                    await event_bus.broadcast("managing_partner", "memory_match", {
                        "current_action": f"⚡ Memory match — risk patterns from {_co} evaluation loaded. Cross-referencing learned committee patterns...",
                        "matched_deal": _did,
                        "matched_company": _co,
                    })
                asyncio.create_task(_emit_mm())
        except Exception:
            pass

        # RTDB: log session start (fire-and-forget)
        try:
            from core.rtdb import write_session, write_activity
            _rtdb_uid = uid or "__public__"
            ok = write_session(_rtdb_uid, deal_id, {
                "companyName": company,
                "status": "running",
                "startedAt": datetime.now(timezone.utc).isoformat(),
            })
            write_activity(_rtdb_uid, "deal_triggered", {"dealId": deal_id, "company": company})
            if not ok:
                logger.warning("RTDB session write skipped/failed — check FIREBASE_DATABASE_URL secret and HF Space logs")
        except Exception as e:
            logger.warning("RTDB session write exception: %s", e)

        _submitter = f" Submitted by {sim_state.active_user_name}." if sim_state.active_user_name else ""
        brief = f"New deal submitted for committee review: {company} — Series A, {raise_amount} raise.{_submitter} Full pitch data is loaded in the deal brief. Please convene the investment committee and begin due diligence."

        # Start the watchdog background task and track start time
        import time
        sim_state.started_at = time.time()
        asyncio.create_task(run_pipeline_watchdog(deal_id))

        if is_mock_mode():
            # Deterministic fan-out: dispatch the brief DIRECTLY to all 4 specialists
            # in parallel. We no longer rely on the Managing Partner's LLM to
            # @-mention them (that under-fired and dropped agents). The MP is gated
            # and only synthesizes once all 4 report (see _trigger_mp_verdict).
            await event_bus.broadcast("managing_partner", "working", {
                "current_action": f"Convening committee on {company} — briefing all 4 partners"
            })
            specialist_rooms = {
                "Financial": "finance-partner-room",
                "Legal": "legal-partner-room",
                "Technical": "tech-partner-room",
                "Market": "market-partner-room",
            }
            for domain, room in specialist_rooms.items():
                partner_brief = (
                    f"New deal in committee: {company} — Series A, {raise_amount} raise. "
                    f"Full pitch data is loaded in the deal brief. Run your {domain} due "
                    f"diligence now (use load_deal_brief and get_red_flags), then post "
                    f"'{domain.upper()} ANALYSIS COMPLETE' with your risk score and top red flags."
                )
                await mock_bus.send_message(
                    sender="Managing-Partner",
                    target_room=room,
                    message=partner_brief,
                    incident_id=deal_id,
                )
            return {"status": "success", "message": f"Deal '{company}' submitted to committee (Mock Mode).", "deal_id": deal_id, "mode": "mock"}
        else:
            from api.v1 import dispatch_real_band_message
            # Broadcast the MP event so the dashboard shows activity
            await event_bus.broadcast("managing_partner", "working", {
                "current_action": f"Convening committee on {company} — briefing all 4 partners"
            })
            # Step 1 — Tell the MP to convene only (NOT synthesize yet).
            # Synthesis is triggered by the orchestrator after all 4 specialists report.
            convene_msg = (
                f"CONVENE ONLY — do NOT produce a verdict yet. "
                f"New deal received: {company} — Series A, {raise_amount} raise. "
                f"Announce to the room that the committee is now in session and you are "
                f"dispatching the 4 partners for independent due diligence. "
                f"Reply with a short 2-3 sentence acknowledgement only. "
                f"The orchestrator will call you for synthesis once all partner reports are in."
            )
            await dispatch_real_band_message(convene_msg, "managing-partner", sender_agent_name="financial_partner")

            # Step 2 — Fan out directly to all 4 specialists (same as mock mode).
            specialist_briefs = [
                ("financial-partner", "Financial"),
                ("legal-partner", "Legal"),
                ("technical-partner", "Technical"),
                ("market-partner", "Market"),
            ]
            room_map = {
                "financial-partner": "finance-partner-room",
                "legal-partner": "legal-partner-room",
                "technical-partner": "tech-partner-room",
                "market-partner": "market-partner-room",
            }
            dispatched = 0
            for handle, domain in specialist_briefs:
                partner_brief = (
                    f"New deal in committee: {company} — Series A, {raise_amount} raise. "
                    f"Full pitch data is loaded in the deal brief. Run your {domain} due "
                    f"diligence now (use load_deal_brief and get_red_flags), then post "
                    f"'{domain.upper()} ANALYSIS COMPLETE' with your risk score and top 3 red flags."
                )
                sp_ok = await dispatch_real_band_message(partner_brief, handle, sender_agent_name="managing_partner")
                if sp_ok:
                    dispatched += 1
                else:
                    await mock_bus.send_message(sender="Managing-Partner", target_room=room_map[handle], message=partner_brief, incident_id=deal_id)
            if dispatched > 0:
                return {"status": "success", "message": f"Deal '{company}' submitted to committee ({dispatched}/4 specialists via real Band).", "deal_id": deal_id, "mode": "real"}
            else:
                logger.warning("All real Band specialist dispatches failed, falling back to mock bus")
                await mock_bus.send_message(sender="Managing-Partner", target_room="managing-partner-room", message=brief, incident_id=deal_id)
                return {"status": "success", "message": f"Deal '{company}' submitted (mock fallback).", "deal_id": deal_id, "mode": "mock_fallback"}
    except Exception as e:
        sim_state.running = False
        logger.error(f"trigger-deal: unexpected error, run lock released: {e}")
        raise


@app.get("/api/status")
async def get_status(request: Request):
    """Basic health check and configuration status."""
    uid = await get_uid_optional(request)

    # Set ContextVar so sim_state._get_state() uses the correct per-user partition.
    from core.auth import current_uid as _cuid
    _token = _cuid.set(uid or "__public__")
    try:
        user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
        # Only expose live sim state to the user who triggered the current session
        is_my_session = (sim_state.active_uid == uid) if uid else (sim_state.active_uid is None)
        return {
            "status": "healthy",
            "mock_mode": is_mock_mode(),
            "registered_rooms": list(mock_bus.rooms.keys()) if is_mock_mode() else [],
            "simulation_running": sim_state.running if is_my_session else False,
            "active_incident_id": sim_state.active_incident_id if is_my_session else None,
            "memory_incidents": user_memory.get_memory_stats()["total_incidents"],
            "agent_statuses": dict(sim_state.agent_statuses) if is_my_session else {},
            "completed_agents": list(sim_state.completed_agents) if is_my_session else [],
            "deal_concluded": sim_state.deal_concluded if is_my_session else False,
        }
    finally:
        _cuid.reset(_token)

@app.get("/api/rtdb-test")
async def rtdb_test():
    """Write a timestamped test record to /diagnostics/probe_tests and return the result."""
    from core.rtdb import probe, _ref, _now
    status = probe()
    if status != "ok":
        return {"rtdb": "FAILED", "reason": status}
    ref = _ref(f"/diagnostics/probe_tests")
    try:
        ref.push({"timestamp": _now(), "source": "api/rtdb-test", "message": "RTDB write confirmed ✓"})
        return {"rtdb": "ok", "message": "Test record written to /diagnostics/probe_tests in Firebase"}
    except Exception as e:
        return {"rtdb": "FAILED", "reason": str(e)}


@app.get("/mcp-connect")
async def mcp_connect_info():
    """Returns copy-paste MCP connection instructions for every client type."""
    base = os.environ.get("FUSION_PUBLIC_URL", "http://localhost:8000")
    mcp_url = f"{base}/mcp"
    return {
        "mcp_url": mcp_url,
        "smithery": "https://smithery.ai/server/@baljotchohan/fusion-vc",
        "claude_code": f"claude mcp add fusion-vc --transport http {mcp_url}",
        "claude_desktop": {
            "mcpServers": {
                "fusion-vc": {"command": "npx", "args": ["mcp-remote", mcp_url]}
            }
        },
        "cursor": {
            "mcpServers": {
                "fusion-vc": {"url": mcp_url, "transport": "http"}
            }
        },
        "tools": [
            "chat_with_managing_partner",
            "get_deal_record",
            "get_boardroom_verdict",
            "query_deal_vault",
            "learn_risk_pattern",
        ],
    }


@app.post("/api/reset")
async def reset_simulation(request: Request):
    """Resets the simulation state so a new attack can be triggered."""
    uid = await get_uid_optional(request)
    # Only the user who owns the current session (or any caller if no session is active) may reset.
    if sim_state.active_uid and uid != sim_state.active_uid:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only the session owner may reset the committee.")
    sim_state.reset()
    # Clear all agent busy flags so they're ready for the next run
    if is_mock_mode():
        for room_agents in mock_bus.rooms.values():
            for agent in room_agents:
                agent._is_busy = False
    logger.info("FastAPI: Simulation state reset. Ready for next run.")
    return {"status": "reset", "message": "Simulation state cleared. Ready for next run."}

@app.post("/api/force-verdict")
async def api_force_verdict(request: Request, incident_id: Optional[str] = None):
    """Force rendering a partial verdict for a stalled deal."""
    from fastapi import HTTPException
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    target_id = incident_id or sim_state.active_incident_id or user_memory.get_latest_incident_id()
    if not target_id:
        raise HTTPException(status_code=400, detail="No active or past incident found to force verdict.")
    await force_partial_verdict(target_id)
    return {"status": "success", "message": f"Partial verdict forced successfully for incident {target_id}."}

# ─── MOCK LLM ENDPOINT ───────────────────────────────────────

def _build_response(body: dict, content: str, tool_calls: list):
    """Build a mock OpenAI chat completion response (streaming or non-streaming)."""
    if body.get("stream"):
        import time as _time
        from fastapi.responses import StreamingResponse

        async def _gen():
            chunk = {
                "id": "chatcmpl-noop",
                "object": "chat.completion.chunk",
                "created": int(_time.time()),
                "model": "mock-model",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            chunk["choices"] = [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")
    return JSONResponse({"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": None}, "finish_reason": "stop"}]})

@app.post("/mock-llm/chat/completions")
async def mock_llm_completions(request: Request):
    """Offline mock OpenAI LLM server that simulates FUSION agent reasoning and boardroom handoffs."""
    from core.auth import current_uid, current_incident_id
    uid_header = request.headers.get("X-FUSION-UID")
    inc_header = request.headers.get("X-FUSION-Incident-ID")
    if uid_header:
        current_uid.set(uid_header)
    if inc_header:
        current_incident_id.set(inc_header)

    body = await request.json()
    messages = body.get("messages", [])
    tools = body.get("tools", [])

    # Extract system prompt and user input
    system_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
    user_msg = user_msgs[-1] if user_msgs else ""

    # Infer calling agent (check custom headers first)
    agent_name = request.headers.get("x-agent-name", "")
    if not agent_name:
        model = body.get("model", "")
        if model.startswith("mock-") and model != "mock-model":
            agent_name = model[5:]

    if not agent_name:
        import re
        _marker = re.search(r"\[ARGUS_AGENT:\s*([a-z_]+)\]", system_msg)
        agent_name = _marker.group(1) if _marker else ""
        if agent_name:
            pass
        elif "Managing Partner" in system_msg or "managing_partner" in system_msg:
            agent_name = "managing_partner"
        elif "Financial Partner" in system_msg or "financial_partner" in system_msg:
            agent_name = "financial_partner"
        elif "Legal Partner" in system_msg or "legal_partner" in system_msg:
            agent_name = "legal_partner"
        elif "Technical Partner" in system_msg or "technical_partner" in system_msg:
            agent_name = "technical_partner"
        elif "Market Partner" in system_msg or "market_partner" in system_msg:
            agent_name = "market_partner"

    if not agent_name:
        # Fallback keyword checks
        all_text = (system_msg + "\n" + user_msg).lower()
        if "financial" in all_text or "finance" in all_text:
            agent_name = "financial_partner"
        elif "legal" in all_text or "law" in all_text:
            agent_name = "legal_partner"
        elif "technical" in all_text or "tech" in all_text:
            agent_name = "technical_partner"
        elif "market" in all_text:
            agent_name = "market_partner"
        else:
            agent_name = "managing_partner"

    response_content = ""
    tool_calls = []
    available_tool_names = [t.get("function", {}).get("name", "") for t in tools] if tools else []
    logger.info(f"[{agent_name}] Mock LLM received tools: {available_tool_names}")

    # ── LOOP PREVENTION ──────────────────────────────────────────
    # Only block an agent if IT ITSELF has already completed for this deal.
    # Do NOT block specialists based on deal_concluded — they must be
    # allowed to finish their work even if the managing partner verdict
    # arrived early (race condition fix).
    if agent_name in sim_state.completed_agents:
        if agent_name == "managing_partner":
            logger.info(f"[managing_partner] Verdict already rendered — returning no-op")
        else:
            logger.info(f"[{agent_name}] Already completed for this deal — returning no-op")
        return _build_response(body, f"{agent_name}: Analysis already submitted. Standing by.", [])
    # ─────────────────────────────────────────────────────────────

    last_msg = messages[-1] if messages else {}
    last_role = last_msg.get("role", "")
    has_tool_messages = last_role in ("tool", "function")

    # ── Realistic pacing delays ────────────────────────────────────────────────
    # Tightened for a fast, deterministic run: a full 5-partner committee lands in
    # ~4-7s (×ARGUS_MOCK_PACE) while still reading as sequential deliberation.
    STAGE1_DELAYS = {
        "managing_partner":    (0.4, 0.8),
        "financial_partner":   (0.6, 1.0),
        "legal_partner":       (0.6, 1.0),
        "technical_partner":   (0.7, 1.2),
        "market_partner":      (0.6, 1.0),
    }
    STAGE2_DELAYS = {
        "managing_partner":    (0.7, 1.2),
        "financial_partner":   (0.4, 0.8),
        "legal_partner":       (0.4, 0.8),
        "technical_partner":   (0.5, 1.0),
        "market_partner":      (0.4, 0.8),
    }

    delay_range = (STAGE2_DELAYS if has_tool_messages else STAGE1_DELAYS).get(
        agent_name, (0.4, 0.8)
    )
    pace = float(os.getenv("ARGUS_MOCK_PACE", "0.2"))
    await asyncio.sleep(random.uniform(*delay_range) * pace)
    # ──────────────────────────────────────────────────────────────────────────

    # ── Dynamic evidence-backed reports ──
    from core.pitch_loader import _load_pitch_file
    from core.diligence_engine import (
        run_diligence_calculations, get_citation, format_red_flags
    )
    
    pitch_data = _load_pitch_file()
    calc = run_diligence_calculations(pitch_data)
    
    company_name = calc["company_name"]
    raise_amount = calc["raise_amount"]
    valuation = calc["valuation"]
    
    arr = calc["arr"]
    burn = calc["burn"]
    runway = calc["runway"]
    gross_margin = calc["gross_margin"]
    customers = calc["customers"]
    
    litigation = calc["litigation"]
    compliance = calc["compliance"]
    
    stack = calc["stack"]
    security = calc["security"]
    
    tam = calc["tam"]
    competition = calc["competition"]
    
    fin_flags = calc["fin_flags"]
    leg_flags = calc["leg_flags"]
    tech_flags = calc["tech_flags"]
    mkt_flags = calc["mkt_flags"]
    
    fin_score = calc["fin_score"]
    leg_score = calc["leg_score"]
    tech_score = calc["tech_score"]
    mkt_score = calc["mkt_score"]
    
    fin_rec = calc["fin_rec"]
    leg_rec = calc["leg_rec"]
    tech_rec = calc["tech_rec"]
    mkt_rec = calc["mkt_rec"]
    
    # Generate dynamic partner reports
    if "neuraldx" in company_name.lower():
        # Rich, detailed, non-compressed reports for NeuralDx
        fin_report = (
            f"FINANCIAL DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Financial Analysis\n"
            f"Confidence: {arr.get('confidence', 80)}%\n\n"
            f"EXECUTIVE SUMMARY:\n"
            f"NeuralDx presents severe financial risks characterized by critical runway, extreme customer concentration, unsustainable unit economics, and significant revenue recognition inflation.\n\n"
            f"REVENUE ANALYSIS & NIH GRANT INFLATION:\n"
            f"- Reported ARR: {get_citation(arr, 'Financials')}\n"
            f"- Net monthly burn: {get_citation(burn, 'Financials')}\n"
            f"- Cash on Hand: $6,020,000, leaving a critical runway of {get_citation(runway, 'Financials')}\n"
            f"- Gross Margin: {get_citation(gross_margin, 'Financials')}\n\n"
            f"Although YoY growth is claimed at 345%, organic YoY growth is only 148%. The claimed Q4 2025 ARR of $9.4M was artificially inflated by a $3.1M one-time, non-recurring NIH STRIDES Initiative grant (33% of ARR) and early recognition of a $1.1M one-time implementation fee from Mayo Clinic (which was contractually deferred until Q1 2026). Excluding these, organic Q4 2025 ARR is $5.2M.\n\n"
            f"AUDITOR EMPHASIS-OF-MATTER & RESTATEMENT RISK:\n"
            f"The company's auditor, Grant Thornton, issued an emphasis-of-matter paragraph in the FY2025 audit report questioning the revenue recognition of the NIH grant. Recognizing the full $3.1M in Q4 2025 violates milestone-based recognition principles. If forced to restate, $1.8M–$2.1M of Q4 2025 revenue must be deferred over 18 months, leading to a material restatement.\n\n"
            f"CUSTOMER CONCENTRATION & AT-RISK ACCOUNTS:\n"
            f"Top 2 customers account for 76% of ARR:\n"
            f"1. Penn Medicine (42% of ARR, $5.8M ARR): Contract expires Jan 2027. Penn has opened a competitive RFP and is evaluating Aidoc and Microsoft Nuance. Furthermore, NeuralDx has dropped below the contractually mandated 92% sensitivity threshold (live monitoring shows 89.4%), triggering Penn's right to renegotiate or terminate on 90 days' notice.\n"
            f"2. Mayo Clinic (34% of ARR, $4.7M ARR): Currently on a month-to-month pilot. Mayo's internal AI team has developed an in-house model achieving 91.2% sensitivity and is formally evaluating 'build vs buy', presenting immediate 30-day termination risk.\n\n"
            f"UNIT ECONOMICS & LTV:CAC BREAKDOWN:\n"
            f"At the scan level, the unit economics are unsustainable. At $0.85/scan, COGS is $0.43 (comprising $0.31 AWS inference on EOL V100 GPUs, $0.08 radiologist check labor, and $0.04 Datadog monitoring), leaving 49% gross profit ($0.42/scan). CAC is $380,000 with a 3-year contract LTV of $379,440, yielding an unsustainable LTV:CAC ratio of 1.0x with zero margin for support, churn, or pricing pressure.\n"
        )
        if calc.get("questions") and calc["questions"].get("ceo"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["ceo"])
            fin_report += f"\n❓ AUTO-GENERATED VC DILIGENCE QUESTIONS (CEO):\n{qs}\n"
        
        fin_score_display = f"{fin_score:.1f}/10" if fin_score is not None else "N/A"
        fin_report += (
            f"\n🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(fin_flags)}\n\n"
            f"FINANCIAL RISK SCORE: {fin_score_display}\n"
            f"RECOMMENDATION: {fin_rec}"
        )

        leg_report = (
            f"LEGAL DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Legal Analysis\n"
            f"Confidence: {litigation.get('confidence', 80)}%\n\n"
            f"EXECUTIVE SUMMARY:\n"
            f"NeuralDx faces critical legal exposures including active patent inventorship litigation, severe FDA compliance and off-label marketing violations, potential HIPAA exposure with a BAA gap, and labor misclassification.\n\n"
            f"IP LITIGATION & CORE PATENT DISPUTE:\n"
            f"The company's core intellectual property is under threat. Prakash Raman and Yevgenia Koval (former ML engineers who departed in Q2 2023) have filed a lawsuit in Delaware Chancery Court (Case #2023-0441-MTZ) claiming co-inventorship of the core 3D-CNN nodule detection algorithm (US Patent Application 17/884,212). They seek correction of inventorship, a 30% equity stake in the patent, and $14.5M in damages. Outside counsel (Wilson Sonsini) assesses a high 35-40% probability of an adverse outcome, which would result in disputed patent ownership and an injunction on commercial deployment. This litigation was not disclosed in the Series B pitch deck. [Grounding: Legal -> {get_citation(litigation, 'Legal')}]\n\n"
            f"FDA COMPLIANCE & OFF-LABEL MARKETING:\n"
            f"NeuralDx is actively commercializing and marketing 4 indications for which it has no FDA clearance:\n"
            f"- Liver lesion characterization (not cleared)\n"
            f"- Pulmonary Embolism (PE) detection on CTPA (not cleared; FDA warning letters issued to competitors for this exact off-label use)\n"
            f"- Intracranial hemorrhage on head CT (not cleared)\n"
            f"- Pneumothorax on chest X-ray (not cleared; different modality requiring separate 510(k))\n"
            f"Its only cleared indication is lung nodule detection (K221847). Informal FDA inquiries were received in Jan and Mar 2026. A formal Warning Letter would freeze commercial procurement. [Grounding: Legal -> {get_citation(compliance, 'Legal')}]\n\n"
            f"HIPAA COMPLIANCE & DATA BREACH HISTORY:\n"
            f"- Datadog BAA Gap: NeuralDx transmits production performance logs containing patient MRN and scan metadata to Datadog without a signed Business Associate Agreement (BAA). Since production launch in 2021, this potential HIPAA breach affects ~180,000 patient records, exposing the company to reportable OCR violations and civil penalties.\n"
            f"- Minnesota PACS Incident: In Feb 2026, a PACS integration bug at North Memorial Health caused NeuralDx's system to write AI outputs to wrong patient records for 43 patients. A HIPAA breach notification has been filed with HHS.\n\n"
            f"LABOR & EMPLOYMENT COMPLIANCE:\n"
            f"Out of 17 independent contractors (11 in India, 6 in Ukraine/Poland), 8 have worked exclusively for NeuralDx for 24+ months under daily supervision, daily standups, and company-issued equipment. This constitutes a severe contractor misclassification risk under the Indian Contract Labour Act and the IRS SS-8 test.\n\n"
            f"REGULATORY ETHICS & SEC/409A SCRUTINY:\n"
            f"- Thomas Huang FDA Recusal: Head of Regulatory Affairs Thomas Huang was the FDA reviewer on competitor Aidoc's product before joining NeuralDx. No formal recusal review under 21 CFR Part 19 has been performed.\n"
            f"- 409A Discrepancy: A 2.3x gap between the March 2026 common stock FMV ($2.10) and Series B proposed $4.91 (implied) exposes the company to IRS underpricing penalties.\n"
        )
        if calc.get("questions") and calc["questions"].get("legal"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["legal"])
            leg_report += f"\n❓ AUTO-GENERATED VC DILIGENCE QUESTIONS (Legal Counsel):\n{qs}\n"
            
        leg_score_display = f"{leg_score:.1f}/10" if leg_score is not None else "N/A"
        leg_report += (
            f"\n🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(leg_flags)}\n\n"
            f"LEGAL RISK SCORE: {leg_score_display}\n"
            f"RECOMMENDATION: {leg_rec}"
        )

        tech_report = (
            f"TECHNICAL DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Technical Audit\n"
            f"Confidence: {stack.get('confidence', 80)}%\n\n"
            f"EXECUTIVE SUMMARY:\n"
            f"NeuralDx exhibits significant technical debt, critical security vulnerabilities on DICOM servers, a lack of model drift monitoring, model training demographic bias, and an outdated software stack.\n\n"
            f"DICOM SERVER & SECURITY VULNERABILITIES:\n"
            f"- Unpatched Critical CVE: The DICOM server runs Orthanc 1.9.0 (released 2021) which contains CVE-2023-33466. This critical unpatched vulnerability allows unauthenticated remote read of patient scan metadata. [Grounding: Technical -> {get_citation(security, 'Technical')}]\n"
            f"- Open Pentest Findings: A September 2023 Bishop Fox penetration test revealed 2 Critical and 4 High findings. One Critical finding (unauthenticated DICOM endpoint) remains completely open.\n"
            f"- PACS Integration Key Hygiene: The PACS integration utilizes static API keys that have not been rotated in 18+ months.\n\n"
            f"INFRASTRUCTURE & DISASTER RECOVERY GAPS:\n"
            f"The entire production and storage infrastructure is deployed in a single region (AWS us-east-1). There is no multi-region replication, no failover, no documented disaster recovery (DR) plan, and RTO/RPO are entirely undefined, posing severe business continuity risks.\n\n"
            f"MODEL DRIFT & DEPRECIATED SOFTWARE STACK:\n"
            f"The core model relies on an outdated stack: PyTorch 1.12 (2022 release) and CUDA 11.6 (EOL). v1.2.4 of the model in production was last retrained in March 2022 (26+ months ago). More critically, the company has no model drift monitoring or system to detect if production scans deviate from the training distribution, risking clinical degradation. [Grounding: Technical -> {get_citation(stack, 'Technical')}]\n\n"
            f"DEMOGRAPHIC TRAINING DATA BIAS:\n"
            f"The model training dataset is 89% Caucasian. Internal, unaudited bias analysis from Feb 2024 revealed:\n"
            f"- Sensitivity in Black patients: 87.3% vs 96.1% in White patients (an 8.8% clinical accuracy gap).\n"
            f"- Sensitivity in obese patients (BMI > 35): 81.2%.\n"
            f"This bias was not disclosed in the FDA 510(k) filing. New March 2025 FDA minority health guidelines require a supplemental 510(k) or de novo submission to address this demographic disparity.\n\n"
            f"REAL-WORLD ACCURACY VS. MARKETING CLAIMS:\n"
            f"Marketing claims 94.1% sensitivity based on internal validation data. However, the only independent external validation (Yale Chest 2023, 3,200 scans) showed a sensitivity of 88.7% and specificity of 86.4%. This -5.4% sensitivity drop represents a significant real-world patient safety concern.\n"
        )
        if calc.get("questions") and calc["questions"].get("cto"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["cto"])
            tech_report += f"\n❓ AUTO-GENERATED VC DILIGENCE QUESTIONS (CTO):\n{qs}\n"
            
        tech_score_display = f"{tech_score:.1f}/10" if tech_score is not None else "N/A"
        tech_report += (
            f"\n🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(tech_flags)}\n\n"
            f"TECHNICAL RISK SCORE: {tech_score_display}\n"
            f"RECOMMENDATION: {tech_rec}"
        )

        mkt_report = (
            f"MARKET DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Market Research\n"
            f"Confidence: {tam.get('confidence', 80)}%\n\n"
            f"EXECUTIVE SUMMARY:\n"
            f"NeuralDx faces intense competition from well-funded market leaders, significant macro headwinds in hospital budgets, and inflated TAM assumptions.\n\n"
            f"MARKET OPPORTUNITY & TAM INFLATION:\n"
            f"- TAM Claim: {get_citation(tam, 'Market')}\n"
            f"Independent market analysis indicates that the $45B global radiology figure represents total radiology department spending (labor, equipment, etc.). The actual software addressable market for CADe/CADx tools in US hospitals is estimated at $900M–$1.4B by 2028. The company's TAM is inflated by 8-13x.\n\n"
            f"COMPETITIVE LANDSCAPE:\n"
            f"- Competition: {get_citation(competition, 'Market')}\n\n"
            f"Key threats include:\n"
            f"- Aidoc ($320M raised, Series D in Feb 2026): 15 cleared indications vs. 1 for NeuralDx.\n"
            f"- Viz.ai: Vested partnerships with Epic and Cerner, 20+ cleared models.\n"
            f"- Intelerad: PACS vendor bundling AI for free, squeezing margins.\n"
            f"- Microsoft Nuance: Already present in 80% of US hospitals.\n"
            f"- GE HealthCare: Bundling AI directly with CT scanner hardware.\n"
            f"- Mayo Clinic: Second-largest customer building its own replacement.\n\n"
            f"MACRO HEADWINDS:\n"
            f"- Hospital operating margins averaged -1.1% in 2025, leading to frozen SaaS budgets.\n"
            f"- CMS reimbursement: CPT code 0691T pays $18.25/scan, but private insurers (Aetna, Cigna) do not reimburse separately.\n"
            f"- Radiologist workforce shortage is easing (22% increase in residency matches), reducing SaaS workflow tools adoption urgency.\n\n"
            f"🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(mkt_flags)}\n\n"
            f"MARKET RISK SCORE: {mkt_score:.1f}/10\n" if mkt_score is not None else f"MARKET RISK SCORE: N/A\n"
        )
        mkt_report += f"RECOMMENDATION: {mkt_rec}"
    else:
        # Standard reports (retains compatibility with Auria, Helios, etc.)
        fin_report = (
            f"FINANCIAL DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Financial Analysis\n"
            f"Confidence: {arr.get('confidence', 80)}%\n\n"
            f"REVENUE & RUNWAY:\n"
            f"- ARR: {get_citation(arr, 'Financials')}\n"
            f"- Burn Rate: {get_citation(burn, 'Financials')}\n"
            f"- Runway: {get_citation(runway, 'Financials')}\n"
            f"- Gross Margin: {get_citation(gross_margin, 'Financials')}\n\n"
            f"CUSTOMER CONCENTRATION:\n"
            f"- {get_citation(customers, 'Financials')}\n"
        )
        if calc.get("scenario"):
            sc = calc["scenario"]
            fin_report += (
                f"\n📊 SCENARIO ENGINE: CLIENT CHURN SENSITIVITY (ESTIMATE)\n"
                f"If primary customer '{sc['client_name']}' churns (representing {sc['concentration_pct']:.0f}% concentration):\n"
                f"- Revenue Loss: -${sc['churn_revenue_loss']:,.0f} ARR\n"
                f"- New Projected ARR: ${sc['new_arr']:,.0f} ARR\n"
                f"- Burn Rate Impact: ${sc['current_monthly_burn']:,.0f}/mo → ${sc['new_monthly_burn']:,.0f}/mo\n"
                f"- Estimated Compressed Runway: {sc['new_runway']:.1f} months\n"
                f"- Valuation Markdown ({sc['multiple']:.1f}x multiple): {valuation} → ${sc['new_valuation']:,.0f}\n"
            )
        if calc.get("questions") and calc["questions"].get("ceo"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["ceo"])
            fin_report += f"\n❓ AUTO-GENERATED VC DILIGENCE QUESTIONS (CEO):\n{qs}\n"
        
        fin_score_display = f"{fin_score:.1f}/10" if fin_score is not None else "N/A"
        fin_report += (
            f"\n🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(fin_flags)}\n\n"
            f"FINANCIAL RISK SCORE: {fin_score_display}\n"
            f"RECOMMENDATION: {fin_rec}"
        )
        
        leg_report = (
            f"LEGAL DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Legal Analysis\n"
            f"Confidence: {litigation.get('confidence', 80)}%\n\n"
            f"LITIGATION STATUS:\n"
            f"- {get_citation(litigation, 'Legal')}\n\n"
            f"REGULATORY COMPLIANCE:\n"
            f"- Compliance: {get_citation(compliance, 'Legal')}\n"
        )
        if calc.get("questions") and calc["questions"].get("legal"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["legal"])
            leg_report += f"\n❓ AUTO-GENERATED VC DILIGENCE QUESTIONS (Legal Counsel):\n{qs}\n"
            
        leg_score_display = f"{leg_score:.1f}/10" if leg_score is not None else "N/A"
        leg_report += (
            f"\n🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(leg_flags)}\n\n"
            f"LEGAL RISK SCORE: {leg_score_display}\n"
            f"RECOMMENDATION: {leg_rec}"
        )
        
        tech_report = (
            f"TECHNICAL DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Technical Audit\n"
            f"Confidence: {stack.get('confidence', 80)}%\n\n"
            f"TECHNOLOGY STACK:\n"
            f"- Core stack: {get_citation(stack, 'Technical')}\n\n"
            f"SECURITY POSTURE:\n"
            f"- Security state: {get_citation(security, 'Technical')}\n"
        )
        if calc.get("questions") and calc["questions"].get("cto"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["cto"])
            tech_report += f"\n❓ AUTO-GENERATED VC DILIGENCE QUESTIONS (CTO):\n{qs}\n"
            
        tech_score_display = f"{tech_score:.1f}/10" if tech_score is not None else "N/A"
        tech_report += (
            f"\n🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(tech_flags)}\n\n"
            f"TECHNICAL RISK SCORE: {tech_score_display}\n"
            f"RECOMMENDATION: {tech_rec}"
        )
        
        mkt_report = (
            f"MARKET DUE DILIGENCE REPORT — {company_name}\n"
            f"Partner: Market Research\n"
            f"Confidence: {tam.get('confidence', 80)}%\n\n"
            f"MARKET OPPORTUNITY:\n"
            f"- TAM: {get_citation(tam, 'Market')}\n\n"
            f"COMPETITIVE LANDSCAPE:\n"
            f"- Competition: {get_citation(competition, 'Market')}\n\n"
            f"🚨 CRITICAL RED FLAGS:\n"
            f"{format_red_flags(mkt_flags)}\n\n"
            f"MARKET RISK SCORE: {mkt_score:.1f}/10\n" if mkt_score is not None else f"MARKET RISK SCORE: N/A\n"
        )
        mkt_report += f"RECOMMENDATION: {mkt_rec}"
    
    weighted_score = calc["weighted_score"]
    verdict = calc["verdict"]
    coverage_score = calc["coverage_score"]
    
    # build primary reasons list
    reasons = []
    if weighted_score is None:
        reasons = ["Coverage below minimum threshold (40%)"]
    elif calc["override_reasons"]:
        reasons = calc["override_reasons"]
    else:
        all_flags = fin_flags + leg_flags + tech_flags + mkt_flags
        for f in all_flags[:3]:
            if isinstance(f, dict):
                reasons.append(f.get("claim"))
            else:
                reasons.append(str(f))
        if not reasons:
            reasons = ["Target company metrics align with investment thesis.", "TAM and sector timing support the deal.", "Compliance and technical audits resolved successfully."]
            
    reasons_str = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasons))
    
    co_text = company_name[:42]
    deal_text = f"{raise_amount} at {valuation} post"[:42]
    decision_text = ("REJECT" if verdict == "PASS" else verdict)[:42]
    
    confidence_val_pct = calc.get("verdict_confidence", coverage_score)
    confidence_text = f"{confidence_val_pct:.1f}%"[:42]
    
    quality_val_pct = calc.get("evidence_quality_score", 80.0)
    quality_text = f"{quality_val_pct:.1f}%"[:42]
    
    readiness_score = calc.get("deal_readiness_score", 80.0)
    readiness_status = calc.get("deal_readiness_status", "Ready for IC Review")
    readiness_text = f"{readiness_score:.1f}/100 ({readiness_status})"[:42]
    
    fin_val_str = f"{fin_score:>2.0f}/10" if fin_score is not None else " N/A "
    fin_w_str = f"{0.3*fin_score:>4.2f}" if fin_score is not None else " N/A"
    
    leg_val_str = f"{leg_score:>2.0f}/10" if leg_score is not None else " N/A "
    leg_w_str = f"{0.25*leg_score:>4.2f}" if leg_score is not None else " N/A"
    
    tech_val_str = f"{tech_score:>2.0f}/10" if tech_score is not None else " N/A "
    tech_w_str = f"{0.25*tech_score:>4.2f}" if tech_score is not None else " N/A"
    
    mkt_val_str = f"{mkt_score:>2.0f}/10" if mkt_score is not None else " N/A "
    mkt_w_str = f"{0.2*mkt_score:>4.2f}" if mkt_score is not None else " N/A"
    
    weighted_val_str = f"{weighted_score:>4.1f}/10" if weighted_score is not None else " N/A  "
    
    card = (
        "```\n"
        "+----------------------------------------------------------+\n"
        "|         FUSION INVESTMENT COMMITTEE DECISION             |\n"
        "+----------------------------------------------------------+\n"
        f"| Company:      {co_text:<42} |\n"
        f"| Deal:         {deal_text:<42} |\n"
        "+----------------------------------------------------------+\n"
        f"|  DECISION:    {decision_text:<42} |\n"
        f"|  CONFIDENCE:  {confidence_text:<42} |\n"
        f"|  EVI QUALITY: {quality_text:<42} |\n"
        f"|  READINESS:   {readiness_text:<42} |\n"
        "+----------------------------------------------------------+\n\n"
        "RISK SCORECARD:\n"
        f"  Financial Risk:  {fin_val_str}  (weight: 30%) → {fin_w_str}\n"
        f"  Legal Risk:      {leg_val_str}  (weight: 25%) → {leg_w_str}\n"
        f"  Technical Risk:  {tech_val_str}  (weight: 25%) → {tech_w_str}\n"
        f"  Market Risk:     {mkt_val_str}  (weight: 20%) → {mkt_w_str}\n"
        "  ------------------------------------------------------\n"
        f"  WEIGHTED SCORE:  {weighted_val_str}\n\n"
        "PRIMARY REASONS:\n"
        f"{reasons_str}\n"
        "```"
    )
    
    if calc.get("missing_gaps"):
        gaps_str = ", ".join(calc["missing_gaps"])
        card += f"\n\nMISSING DILIGENCE GAPS:\n- {gaps_str}"
        
    warnings_str = ""
    if calc.get("contradictions"):
        for contra in calc["contradictions"]:
            warnings_str += f"{contra['message']}\n"
    if calc.get("validation_warnings"):
        for warn in calc["validation_warnings"]:
            warnings_str += f"{warn}\n"
    if warnings_str:
        card = warnings_str + "\n" + card
        
    final_reports = {
        "financial_partner": fin_report,
        "legal_partner": leg_report,
        "technical_partner": tech_report,
        "market_partner": mkt_report,
        "managing_partner": card
    }
    
    next_room_map = {
        "financial_partner": ("managing-partner-room", f"@managing-partner FINANCIAL ANALYSIS COMPLETE. Risk Score: {fin_score:.1f}/10. {fin_rec}." if fin_score is not None else f"@managing-partner FINANCIAL ANALYSIS COMPLETE. Risk Score: N/A. {fin_rec}."),
        "legal_partner": ("managing-partner-room", f"@managing-partner LEGAL ANALYSIS COMPLETE. Risk Score: {leg_score:.1f}/10. {leg_rec}." if leg_score is not None else f"@managing-partner LEGAL ANALYSIS COMPLETE. Risk Score: N/A. {leg_rec}."),
        "technical_partner": ("managing-partner-room", f"@managing-partner TECHNICAL ANALYSIS COMPLETE. Risk Score: {tech_score:.1f}/10. {tech_rec}." if tech_score is not None else f"@managing-partner TECHNICAL ANALYSIS COMPLETE. Risk Score: N/A. {tech_rec}."),
        "market_partner": ("managing-partner-room", f"@managing-partner MARKET ANALYSIS COMPLETE. Risk Score: {mkt_score:.1f}/10. {mkt_rec}." if mkt_score is not None else f"@managing-partner MARKET ANALYSIS COMPLETE. Risk Score: N/A. {mkt_rec}."),
    }

    expects_real_schema = False
    for t in tools:
        func = t.get("function", {})
        if func.get("name") == "thenvoi_send_message":
            properties = func.get("parameters", {}).get("properties", {})
            if "content" in properties:
                expects_real_schema = True
                break

    def _resolve_mention_handle(msg_text: str) -> str:
        msg_text = msg_text.lower()
        if "@financial-partner" in msg_text:
            return "baljotchohan23/financial-partner"
        if "@legal-partner" in msg_text:
            return "baljotchohan23/legal-partner"
        if "@technical-partner" in msg_text:
            return "baljotchohan23/technical-partner"
        if "@market-partner" in msg_text:
            return "baljotchohan23/market-partner"
        if "@managing-partner" in msg_text:
            return "baljotchohan23/managing-partner"
        return "baljotchohan23/managing-partner"

    def _send(call_id, room, message):
        if expects_real_schema:
            handle = _resolve_mention_handle(message)
            # Strip the leading mention handle from the content to prevent double pills in the UI,
            # as the platform automatically prepends the pill from the mentions parameter.
            short_handle = message.split()[0] if message.startswith("@") else ""
            if short_handle and short_handle.startswith("@"):
                cleaned_message = message[len(short_handle):].lstrip()
            else:
                cleaned_message = message
            logger.info(f"Mock LLM [_send]: {agent_name} sending content='{cleaned_message}', mentions={repr([handle])}")
            tool_calls.append({
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "thenvoi_send_message",
                    "arguments": json.dumps({"content": cleaned_message, "mentions": [handle]}),
                },
            })
        else:
            tool_calls.append({
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "thenvoi_send_message",
                    "arguments": json.dumps({"room": room, "message": message}),
                },
            })

    def _call(call_id, name, arguments):
        tool_calls.append({
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        })

    # React-loop-aware staging: branch on the LAST message
    last_msg = messages[-1] if messages else {}
    last_role = last_msg.get("role", "")
    last_content = str(last_msg.get("content", "") or "")
    
    handoff_done = False
    if last_role in ("tool", "function"):
        # 1. Check if the tool call that produced this result was thenvoi_send_message
        tool_call_id = last_msg.get("tool_call_id")
        if len(messages) >= 2:
            prev_msg = messages[-2]
            if prev_msg.get("role") == "assistant":
                for tc in prev_msg.get("tool_calls", []):
                    if tc.get("id") == tool_call_id and tc.get("function", {}).get("name") == "thenvoi_send_message":
                        handoff_done = True
                        break
        # 2. Check the content or name/function_name for backward compatibility
        if not handoff_done:
            handoff_done = (
                "Message sent successfully" in last_content
                or last_msg.get("name") == "thenvoi_send_message"
                or last_msg.get("function_name") == "thenvoi_send_message"
            )
            
    data_tool_result = last_role in ("tool", "function") and not handoff_done

    if agent_name == "managing_partner":
        if "thenvoi_send_message" in available_tool_names:
            # Query memory graph to see which partners have logged their reports
            deal_id = sim_state.active_incident_id
            if not deal_id:
                deal_id = memory_graph.get_latest_incident_id()
            if not deal_id:
                # Create a default deal if none exists
                import uuid
                deal_id = f"deal_{uuid.uuid4().hex[:8]}"
                sim_state.active_incident_id = deal_id
                memory_graph.create_incident(deal_id, {"trigger": "auto_trigger", "company": "NovaPay Inc"})
            
            sim_state.active_incident_id = deal_id
            
            # Check logged findings in the memory graph — ONLY
            # use the current deal's timeline. Do NOT scan room chat
            # history, which contains stale "COMPLETE" strings from
            # previous runs and causes false all-done detection.
            logged_agents = set()
            inc = memory_graph.get_incident(deal_id) or {}
            for event in inc.get("timeline", []):
                logged_agents.add(event.get("agent"))
            
            # Also include agents tracked by sim_state (set by mock LLM
            # when their handoff completes — this is the most reliable
            # source since it updates synchronously in the same process).
            logged_agents.update(sim_state.completed_agents)
            
            # Also check the LATEST user message only (not full history)
            # to detect a partner that just finished in this turn.
            latest_user = user_msg  # already extracted above
            if "FINANCIAL ANALYSIS COMPLETE" in latest_user:
                logged_agents.add("financial_partner")
            if "LEGAL ANALYSIS COMPLETE" in latest_user:
                logged_agents.add("legal_partner")
            if "TECHNICAL ANALYSIS COMPLETE" in latest_user:
                logged_agents.add("technical_partner")
            if "MARKET ANALYSIS COMPLETE" in latest_user:
                logged_agents.add("market_partner")
            
            have_fin = "financial_partner" in logged_agents
            have_leg = "legal_partner" in logged_agents
            have_tech = "technical_partner" in logged_agents
            have_mkt = "market_partner" in logged_agents

            logger.info(f"[managing_partner] have_fin={have_fin}, have_leg={have_leg}, have_tech={have_tech}, have_mkt={have_mkt}")
            if have_fin and have_leg and have_tech and have_mkt:
                # All reports are in, deliver final synthesized decision
                response_content = final_reports["managing_partner"]
                # Cache it so that the adapter has a last-resort fallback
                sim_state.final_verdict_card = response_content
                
                sim_state.completed_agents.add("managing_partner")
                # Do NOT set deal_concluded here — let broadcast_event_to_websockets
                # verify all 4 specialists completed first. This prevents the race
                # condition where the verdict kills slower specialists mid-flight.
                sim_state._mp_verdict_pending = True
                logger.info("[managing_partner] ✅ VERDICT RENDERED — awaiting all specialists before concluding")
            else:
                # Fresh trigger or partial reports
                sent_brief = deal_id in sim_state.dispatched_deals
                logger.info(f"[managing_partner] deal_id={deal_id}, sent_brief={sent_brief}, dispatched={sim_state.dispatched_deals}")
                if not sent_brief:
                    # Dispatch parallel requests to all 4 partners
                    brief_co = sim_state.active_company_name or inc.get("metadata", {}).get("company") or "NovaPay Inc"
                    _send("call_mp_fin", "finance-partner-room", f"@financial-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your financial due diligence now and report back to managing-partner-room.")
                    _send("call_mp_leg", "legal-partner-room", f"@legal-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your legal due diligence now and report back to managing-partner-room.")
                    _send("call_mp_tech", "tech-partner-room", f"@technical-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your technical due diligence now and report back to managing-partner-room.")
                    _send("call_mp_mkt", "market-partner-room", f"@market-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your market due diligence now and report back to managing-partner-room.")
                    sim_state.dispatched_deals.add(deal_id)
                    logger.info(f"[managing_partner] Dispatched briefs. tool_calls={len(tool_calls)}")
                    response_content = "Dispatched briefs to partners."
                else:
                    waiting_for = []
                    if not have_fin: waiting_for.append("Financial")
                    if not have_leg: waiting_for.append("Legal")
                    if not have_tech: waiting_for.append("Technical")
                    if not have_mkt: waiting_for.append("Market")
                    response_content = f"Managing Partner: awaiting findings from {', '.join(waiting_for)} Partner..."
    else:
        # Specialists
        if handoff_done:
            response_content = final_reports.get(agent_name, "Processing complete.")
            # Mark this specialist as completed so it won't re-process
            sim_state.completed_agents.add(agent_name)
            logger.info(f"[{agent_name}] ✅ Marked as completed (handoff done)")
        elif data_tool_result:
            response_content = final_reports.get(agent_name, "Processing complete.")
            next_step = next_room_map.get(agent_name)
            if next_step and "thenvoi_send_message" in available_tool_names:
                room, message = next_step
                _send("call_next_handoff", room, message)
        else:
            # Stage 1: fresh user stimulus
            if agent_name == "financial_partner":
                if "load_deal_brief" in available_tool_names:
                    _call("call_fin_1", "load_deal_brief", "{\"section\": \"financials\"}")
            elif agent_name == "legal_partner":
                if "load_deal_brief" in available_tool_names:
                    _call("call_leg_1", "load_deal_brief", "{\"section\": \"legal\"}")
            elif agent_name == "technical_partner":
                if "load_deal_brief" in available_tool_names:
                    _call("call_tech_1", "load_deal_brief", "{\"section\": \"technical\"}")
            elif agent_name == "market_partner":
                if "load_deal_brief" in available_tool_names:
                    _call("call_mkt_1", "load_deal_brief", "{\"section\": \"market\"}")

    if body.get("stream"):
        import time
        from fastapi.responses import StreamingResponse

        async def stream_generator():
            try:
                if tool_calls:
                    # Emit the analysis content BEFORE the tool_calls so LangGraph
                    # assembles an AIMessage with content=full_report AND tool_calls=[...].
                    # Without this, msg_content="" and the graph state extractor falls
                    # back to the short thenvoi_send_message arg (54 chars) instead of
                    # the full due-diligence report (1000+ chars).
                    if response_content:
                        content_chunk = {
                            "id": "chatcmpl-mock",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "mock-model",
                            "choices": [{
                                "index": 0,
                                "delta": {"role": "assistant", "content": response_content},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(content_chunk)}\n\n"
                        await asyncio.sleep(0.02)

                    # Yield tool calls delta chunk
                    chunk = {
                        "id": "chatcmpl-mock",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "mock-model",
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "index": i,
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {
                                            "name": tc["function"]["name"],
                                            "arguments": tc["function"]["arguments"]
                                        }
                                    }
                                    for i, tc in enumerate(tool_calls)
                                ]
                            },
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.02)

                    # Yield finish_reason chunk
                    chunk = {
                        "id": "chatcmpl-mock",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "mock-model",
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "tool_calls"
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    # Yield content delta chunk
                    chunk = {
                        "id": "chatcmpl-mock",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "mock-model",
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": response_content
                            },
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.02)
                    
                    # Yield finish_reason chunk
                    chunk = {
                        "id": "chatcmpl-mock",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "mock-model",
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                logger.error(f"Mock LLM: error in stream generator: {e}")
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    return JSONResponse({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": response_content,
                "tool_calls": tool_calls if tool_calls else None
            },
            "finish_reason": "tool_calls" if tool_calls else "stop"
        }]
    })

# ─── WEBSOCKET ROUTE ──────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket endpoint for the Next.js dashboard to stream live updates.

    Accepts a `token` query param (Firebase ID token) to scope events to the
    authenticated user. Unauthenticated connections land in "__public__" bucket
    and only receive events from unauthenticated deal triggers.
    """
    uid = "__public__"
    username = "guest"
    if token:
        try:
            from firebase_admin import auth as fb_auth
            decoded = fb_auth.verify_id_token(token)
            uid = decoded["uid"]
            email = decoded.get("email")
            username = decoded.get("name") or (email.split("@")[0] if email else None) or uid
            
            from core.auth import current_token
            current_token.set(token)
        except Exception:
            pass  # invalid/expired token → public bucket

    from core.auth import current_uid, current_username
    current_uid.set(uid)
    current_username.set(username)

    await websocket.accept()
    active_websockets[uid].add(websocket)
    total = sum(len(s) for s in active_websockets.values())
    logger.info(f"FastAPI: WebSocket connected uid={uid}. Total connections: {total}")

    # RTDB: record live presence so Firebase Console shows who's connected
    if uid != "__public__":
        try:
            ip = websocket.headers.get("x-forwarded-for", "").split(",")[0].strip() or (websocket.client.host if websocket.client else "unknown")
            user_agent = websocket.headers.get("user-agent", "unknown")
            from core.rtdb import write_activity, upsert_profile
            if token:
                try:
                    from firebase_admin import auth as _fba
                    _dec = _fba.verify_id_token(token)
                    upsert_profile(uid, _dec.get("name"), _dec.get("email"), _dec.get("picture"), ip=ip, user_agent=user_agent)
                except Exception:
                    pass
            write_activity(uid, "session_connected", {"totalConnections": total, "ip": ip, "userAgent": user_agent})
        except Exception:
            pass

    # Replay completed agent findings for THIS user's active deal
    try:
        user_memory = memory_graph.__class__(uid=uid)
        deal_id = sim_state.active_incident_id if sim_state.active_uid == uid else None
        deal_id = deal_id or user_memory.get_latest_incident_id()
        if deal_id:
            inc = user_memory.get_incident(deal_id) or {}
            for event in inc.get("timeline", []):
                await websocket.send_json({
                    "type": "agent_update",
                    "agent": event.get("agent"),
                    "status": "done",
                    "output": {"report": event.get("finding")},
                    "timestamp": event.get("timestamp", "")
                })
            agent_names = ["managing_partner", "financial_partner", "legal_partner", "technical_partner", "market_partner"]
            for agent_name in agent_names:
                if sim_state.agent_statuses.get(agent_name) == "working" and sim_state.active_uid == uid:
                    await websocket.send_json({
                        "type": "agent_update", "agent": agent_name,
                        "status": "working", "output": {}, "timestamp": ""
                    })
    except Exception as e:
        logger.error(f"FastAPI: Error sending initial state to WebSocket: {e}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
                logger.debug(f"FastAPI: Received WS message: {data}")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        active_websockets[uid].discard(websocket)
        total = sum(len(s) for s in active_websockets.values())
        logger.info(f"FastAPI: WebSocket disconnected uid={uid}. Total connections: {total}")
    except Exception as e:
        logger.error(f"FastAPI: WebSocket error: {e}")
        active_websockets[uid].discard(websocket)
