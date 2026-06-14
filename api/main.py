# api/main.py
"""
FastAPI application serving REST endpoints and a WebSocket server
to stream real-time agent updates to the Next.js dashboard.
"""
import os
import json
import logging
import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
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
from core.pitch_loader import _load_pitch_file
import mcp_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fusion.api")

# ── Remote MCP transport ─────────────────────────────────────────────────────
# Expose the same 5 committee tools as mcp_server.py (stdio) over streamable HTTP,
# mounted at /mcp, so ANY MCP client can connect to the deployed FUSION by URL.
# Tool behavior is shared via mcp_tools.dispatch — stdio and HTTP can't drift.
# streamable_http_path="/" + mount("/mcp") => the endpoint is exactly /mcp.
fusion_mcp = FastMCP("fusion-mcp", stateless_http=True, streamable_http_path="/")
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


# Active WebSocket dashboard connections
active_websockets: List[WebSocket] = []

def _clear_agent_busy_flags():
    if is_mock_mode():
        for room_agents in mock_bus.rooms.values():
            for agent in room_agents:
                agent._is_busy = False


async def broadcast_event_to_websockets(event_data: dict):
    """Callback registered with event_bus to forward agent updates to the dashboard."""
    sim_state.touch()
    # Track last-known status per agent for the chat API / MCP clients
    if event_data.get("agent"):
        sim_state.agent_statuses[event_data["agent"]] = event_data.get("status", "idle")

    # Auto-reset simulation lock when managing partner (last agent) finishes and delivers the final synthesized verdict
    if event_data.get("agent") == "managing_partner" and event_data.get("status") == "done":
        output_data = event_data.get("output") or {}
        report_text = output_data.get("report") or ""
        import re
        if re.search(r"DECISION:", report_text, re.I):
            sim_state.running = False
            sim_state.deal_concluded = True
            # Clear all agent busy flags so the next run starts clean
            _clear_agent_busy_flags()
            logger.info("FastAPI: Simulation complete (verdict rendered) — state auto-reset.")
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

    if not active_websockets:
        return

    message = json.dumps(event_data)
    # Broadcast to all connected clients
    for ws in list(active_websockets):
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send to WebSocket: {e}")
            active_websockets.remove(ws)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Register the event bus listener on application startup
    event_bus.register_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener registered.")
    
    # The MCP session manager must run for the mounted /mcp app to serve requests.
    async with fusion_mcp.session_manager.run():
        logger.info("🔌 FUSION MCP streamable-HTTP transport live at /mcp")
        yield
        
    # Unregister the listener on application shutdown
    event_bus.unregister_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener unregistered.")


app = FastAPI(title="FUSION API", version="1.0.0", lifespan=lifespan)
app.include_router(v1_router)
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

# ─── REST ENDPOINTS ───────────────────────────────────────────

class TriggerResponse(BaseModel):
    status: str
    message: str
    mode: str

@app.post("/api/trigger-attack", response_model=TriggerResponse)
async def trigger_attack():
    """Compatibility wrapper that triggers the FUSION deal review."""
    res = await trigger_deal()
    return TriggerResponse(
        status=res.get("status", "error"),
        message=res.get("message", ""),
        mode=res.get("mode", "mock")
    )

@app.post("/api/trigger-deal")
async def trigger_deal(company: Optional[str] = None, raise_amount: str = "$10M"):
    """Triggers the FUSION investment committee on a deal."""
    if sim_state.is_stale(max_idle_seconds=90):
        sim_state.reset()
        _clear_agent_busy_flags()

    if sim_state.running:
        return {"status": "already_running", "message": "Committee already in session.", "mode": "mock" if is_mock_mode() else "real"}

    # Reset simulation state and agent flags for a fresh run
    sim_state.reset()
    _clear_agent_busy_flags()

    sim_state.running = True
    sim_state.touch()

    from core.demo_registry import resolve_pitch_file
    from core.pitch_loader import clear_pitch_cache, resolve_uploaded_pitch, _company_name_of, _load_pitch_file

    # Resolve which pitch the committee should analyze. The uploaded-document
    # binding must survive a server restart / state reset, so we resolve the
    # uploaded pitch from DISK (durable) rather than trusting in-memory state:
    #  1. an explicitly-named built-in demo company   → its pitch file
    #  2. an uploaded pitch matching the company name  → that upload (by disk)
    #  3. no company given but an upload exists         → the most recent upload
    #  4. otherwise                                     → default (NovaPay)
    new_deal_id = f"DEAL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    resolved_pitch = resolve_pitch_file(company) if company else None
    if resolved_pitch:
        deal_id = new_deal_id
        sim_state.active_pitch_file = resolved_pitch
        sim_state.active_company_name = company
        logger.info(f"trigger-deal: resolved demo '{company}' → pitch file {resolved_pitch}")
    else:
        up_file, up_incident = resolve_uploaded_pitch(company)
        if up_file:
            # Reuse the uploaded incident so the report ties back to the upload.
            deal_id = up_incident or new_deal_id
            sim_state.active_pitch_file = up_file
            sim_state.active_company_name = company or _company_name_of(_load_pitch_file(up_file)) or "Uploaded Deal"
            logger.info(f"trigger-deal: '{company}' → uploaded pitch {up_file} (incident {deal_id})")
        else:
            deal_id = new_deal_id
            sim_state.active_pitch_file = None  # loader falls back to the default pitch
            sim_state.active_company_name = company or "NovaPay Inc"
            logger.info(f"trigger-deal: no demo/upload match for '{company}' → default pitch")

    company = sim_state.active_company_name
    memory_graph.create_incident(deal_id, {"trigger": "pitch_submission", "company": company})
    sim_state.active_incident_id = deal_id
    sim_state.dispatched_deals.clear()   # fresh run — nothing dispatched yet
    clear_pitch_cache()

    brief = f"New deal submitted for committee review: {company} — Series A, {raise_amount} raise. Full pitch data is loaded in the deal brief. Please convene the investment committee and begin due diligence."

    if is_mock_mode():
        await mock_bus.send_message(
            sender="Deal-Intake",
            target_room="managing-partner-room",
            message=brief
        )
        return {"status": "success", "message": f"Deal '{company}' submitted to committee (Mock Mode).", "deal_id": deal_id, "mode": "mock"}
    else:
        from api.v1 import dispatch_real_band_message
        ok = await dispatch_real_band_message(brief, "managing-partner", sender_agent_name="financial_partner")
        if ok:
            return {"status": "success", "message": f"Deal '{company}' submitted to real Band rooms.", "deal_id": deal_id, "mode": "real"}
        else:
            return {"status": "error", "message": "Failed to dispatch trigger message to real Band room.", "deal_id": deal_id, "mode": "real"}


@app.get("/api/status")
async def get_status():
    """Basic health check and configuration status."""
    return {
        "status": "healthy",
        "mock_mode": is_mock_mode(),
        "registered_rooms": list(mock_bus.rooms.keys()) if is_mock_mode() else [],
        "simulation_running": sim_state.running,
        "active_incident_id": sim_state.active_incident_id,
        "memory_incidents": memory_graph.get_memory_stats()["total_incidents"],
    }

@app.post("/api/reset")
async def reset_simulation():
    """Resets the simulation state so a new attack can be triggered."""
    sim_state.reset()
    # Clear all agent busy flags so they're ready for the next run
    if is_mock_mode():
        for room_agents in mock_bus.rooms.values():
            for agent in room_agents:
                agent._is_busy = False
    logger.info("FastAPI: Simulation state reset. Ready for next run.")
    return {"status": "reset", "message": "Simulation state cleared. Ready for next run."}

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
    body = await request.json()
    messages = body.get("messages", [])
    tools = body.get("tools", [])

    # Extract system prompt and user input
    system_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
    user_msg = user_msgs[-1] if user_msgs else ""

    # Infer calling agent
    model = body.get("model", "")
    agent_name = ""
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
    # If this agent already completed its work for the current deal,
    # or the deal has been fully concluded, return a short no-op
    # response so the LangGraph turn ends without new tool calls.
    if sim_state.deal_concluded:
        logger.info(f"[{agent_name}] Deal already concluded — returning no-op")
        return _build_response(body, f"{agent_name}: Deal already concluded. Standing by.", [])
    if agent_name in sim_state.completed_agents and agent_name != "managing_partner":
        logger.info(f"[{agent_name}] Already completed for this deal — returning no-op")
        return _build_response(body, f"{agent_name}: Analysis already submitted. Standing by.", [])
    # Managing partner can be called multiple times (once per incoming
    # specialist report) but should stop once it has rendered its verdict.
    if agent_name == "managing_partner" and "managing_partner" in sim_state.completed_agents:
        logger.info(f"[managing_partner] Verdict already rendered — returning no-op")
        return _build_response(body, "Managing Partner: Final verdict already rendered. Standing by.", [])
    # ─────────────────────────────────────────────────────────────

    last_msg = messages[-1] if messages else {}
    last_role = last_msg.get("role", "")
    has_tool_messages = last_role in ("tool", "function")

    # ── Realistic pacing delays ────────────────────────────────────────────────
    STAGE1_DELAYS = {
        "managing_partner":    (1.5, 2.5),
        "financial_partner":   (2.0, 3.5),
        "legal_partner":       (2.0, 3.5),
        "technical_partner":   (2.5, 4.0),
        "market_partner":      (2.0, 3.0),
    }
    STAGE2_DELAYS = {
        "managing_partner":    (2.5, 4.0),
        "financial_partner":   (1.5, 2.5),
        "legal_partner":       (1.5, 2.5),
        "technical_partner":   (2.0, 3.0),
        "market_partner":      (1.5, 2.5),
    }

    delay_range = (STAGE2_DELAYS if has_tool_messages else STAGE1_DELAYS).get(
        agent_name, (1.0, 2.0)
    )
    pace = float(os.getenv("ARGUS_MOCK_PACE", "0.6"))
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
    decision_text = verdict[:42]
    
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
                
                # Check if verdict was already dispatched as a message
                sent_verdict = sim_state.verdict_dispatched
                if not sent_verdict:
                    # Prepend a mention to financial-partner to satisfy the API requirement
                    verdict_msg = f"@financial-partner {response_content}"
                    _send("call_mp_verdict", "finance-partner-room", verdict_msg)
                    sim_state.verdict_dispatched = True
                    logger.info("[managing_partner] Dispatched final verdict scorecard to room")
                    response_content = "Dispatched final verdict scorecard."
                else:
                    sim_state.completed_agents.add("managing_partner")
                    sim_state.deal_concluded = True
                    sim_state.running = False
                    logger.info("[managing_partner] ✅ VERDICT RENDERED — deal concluded")
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
            if tool_calls:
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
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for the Next.js dashboard to stream live updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info(f"FastAPI: WebSocket connected. Active connections: {len(active_websockets)}")

    # Send initial status/replay of all completed agent findings upon connection
    try:
        deal_id = sim_state.active_incident_id or memory_graph.get_latest_incident_id()
        if deal_id:
            inc = memory_graph.get_incident(deal_id) or {}
            for event in inc.get("timeline", []):
                agent_name = event.get("agent")
                finding = event.get("finding")
                await websocket.send_json({
                    "type": "agent_update",
                    "agent": agent_name,
                    "status": "done",
                    "output": {"report": finding},
                    "timestamp": event.get("timestamp", "")
                })
            
            agent_names = ["managing_partner", "financial_partner", "legal_partner", "technical_partner", "market_partner"]
            for agent_name in agent_names:
                status = sim_state.agent_statuses.get(agent_name, "idle")
                if status == "working":
                    await websocket.send_json({
                        "type": "agent_update",
                        "agent": agent_name,
                        "status": "working",
                        "output": {},
                        "timestamp": ""
                    })
    except Exception as e:
        logger.error(f"FastAPI: Error sending initial state to WebSocket: {e}")

    try:
        while True:
            # Maintain connection, check for keepalives
            data = await websocket.receive_text()
            logger.debug(f"FastAPI: Received WS message: {data}")
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        logger.info(f"FastAPI: WebSocket disconnected. Active connections: {len(active_websockets)}")
    except Exception as e:
        logger.error(f"FastAPI: WebSocket error: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)
