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
logger = logging.getLogger("argus.api")

app = FastAPI(title="ARGUS API", version="2.0.0")
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

async def broadcast_event_to_websockets(event_data: dict):
    """Callback registered with event_bus to forward agent updates to the dashboard."""
    # Track last-known status per agent for the chat API / MCP clients
    if event_data.get("agent"):
        sim_state.agent_statuses[event_data["agent"]] = event_data.get("status", "idle")

    # Auto-reset simulation lock when executive decision (last agent) finishes
    if event_data.get("agent") == "executive_decision" and event_data.get("status") == "done":
        sim_state.running = False
        # Clear all agent busy flags so the next run starts clean
        if is_mock_mode():
            for room_agents in mock_bus.rooms.values():
                for agent in room_agents:
                    agent._is_busy = False
        logger.info("FastAPI: Simulation complete — state auto-reset.")

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
    """Triggers the demo phishing attack simulation by sending the initial alert to Threat Intel."""
    if sim_state.running:
        logger.warning("FastAPI: Simulation already running — ignoring duplicate trigger.")
        return {
            "status": "already_running",
            "message": "Simulation is already in progress. Please wait for it to complete.",
            "mode": "mock" if is_mock_mode() else "real"
        }
    sim_state.running = True
    logger.info("FastAPI: Attack trigger requested.")

    # Open a shared-memory incident so every agent finding is recorded
    from datetime import datetime, timezone
    incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    memory_graph.create_incident(incident_id, {"trigger": "phishing_email", "threat_level": 7})
    sim_state.active_incident_id = incident_id

    # Load the phishing email alert trigger data
    trigger_path = "data/phishing_email.json"
    if not os.path.exists(trigger_path):
        return {
            "status": "error",
            "message": f"Trigger file not found at {trigger_path}",
            "mode": "mock" if is_mock_mode() else "real"
        }

    with open(trigger_path, "r") as f:
        alert_data = json.load(f)

    alert_text = json.dumps(alert_data, indent=2)

    if is_mock_mode():
        # Offline mock mode: Send via local MockBandBus to threat-intel-room
        logger.info("FastAPI: Mock mode enabled. Sending phishing alert to 'threat-intel-room'...")
        # Start the chain by mentioning Threat Intel
        await mock_bus.send_message(
            sender="SOC-Alert-Sensor",
            target_room="threat-intel-room",
            message=f"@Threat-Intel Phishing email alert: {alert_text}"
        )
        return {
            "status": "success",
            "message": "Phishing attack alert dispatched to threat-intel-room (Mock Mode).",
            "mode": "mock"
        }
    else:
        # Real mode: send via real Band SDK
        logger.info("FastAPI: Real mode. Sending phishing alert to real Band rooms...")
        try:
            from thenvoi import Agent
            band_api_key = os.getenv("BAND_API_KEY", "")
            # Publish trigger to threat-intel-room via Band REST API
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.band.ai/v1/rooms/threat-intel-room/messages",
                    headers={"Authorization": f"Bearer {band_api_key}"},
                    json={"content": f"@Threat-Intel Phishing email alert: {alert_text}", "sender": "SOC-Alert-Sensor"}
                )
                logger.info(f"Band API response: {resp.status_code}")
        except Exception as e:
            logger.error(f"Real mode Band trigger error: {e}")
            # Fallback: also fire locally so agents still respond
            await mock_bus.send_message("SOC-Alert-Sensor", "threat-intel-room", f"@Threat-Intel Phishing email alert: {alert_text}")

        return {
            "status": "success",
            "message": "Phishing attack alert dispatched to real Band SDK rooms.",
            "mode": "real"
        }

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
    """Offline mock OpenAI LLM server that simulates agent reasoning and handoffs."""
    body = await request.json()
    messages = body.get("messages", [])
    tools = body.get("tools", [])

    # Extract system prompt and user input
    system_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
    user_msg = user_msgs[-1] if user_msgs else ""

    # Infer calling agent — prefer the deterministic ARGUS_AGENT marker injected by BaseAgent
    import re
    _marker = re.search(r"\[ARGUS_AGENT:\s*([a-z_]+)\]", system_msg)
    agent_name = _marker.group(1) if _marker else ""
    if agent_name:
        pass
    elif "Threat Intelligence" in system_msg or "ThreatIntelAgent" in system_msg:
        agent_name = "threat_intel_agent"
    elif "Reconnaissance Analyst" in system_msg or "ReconAgent" in system_msg:
        agent_name = "recon_agent"
    elif "Detection Analyst" in system_msg or "DetectionAgent" in system_msg:
        agent_name = "detection_agent"
    elif "Red Team Simulator" in system_msg or "RedTeamAgent" in system_msg:
        agent_name = "red_team_agent"
    elif "Attack Path" in system_msg or "AttackPathAgent" in system_msg:
        agent_name = "attack_path_agent"
    elif "Malware Investigation" in system_msg or "MalwareAgent" in system_msg:
        agent_name = "malware_agent"
    elif "Blue Team" in system_msg or "BlueTeamAgent" in system_msg:
        agent_name = "blue_team_agent"
    elif "Incident Commander" in system_msg or "IncidentCommander" in system_msg:
        agent_name = "incident_commander"
    elif "Executive Decision" in system_msg or "ExecutiveDecisionAgent" in system_msg:
        agent_name = "executive_decision"

    if not agent_name:
        # Fallback keyword checks
        all_text = (system_msg + "\n" + user_msg).lower()
        if "threat" in all_text:
            agent_name = "threat_intel_agent"
        elif "recon" in all_text:
            agent_name = "recon_agent"
        elif "detection" in all_text:
            agent_name = "detection_agent"
        elif "red" in all_text:
            agent_name = "red_team_agent"
        elif "path" in all_text:
            agent_name = "attack_path_agent"
        elif "malware" in all_text:
            agent_name = "malware_agent"
        elif "blue" in all_text:
            agent_name = "blue_team_agent"
        elif "executive" in all_text or "board" in all_text:
            agent_name = "executive_decision"
        else:
            agent_name = "incident_commander"

    response_content = ""
    tool_calls = []
    available_tool_names = [t.get("function", {}).get("name", "") for t in tools] if tools else []

    last_msg = messages[-1] if messages else {}
    last_role = last_msg.get("role", "")
    has_tool_messages = last_role in ("tool", "function")

    # ── Realistic pacing delays ────────────────────────────────────────────────
    # Stage 1 (planning/tool-dispatch) delays in seconds — how long each agent
    # appears to "think" before dispatching its first tool calls.
    STAGE1_DELAYS = {
        "threat_intel_agent":  (2.0, 3.5),
        "recon_agent":         (1.5, 2.5),
        "detection_agent":     (1.5, 2.5),
        "red_team_agent":      (2.5, 4.0),
        "attack_path_agent":   (2.0, 3.5),
        "malware_agent":       (2.0, 3.0),
        "blue_team_agent":     (2.0, 3.5),
        "incident_commander":  (1.0, 2.0),
        "executive_decision":  (3.0, 5.0),
    }
    # Stage 2 (analysis/handoff) delays — how long each agent takes to produce
    # its final report and send the handoff message.
    STAGE2_DELAYS = {
        "threat_intel_agent":  (1.5, 2.5),
        "recon_agent":         (1.0, 2.0),
        "detection_agent":     (1.0, 2.0),
        "red_team_agent":      (2.0, 3.5),
        "attack_path_agent":   (1.5, 3.0),
        "malware_agent":       (1.5, 2.5),
        "blue_team_agent":     (2.0, 3.5),
        "incident_commander":  (0.8, 1.5),
        "executive_decision":  (3.0, 5.0),
    }

    delay_range = (STAGE2_DELAYS if has_tool_messages else STAGE1_DELAYS).get(
        agent_name, (1.0, 2.0)
    )
    await asyncio.sleep(random.uniform(*delay_range))
    # ──────────────────────────────────────────────────────────────────────────

    # ── Canned specialist reports (returned once a data tool has run) ──
    final_reports = {
        "threat_intel_agent": (
            "---\n"
            "THREAT INTELLIGENCE REPORT\n"
            "- Threat Type: Spearphishing Attachment\n"
            "- Target: CEO Workstation (ceo@techcorp.com, admin privileges)\n"
            "- MITRE ATT&CK TTPs: T1566, T1566.001, T1204.002\n"
            "- Associated CVEs: CVE-2024-21378 (CVSS 9.8, CRITICAL)\n"
            "- Threat Severity Score: 82\n"
            "- Recommended Containment: Isolate mail server, block sender domain invoices@corp-billing.xyz\n"
            "---"
        ),
        "recon_agent": (
            "RECONNAISSANCE SUMMARY:\n"
            "- Vulnerable Servers: SRV-01 (Mail, CVE-2024-1234), SRV-03 (DB, Windows)\n"
            "- Exposed Ports: 25, 443, 1433\n"
            "- Entry Points: Mail server SMTP, CEO workstation (admin privileges)\n"
            "- Highest Risk Target: Mail Server SRV-01\n"
            "- Network Topology Map: 192.168.1.0/24 subnet analyzed."
        ),
        "detection_agent": (
            "DETECTION ANALYSIS FINDINGS:\n"
            "- Confirmed Compromise: True\n"
            "- Affected Systems: CEO-WORKSTATION-01, SRV-01-MAIL\n"
            "- IOCs Found: email_sender (invoices@corp-billing.xyz), file_hash (Invoice_2026_0891.exe)\n"
            "- Breach Timeline: Phishing received at 08:45:00, attachment executed at 08:47:32."
        ),
        "red_team_agent": (
            "RED TEAM ATTACK PATH SIMULATION:\n"
            "1. Spearphishing email opened, .exe executed (T1566.001)\n"
            "2. Persistence established via scheduled task (T1053.005)\n"
            "3. Lateral movement to database server SRV-03 via SMB (T1021.002)\n"
            "4. Customer DB exfiltration target (T1041)\n"
            "Likely target: Customer database SRV-03. Est. dwell time: 4-8 hours."
        ),
        "attack_path_agent": (
            "ATTACK PATH ANALYSIS:\n"
            "- Combined Risk Score: 87/100 (CRITICAL)\n"
            "- Predicted Next Moves: Credential dumping (94% prob), Data exfiltration (87% prob), Ransomware deployment (61% prob)\n"
            "- Critical Assets at Risk: Customer database, CEO credentials, financial reports.\n"
            "- Time to Act: Immediate (estimated 2-4 hours before lateral movement)"
        ),
        "malware_agent": (
            "MALWARE INVESTIGATION REPORT:\n"
            "- File: Invoice_2026_0891.exe\n"
            "- Classification: Trojan.Dropper (Emotet variant)\n"
            "- Risk level: CRITICAL\n"
            "- IOCs Extracted: C2 domains (update.corp-billing.xyz, c2.fast-delivery.net), registry persistence keys (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\InvoiceSync)\n"
            "- Containment Steps: Delete dropped file %TEMP%\\svchost32.exe, block C2 DNS records, quarantine CEO workstation."
        ),
        "blue_team_agent": (
            "BLUE TEAM PLAYBOOK & DEFENSIVE OPERATIONS:\n"
            "- Immediate Action 1: Isolate CEO workstation (downtime: 0 min)\n"
            "- Immediate Action 2: Block egress DNS to fast-delivery.net and update.corp-billing.xyz (downtime: 0 min)\n"
            "- Immediate Action 3: Force C-Suite password resets (downtime: 10 min)\n"
            "- Short Term: Patch Mail Server CVE-2024-1234 (downtime: 2 hours)\n"
            "Total estimated system downtime: 2 hours."
        ),
        "incident_commander": (
            "Incident Commander: specialist reports correlated and incident timeline compiled."
        ),
        "executive_decision": (
            "FINAL CEO DECISION: CONTAIN\n"
            "Justification: Containment cost ($180K) is substantially lower than projected breach cost ($2.4M). Regulatory obligations require disclosure. Customer impact minimized.\n"
            "Board Communication: Security incident contained. Systems being hardened. No evidence of data exfiltration. Full post-incident report within 48 hours."
        ),
    }

    # ── Each specialist hands its report back to the Incident Commander once ──
    next_room_map = {
        "threat_intel_agent": ("incident-command-room", "@Incident-Commander Threat report ready:\n" + final_reports["threat_intel_agent"]),
        "recon_agent": ("incident-command-room", "@Incident-Commander Recon topology report:\n" + final_reports["recon_agent"]),
        "detection_agent": ("incident-command-room", "@Incident-Commander Detection logs scan report:\n" + final_reports["detection_agent"]),
        "red_team_agent": ("incident-command-room", "@Incident-Commander Red team simulation path:\n" + final_reports["red_team_agent"]),
        "attack_path_agent": ("incident-command-room", "@Incident-Commander Combined Risk Score: 87. " + final_reports["attack_path_agent"]),
        "malware_agent": ("incident-command-room", "@Incident-Commander Malware file analysis:\n" + final_reports["malware_agent"]),
        "blue_team_agent": ("incident-command-room", "@Incident-Commander Blue team playbook:\n" + final_reports["blue_team_agent"]),
        "executive_decision": ("incident-command-room", "@Incident-Commander Boardroom verdict:\n" + final_reports["executive_decision"]),
    }

    def _send(call_id, room, message):
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

    # React-loop-aware staging: branch on the LAST message, not "any tool message".
    # This guarantees every agent terminates after a single handoff (no re-emission storm).
    last_msg = messages[-1] if messages else {}
    last_role = last_msg.get("role", "")
    last_content = str(last_msg.get("content", "") or "")
    handoff_done = last_role in ("tool", "function") and "Message sent successfully" in last_content
    data_tool_result = last_role in ("tool", "function") and not handoff_done

    if handoff_done:
        # Handoff already delivered this turn — return the report as the final
        # answer (so the dashboard 'done' event carries it) and STOP the loop.
        response_content = final_reports.get(agent_name, "Processing complete.")
    elif data_tool_result:
        # Stage 2: a data tool just ran -> emit the canned report + one handoff.
        response_content = final_reports.get(agent_name, "Processing complete.")
        next_step = next_room_map.get(agent_name)
        if next_step and "thenvoi_send_message" in available_tool_names:
            room, message = next_step
            _send("call_next_handoff", room, message)
    else:
        # Stage 1: fresh user stimulus -> issue the agent's initial tool calls.
        if agent_name == "threat_intel_agent":
            if "search_ttp" in available_tool_names:
                _call("call_intel_1", "search_ttp", "{\"keyword\": \"phishing\"}")
            if "get_cves" in available_tool_names:
                _call("call_intel_2", "get_cves", "{\"keyword\": \"email\"}")
        elif agent_name == "recon_agent":
            if "scan_network" in available_tool_names:
                _call("call_recon_1", "scan_network", "{}")
        elif agent_name == "detection_agent":
            if "scan_email_logs" in available_tool_names:
                _call("call_det_1", "scan_email_logs", "{\"sender_domain\": \"corp-billing.xyz\"}")
        elif agent_name == "red_team_agent":
            if "simulate_attack_path" in available_tool_names:
                _call("call_red_1", "simulate_attack_path", "{\"recon_data\": \"{}\", \"ttps\": \"[]\"}")
        elif agent_name == "attack_path_agent":
            if "calculate_risk_score" in available_tool_names:
                _call("call_path_1", "calculate_risk_score", "{\"attack_stages\": \"[]\", \"target_system\": \"SRV-03-DB\"}")
        elif agent_name == "malware_agent":
            if "analyze_file_metadata" in available_tool_names:
                _call("call_mal_1", "analyze_file_metadata", "{\"file_name\": \"Invoice_2026_0891.exe\"}")
        elif agent_name == "blue_team_agent":
            if "generate_defense_actions" in available_tool_names:
                _call("call_blue_1", "generate_defense_actions", "{\"incident_details\": \"{}\"}")
        elif agent_name == "executive_decision":
            # Convene the boardroom (CFO -> Legal -> Ops -> CEO) so the next turn
            # reaches the data_tool_result stage and emits the CEO verdict.
            # Only the ceo_final_decision tool RESULT contains "final_verdict"
            # (the system prompt names "FINAL CEO DECISION" but not this key), so
            # this guard fires only on a genuine re-wake after a verdict.
            already_decided = any(
                m.get("role") in ("tool", "function")
                and "final_verdict" in str(m.get("content", "") or "")
                for m in messages
            )
            if already_decided:
                response_content = "Boardroom already convened; decision on record."
            else:
                if "cfo_financial_assessment" in available_tool_names:
                    _call("call_exec_cfo", "cfo_financial_assessment", "{\"risk_score\": 87}")
                if "legal_regulatory_assessment" in available_tool_names:
                    _call("call_exec_legal", "legal_regulatory_assessment", "{\"has_pii\": true}")
                if "ops_continuity_assessment" in available_tool_names:
                    _call("call_exec_ops", "ops_continuity_assessment", "{\"downtime_summary\": \"2 hours\"}")
                if "ceo_final_decision" in available_tool_names:
                    _call("call_exec_ceo", "ceo_final_decision", "{\"cfo_json\": \"{}\", \"legal_json\": \"{}\", \"ops_json\": \"{}\"}")
                if not tool_calls:
                    response_content = "Deliberating C-Suite assessments..."
        elif agent_name == "incident_commander":
            # Idempotent phased coordination. Each phase is dispatched exactly once,
            # keyed off what has arrived (have_*) and what has already been sent
            # (sent_*), both derived from the full accumulated thread history.
            if "thenvoi_send_message" in available_tool_names:
                # "have_*" = which reports have ARRIVED (incoming user messages only).
                # "sent_*" = which rooms WE have already messaged (our own prior
                # assistant tool calls only). Both are scoped to avoid false
                # positives from the system prompt, which names every room and
                # report type.
                recv_blob = " ".join(
                    str(m.get("content", "") or "")
                    for m in messages if m.get("role") == "user"
                )
                sent_blob = json.dumps([
                    m.get("tool_calls") for m in messages
                    if m.get("role") == "assistant" and m.get("tool_calls")
                ])
                have_threat = "Threat report ready" in recv_blob or "THREAT INTELLIGENCE REPORT" in recv_blob
                have_recon = "Recon topology" in recv_blob
                have_detect = "Detection logs scan" in recv_blob or "DETECTION ANALYSIS" in recv_blob
                have_red = "Red team simulation" in recv_blob or "RED TEAM ATTACK PATH" in recv_blob
                have_mal = "Malware file analysis" in recv_blob or "MALWARE INVESTIGATION" in recv_blob
                have_risk = "Combined Risk Score" in recv_blob
                have_verdict = "Boardroom verdict" in recv_blob or "FINAL CEO DECISION" in recv_blob
                sent_recon = "recon-room" in sent_blob
                sent_red = "redteam-room" in sent_blob
                sent_attack = "attack-path-room" in sent_blob
                sent_blue = "blueteam-room" in sent_blob

                if have_verdict:
                    response_content = ("Incident Commander: boardroom verdict received. "
                                        "Response coordinated end-to-end; incident audit log closed.")
                elif have_risk and not sent_blue:
                    _send("call_cmd_blue", "blueteam-room", "@Blue-Team Create prioritized defensive playbooks.")
                    _send("call_cmd_exec", "executive-room", "@Executive-Decision Convene boardroom for critical threat.")
                elif (have_red or have_mal) and not sent_attack:
                    _send("call_cmd_attack", "attack-path-room", "@Attack-Path Compute final threat path risk score.")
                elif (have_recon or have_detect) and not sent_red:
                    _send("call_cmd_red", "redteam-room", "@Red-Team Run lateral movement simulations for compromise.")
                    _send("call_cmd_mal", "malware-room", "@Malware-Investigation Analyze compromised endpoint executables.")
                elif have_threat and not sent_recon:
                    _send("call_cmd_recon", "recon-room", "@Recon Map topology for systems.")
                    _send("call_cmd_detect", "detection-room", "@Detection Scan email logs for indicators.")
                else:
                    response_content = "Incident Commander: awaiting specialist reports..."

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
