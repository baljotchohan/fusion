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

    # ── Canned FUSION partner reports ──
    final_reports = {
        "financial_partner": (
            "FINANCIAL DUE DILIGENCE REPORT — NovaPay Inc\n"
            "Partner: Financial Analysis\n"
            "Confidence: HIGH\n\n"
            "REVENUE QUALITY:\n"
            "- 78% of ARR ($3.9M of $5M ARR) is concentrated in a single customer (Amazon).\n"
            "- Amazon contract expires in 3 months (post-close cliff-edge).\n"
            "- Gross margins are 48% (below SaaS benchmark of 70%+).\n\n"
            "BURN & RUNWAY:\n"
            "- Cash on hand is $3.0M with a monthly burn rate of $380k.\n"
            "- Implies only 8 months of runway remaining.\n\n"
            "UNIT ECONOMICS:\n"
            "- LTV:CAC ratio is 2.5x, which is below the 3.0x Series A threshold.\n"
            "- Customer payback period is 16 months.\n\n"
            "VALUATION:\n"
            "- 8.0x ARR valuation multiple on a declining fintech sector.\n\n"
            "🚨 CRITICAL RED FLAGS:\n"
            "1. Amazon revenue concentration (78% ARR) is a critical point of failure.\n"
            "2. Amazon contract expires 3 months post-close with high renewal risk.\n"
            "3. Remaining runway of 8 months is extremely tight.\n\n"
            "FINANCIAL RISK SCORE: 9/10\n"
            "RECOMMENDATION: PASS"
        ),
        "legal_partner": (
            "LEGAL DUE DILIGENCE REPORT — NovaPay Inc\n"
            "Partner: Legal Analysis\n"
            "Confidence: HIGH\n\n"
            "LITIGATION:\n"
            "- Active patent infringement lawsuit by Klarna claiming $8.0M in damages (80% of the proposed $10M raise).\n\n"
            "COMPLIANCE & LICENSING:\n"
            "- Non-compliant with new CFPB rules effective January 2026.\n"
            "- Operating without money transmitter licenses in 4 states (CA, NY, TX, FL).\n\n"
            "IP & DATA PRIVACY:\n"
            "- Lacks SOC2 certification, blocking enterprise growth.\n"
            "- CCPA compliance is unverified.\n\n"
            "FOUNDER HISTORY:\n"
            "- CEO's prior startup was under SEC investigation (now closed, but remains a diligence flag).\n\n"
            "🚨 CRITICAL RED FLAGS:\n"
            "1. Klarna patent lawsuit ($8.0M damages) is an immediate dealbreaker.\n"
            "2. Lacking money transmitter licenses in 4 key states of operation.\n"
            "3. Non-compliant with CFPB rules since January 2026.\n\n"
            "LEGAL RISK SCORE: 10/10\n"
            "RECOMMENDATION: PASS"
        ),
        "technical_partner": (
            "TECHNICAL DUE DILIGENCE REPORT — NovaPay Inc\n"
            "Partner: Technical Audit\n"
            "Confidence: HIGH\n\n"
            "TECH STACK:\n"
            "- Node.js 14 (End-of-Life since Oct 2023) and MongoDB 4.2 in production, exposing critical vulnerabilities.\n\n"
            "SECURITY POSTURE:\n"
            "- Plaintext storage of SSNs and PII in database.\n"
            "- Never conducted a penetration test or external vulnerability audit.\n"
            "- Undisclosed 2024 data breach (3,200 user records) was not reported to authorities.\n\n"
            "SCALABILITY & DEBT:\n"
            "- Monolithic code architecture unable to horizontally scale past 10,000 active users.\n"
            "- No multi-factor authentication (MFA) enabled on admin panels.\n\n"
            "🚨 CRITICAL RED FLAGS:\n"
            "1. Storing SSNs and PII in plaintext MongoDB is a massive liability.\n"
            "2. Running EOL Node.js 14 and MongoDB 4.2 in a live payment processor.\n"
            "3. Undisclosed 2024 data breach (3,200 records).\n\n"
            "TECHNICAL RISK SCORE: 10/10\n"
            "RECOMMENDATION: PASS"
        ),
        "market_partner": (
            "MARKET DUE DILIGENCE REPORT — NovaPay Inc\n"
            "Partner: Market Research\n"
            "Confidence: HIGH\n\n"
            "TAM & GROWTH:\n"
            "- TAM claim is top-down and unvalidated.\n"
            "- US Buy Now Pay Later (BNPL) sector is shrinking at 12% YoY, contradicting the founder's 200% growth claims.\n\n"
            "COMPETITIVE LANDSCAPE:\n"
            "- Severe competitive pressure from Affirm ($8B), Klarna ($6.7B), and Block.\n"
            "- Defensibility score is 8/25 (no real proprietary moat or switching costs).\n\n"
            "SECTOR TIMING & REGULATION:\n"
            "- Sector venture funding is down 67% YoY.\n"
            "- CFPB credit reporting mandate effective Q3 2026 will restrict BNPL usage by 15-25%.\n\n"
            "🚨 CRITICAL RED FLAGS:\n"
            "1. Shrinking US BNPL sector (12% decline YoY) contradicts growth claims.\n"
            "2. High competition with well-capitalized incumbents (Klarna, Affirm).\n"
            "3. Negative sector timing with VC funding down 67% YoY.\n\n"
            "MARKET RISK SCORE: 8/10\n"
            "RECOMMENDATION: PASS"
        ),
        "managing_partner": (
            "╔══════════════════════════════════════════════════════════╗\n"
            "║         FUSION INVESTMENT COMMITTEE DECISION             ║\n"
            "╠══════════════════════════════════════════════════════════╣\n"
            "║ Company:    NovaPay Inc                                  ║\n"
            "║ Deal:       $10,000,000 Series A at $40,000,000 post     ║\n"
            "╠══════════════════════════════════════════════════════════╣\n"
            "║  DECISION:    PASS                                       ║\n"
            "║  CONFIDENCE:  91%                                        ║\n"
            "╚══════════════════════════════════════════════════════════╝\n\n"
            "RISK SCORECARD:\n"
            "  Financial Risk:  9/10  (weight: 30%) → 2.70\n"
            "  Legal Risk:     10/10  (weight: 25%) → 2.50\n"
            "  Technical Risk: 10/10  (weight: 25%) → 2.50\n"
            "  Market Risk:     8/10  (weight: 20%) → 1.60\n"
            "  ─────────────────────────────────────────────\n"
            "  WEIGHTED SCORE:  9.3/10\n\n"
            "PRIMARY REASONS:\n"
            "1. Klarna patent lawsuit ($8M potential damages = 80% of raise) is an existential risk that must be resolved before any capital is deployed.\n"
            "2. Amazon client concentration (78% ARR) with contract expiry 3 months post-close creates a cliff-edge revenue scenario.\n"
            "3. Security posture (no PCI-DSS, plaintext PII, no pentest, undisclosed breach) is pre-catastrophe for a licensed payments processor."
        ),
    }

    # Handoff mappings for mock bus
    next_room_map = {
        "financial_partner": ("managing-partner-room", "@managing-partner FINANCIAL ANALYSIS COMPLETE. Risk Score: 9/10. PASS. Amazon client concentration (78% ARR) with contract expiry in 3 months."),
        "legal_partner": ("managing-partner-room", "@managing-partner LEGAL ANALYSIS COMPLETE. Risk Score: 10/10. PASS. Klarna patent lawsuit ($8M damages) and missing money transmitter licenses in 4 states."),
        "technical_partner": ("managing-partner-room", "@managing-partner TECHNICAL ANALYSIS COMPLETE. Risk Score: 10/10. PASS. SSNs stored in plaintext, EOL software in production, and undisclosed 2024 data breach."),
        "market_partner": ("managing-partner-room", "@managing-partner MARKET ANALYSIS COMPLETE. Risk Score: 8/10. PASS. Sector shrinking 12% YoY, and upcoming CFPB mandate will restrict BNPL usage."),
    }

    # When the user uploaded a different company, let the canned demo narrative
    # follow that company's name instead of the stock NovaPay storyline.
    active_co = sim_state.active_company_name
    if active_co and active_co != "NovaPay Inc":
        final_reports = {k: v.replace("NovaPay Inc", active_co) for k, v in final_reports.items()}
        next_room_map = {k: (room, m.replace("NovaPay Inc", active_co)) for k, (room, m) in next_room_map.items()}

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
