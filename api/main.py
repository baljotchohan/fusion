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
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.event_bus import event_bus
from core.band_client import mock_bus, is_mock_mode
from core.memory_graph import memory_graph
from api.state import sim_state
from api.v1 import router as v1_router
from core.pitch_loader import _load_pitch_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fusion.api")

app = FastAPI(title="FUSION API", version="1.0.0")
app.include_router(v1_router)

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

# Register the event bus listener on application startup
@app.on_event("startup")
async def startup_event():
    event_bus.register_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener registered.")

@app.on_event("shutdown")
async def shutdown_event():
    event_bus.unregister_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener unregistered.")

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
async def trigger_deal(company: str = "NovaPay Inc", raise_amount: str = "$10M"):
    """Triggers the FUSION investment committee on a deal."""
    if sim_state.is_stale(max_idle_seconds=90):
        sim_state.reset()
        _clear_agent_busy_flags()

    if sim_state.running:
        return {"status": "already_running", "message": "Committee already in session.", "mode": "mock" if is_mock_mode() else "real"}

    sim_state.running = True
    sim_state.touch()

    if sim_state.active_incident_id:
        deal_id = sim_state.active_incident_id
        inc = memory_graph.get_incident(deal_id)
        if inc:
            company = inc["metadata"].get("company", company)
    else:
        from datetime import datetime, timezone
        deal_id = f"DEAL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        memory_graph.create_incident(deal_id, {"trigger": "pitch_submission", "company": company})
        sim_state.active_incident_id = deal_id

    brief = f"New deal submitted for committee review: {company} — Series A, {raise_amount} raise. Full pitch data is loaded in the deal brief. Please convene the investment committee and begin due diligence."

    if is_mock_mode():
        await mock_bus.send_message(
            sender="Deal-Intake",
            target_room="managing-partner-room",
            message=brief
        )
        return {"status": "success", "message": f"Deal '{company}' submitted to committee (Mock Mode).", "deal_id": deal_id, "mode": "mock"}
    else:
        return {"status": "success", "message": f"Deal '{company}' submitted to real Band rooms.", "deal_id": deal_id, "mode": "real"}


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
    
    fin_report += (
        f"\n🚨 CRITICAL RED FLAGS:\n"
        f"{format_red_flags(fin_flags)}\n\n"
        f"FINANCIAL RISK SCORE: {fin_score:.1f}/10\n"
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
        
    leg_report += (
        f"\n🚨 CRITICAL RED FLAGS:\n"
        f"{format_red_flags(leg_flags)}\n\n"
        f"LEGAL RISK SCORE: {leg_score:.1f}/10\n"
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
        
    tech_report += (
        f"\n🚨 CRITICAL RED FLAGS:\n"
        f"{format_red_flags(tech_flags)}\n\n"
        f"TECHNICAL RISK SCORE: {tech_score:.1f}/10\n"
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
        f"MARKET RISK SCORE: {mkt_score:.1f}/10\n"
        f"RECOMMENDATION: {mkt_rec}"
    )
    
    weighted_score = calc["weighted_score"]
    verdict = calc["verdict"]
    coverage_score = calc["coverage_score"]
    
    # build primary reasons list
    reasons = []
    if calc["override_reasons"]:
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
    
    co_text = company_name[:44]
    deal_text = f"{raise_amount} at {valuation} post"[:44]
    decision_text = verdict[:42]
    
    confidence_val_pct = calc.get("verdict_confidence", coverage_score)
    confidence_text = f"{confidence_val_pct:.1f}%"[:42]
    
    quality_val_pct = calc.get("evidence_quality_score", 80.0)
    quality_text = f"{quality_val_pct:.1f}%"[:42]
    
    readiness_score = calc.get("deal_readiness_score", 80.0)
    readiness_status = calc.get("deal_readiness_status", "Ready for IC Review")
    readiness_text = f"{readiness_score:.1f}/100 ({readiness_status})"[:42]
    
    card = (
        "╔══════════════════════════════════════════════════════════╗\n"
        "║         FUSION INVESTMENT COMMITTEE DECISION             ║\n"
        "╠══════════════════════════════════════════════════════════╣\n"
        f"║ Company:    {co_text:<44} ║\n"
        f"║ Deal:       {deal_text:<44} ║\n"
        "╠══════════════════════════════════════════════════════════╣\n"
        f"║  DECISION:    {decision_text:<42} ║\n"
        f"║  CONFIDENCE:  {confidence_text:<42} ║\n"
        f"║  EVI QUALITY: {quality_text:<42} ║\n"
        f"║  READINESS:   {readiness_text:<42} ║\n"
        "╚══════════════════════════════════════════════════════════╝\n\n"
        "RISK SCORECARD:\n"
        f"  Financial Risk:  {fin_score:>2.0f}/10  (weight: 30%) → {0.3*fin_score:>4.2f}\n"
        f"  Legal Risk:      {leg_score:>2.0f}/10  (weight: 25%) → {0.25*leg_score:>4.2f}\n"
        f"  Technical Risk:  {tech_score:>2.0f}/10  (weight: 25%) → {0.25*tech_score:>4.2f}\n"
        f"  Market Risk:     {mkt_score:>2.0f}/10  (weight: 20%) → {0.2*mkt_score:>4.2f}\n"
        "  ─────────────────────────────────────────────\n"
        f"  WEIGHTED SCORE:  {weighted_score:>4.1f}/10\n\n"
        "PRIMARY REASONS:\n"
        f"{reasons_str}"
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
        "financial_partner": ("managing-partner-room", f"@managing-partner FINANCIAL ANALYSIS COMPLETE. Risk Score: {fin_score:.1f}/10. {fin_rec}."),
        "legal_partner": ("managing-partner-room", f"@managing-partner LEGAL ANALYSIS COMPLETE. Risk Score: {leg_score:.1f}/10. {leg_rec}."),
        "technical_partner": ("managing-partner-room", f"@managing-partner TECHNICAL ANALYSIS COMPLETE. Risk Score: {tech_score:.1f}/10. {tech_rec}."),
        "market_partner": ("managing-partner-room", f"@managing-partner MARKET ANALYSIS COMPLETE. Risk Score: {mkt_score:.1f}/10. {mkt_rec}."),
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
            return "@baljotchohan23/financial-partner"
        if "@legal-partner" in msg_text:
            return "@baljotchohan23/legal-partner"
        if "@technical-partner" in msg_text:
            return "@baljotchohan23/technical-partner"
        if "@market-partner" in msg_text:
            return "@baljotchohan23/market-partner"
        if "@managing-partner" in msg_text:
            return "@baljotchohan23/managing-partner"
        return "@baljotchohan23/managing-partner"

    def _send(call_id, room, message):
        if expects_real_schema:
            handle = _resolve_mention_handle(message)
            tool_calls.append({
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "thenvoi_send_message",
                    "arguments": json.dumps({"content": message, "mentions": [handle]}),
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
    handoff_done = last_role in ("tool", "function") and "Message sent successfully" in last_content
    data_tool_result = last_role in ("tool", "function") and not handoff_done

    if handoff_done:
        response_content = final_reports.get(agent_name, "Processing complete.")
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
        elif agent_name == "managing_partner":
            if "thenvoi_send_message" in available_tool_names:
                # Scrape messages to see if we've received reports from partners
                recv_blob = " ".join(
                    str(m.get("content", "") or "")
                    for m in messages if m.get("role") == "user"
                )
                have_fin = "FINANCIAL ANALYSIS COMPLETE" in recv_blob
                have_leg = "LEGAL ANALYSIS COMPLETE" in recv_blob
                have_tech = "TECHNICAL ANALYSIS COMPLETE" in recv_blob
                have_mkt = "MARKET ANALYSIS COMPLETE" in recv_blob

                if have_fin and have_leg and have_tech and have_mkt:
                    # All reports are in, deliver final synthesized decision
                    response_content = final_reports["managing_partner"]
                else:
                    # Fresh trigger or partial reports: dispatch brief to partners
                    deal_id = sim_state.active_incident_id
                    sent_brief = deal_id in sim_state.dispatched_deals if deal_id else False

                    if not sent_brief:
                        # Dispatch parallel requests to all 4 partners
                        brief_co = sim_state.active_company_name or "NovaPay Inc"
                        _send("call_mp_fin", "finance-partner-room", f"@financial-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your financial due diligence now and report back to managing-partner-room.")
                        _send("call_mp_leg", "legal-partner-room", f"@legal-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your legal due diligence now and report back to managing-partner-room.")
                        _send("call_mp_tech", "tech-partner-room", f"@technical-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your technical due diligence now and report back to managing-partner-room.")
                        _send("call_mp_mkt", "market-partner-room", f"@market-partner New deal in committee: {brief_co} — Series A raise. Full pitch loaded in deal brief. Run your market due diligence now and report back to managing-partner-room.")
                        if deal_id:
                            sim_state.dispatched_deals.add(deal_id)
                    else:
                        response_content = "Managing Partner: awaiting specialist findings..."

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
