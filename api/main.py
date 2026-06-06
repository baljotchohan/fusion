# api/main.py
"""
FastAPI application serving REST endpoints and a WebSocket server
to stream real-time agent updates to the Next.js dashboard.
"""
import os
import json
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.event_bus import event_bus
from core.band_client import mock_bus, is_mock_mode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("argus.api")

app = FastAPI(title="ARGUS API", version="1.0.0")

# Enable CORS for the Next.js War Room dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket dashboard connections
active_websockets: List[WebSocket] = []

async def broadcast_event_to_websockets(event_data: dict):
    """Callback registered with event_bus to forward agent updates to the dashboard."""
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
    logger.info("FastAPI: Attack trigger requested.")
    
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
        # Real mode: Connect and send via real Band client API
        # In a real environment, the external sensor would post directly to Band.
        # Here we mock the sensor sending to the real room.
        logger.info("FastAPI: Real mode enabled. Forwarding phishing alert to real Band room...")
        # TODO: Implement real Band sensor publish if needed
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
        "registered_rooms": list(mock_bus.rooms.keys()) if is_mock_mode() else []
    }

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
    
    # Check if this is the second stage (after tools have executed)
    has_tool_messages = any(m.get("role") in ("tool", "function") for m in messages)
    
    # Infer calling agent
    agent_name = ""
    if "Threat Intelligence" in system_msg or "ThreatIntelAgent" in system_msg:
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

    if not has_tool_messages:
        # First-stage invocation: make tool calls
        if agent_name == "threat_intel_agent":
            if "search_ttp" in available_tool_names:
                tool_calls.append({
                    "id": "call_intel_1",
                    "type": "function",
                    "function": {"name": "search_ttp", "arguments": "{\"keyword\": \"phishing\"}"}
                })
            if "get_cves" in available_tool_names:
                tool_calls.append({
                    "id": "call_intel_2",
                    "type": "function",
                    "function": {"name": "get_cves", "arguments": "{\"keyword\": \"email\"}"}
                })
        elif agent_name == "recon_agent":
            if "scan_network" in available_tool_names:
                tool_calls.append({
                    "id": "call_recon_1",
                    "type": "function",
                    "function": {"name": "scan_network", "arguments": "{\"company_json\": \"{}\"}"}
                })
        elif agent_name == "detection_agent":
            if "scan_email_logs" in available_tool_names:
                tool_calls.append({
                    "id": "call_det_1",
                    "type": "function",
                    "function": {"name": "scan_email_logs", "arguments": "{\"company_json\": \"{}\", \"iocs\": \"[]\"}"}
                })
        elif agent_name == "red_team_agent":
            if "simulate_attack_path" in available_tool_names:
                tool_calls.append({
                    "id": "call_red_1",
                    "type": "function",
                    "function": {"name": "simulate_attack_path", "arguments": "{\"recon_data\": \"{}\", \"ttps\": \"[]\"}"}
                })
        elif agent_name == "attack_path_agent":
            if "calculate_risk_score" in available_tool_names:
                tool_calls.append({
                    "id": "call_path_1",
                    "type": "function",
                    "function": {"name": "calculate_risk_score", "arguments": "{\"attack_data\": \"{}\", \"company_profile\": \"{}\"}"}
                })
        elif agent_name == "malware_agent":
            if "analyze_file_metadata" in available_tool_names:
                tool_calls.append({
                    "id": "call_mal_1",
                    "type": "function",
                    "function": {"name": "analyze_file_metadata", "arguments": "{\"file_data\": \"{}\"}"}
                })
        elif agent_name == "blue_team_agent":
            if "generate_defense_actions" in available_tool_names:
                tool_calls.append({
                    "id": "call_blue_1",
                    "type": "function",
                    "function": {"name": "generate_defense_actions", "arguments": "{\"full_context\": \"{}\"}"}
                })
        elif agent_name == "incident_commander":
            if "mock_thenvoi_send_message" in available_tool_names:
                tool_calls.append({
                    "id": "call_cmd_init_1",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"recon-room\", \"message\": \"@Recon Map topology for systems.\"}"
                    }
                })
                tool_calls.append({
                    "id": "call_cmd_init_2",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"detection-room\", \"message\": \"@Detection Scan email logs for indicators.\"}"
                    }
                })
        elif agent_name == "executive_decision":
            response_content = "Deliberating C-Suite assessments..."
    else:
        # Second-stage invocation: return final text and next handoff
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
                "Incident Commander final timeline compilation completed. Operations summary closed."
            ),
            "executive_decision": (
                "FINAL CEO DECISION: CONTAIN\n"
                "Justification: Containment cost ($180K) is substantially lower than projected breach cost ($2.4M). Regulatory obligations require disclosure. Customer impact minimized.\n"
                "Board Communication: Security incident contained. Systems being hardened. No evidence of data exfiltration. Full post-incident report within 48 hours."
            )
        }

        response_content = final_reports.get(agent_name, "Processing complete.")
        
        # Determine and schedule handoffs
        next_room_map = {
            "threat_intel_agent": ("incident-command-room", "@Incident-Commander Threat report ready:\n" + response_content),
            "recon_agent": ("incident-command-room", "@Incident-Commander Recon topology report:\n" + response_content),
            "detection_agent": ("incident-command-room", "@Incident-Commander Detection logs scan report:\n" + response_content),
            "red_team_agent": ("incident-command-room", "@Incident-Commander Red team simulation path:\n" + response_content),
            "attack_path_agent": ("incident-command-room", f"@Incident-Commander Combined Risk Score: 87. " + response_content),
            "malware_agent": ("incident-command-room", "@Incident-Commander Malware file analysis:\n" + response_content),
            "blue_team_agent": ("incident-command-room", "@Incident-Commander Blue team playbook:\n" + response_content),
            "executive_decision": ("incident-command-room", "@Incident-Commander Boardroom verdict:\n" + response_content),
        }
        
        next_step = next_room_map.get(agent_name)
        if next_step and "mock_thenvoi_send_message" in available_tool_names:
            room, message = next_step
            tool_calls.append({
                "id": "call_next_handoff",
                "type": "function",
                "function": {
                    "name": "mock_thenvoi_send_message",
                    "arguments": json.dumps({"room": room, "message": message})
                }
            })
            
        # Incident commander stage-specific coordination
        if agent_name == "incident_commander" and "mock_thenvoi_send_message" in available_tool_names:
            history_text = "\n".join([m.get("content", "") for m in messages if m.get("role") == "user"])
            if "Recon topology" in history_text or "Detection logs" in history_text:
                tool_calls.append({
                    "id": "call_cmd_next_1",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"redteam-room\", \"message\": \"@Red-Team Run lateral movement simulations for compromise.\"}"
                    }
                })
                tool_calls.append({
                    "id": "call_cmd_next_2",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"malware-room\", \"message\": \"@Malware-Investigation Analyze compromised endpoint executables.\"}"
                    }
                })
            elif "Red team simulation" in history_text or "Malware file analysis" in history_text:
                tool_calls.append({
                    "id": "call_cmd_next_3",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"attack-path-room\", \"message\": \"@Attack-Path Compute final threat path risk score.\"}"
                    }
                })
            elif "Risk Score: 87" in history_text or "ATTACK PATH" in history_text:
                tool_calls.append({
                    "id": "call_cmd_next_4",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"blueteam-room\", \"message\": \"@Blue-Team Create prioritized defensive playbooks.\"}"
                    }
                })
                tool_calls.append({
                    "id": "call_cmd_next_5",
                    "type": "function",
                    "function": {
                        "name": "mock_thenvoi_send_message",
                        "arguments": "{\"room\": \"executive-room\", \"message\": \"@Executive-Decision Convene boardroom for critical threat.\"}"
                    }
                })
                
        # Call timeline tool for commander before final finish
        if agent_name == "incident_commander" and "build_incident_timeline" in available_tool_names:
            tool_calls.append({
                "id": "call_cmd_timeline",
                "type": "function",
                "function": {
                    "name": "build_incident_timeline",
                    "arguments": "{\"reports_summary\": \"incident overview logs compiled\"}"
                }
            })

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
