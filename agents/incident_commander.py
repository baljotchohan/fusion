# agents/incident_commander.py
"""
Agent 8: Incident Commander Agent (The brain).
Coordinates the entire autonomous defense pipeline. Recruits agents dynamically,
tracks the timeline, and triggers the Executive Decision boardroom for high-risk threats.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.incident_commander")

@tool
def build_incident_timeline(reports_summary: str) -> str:
    """Consolidates findings from Recon, Detection, and Malware agents into a single chronological timeline."""
    timeline = [
        {"time": "08:45:00Z", "event": "Phishing email detected targeting CEO workstation (Threat Intel)"},
        {"time": "08:47:32Z", "event": "CEO workstation compromised via Invoice attachment execution (Detection)"},
        {"time": "08:47:45Z", "event": "Malicious persistent registry key created (Malware)"},
        {"time": "08:49:12Z", "event": "Lateral movement connection established to database server IP (Recon)"}
    ]
    return json.dumps(timeline, indent=2)

@tool
def assess_escalation_needed(risk_score: float) -> str:
    """Assess if the combined threat risk score is high enough to mandate C-Suite / Executive boardroom escalation."""
    if risk_score >= 70.0:
        return "YES. Escalation is mandatory. Threat risk score matches critical threshold (>= 70)."
    return "NO. Standard automated containment is sufficient. Threat risk score is below 70."

@tool
def generate_status_update(current_stage: str) -> str:
    """Generate a high-level briefing of the current incident mitigation status."""
    return f"Incident Commander Status Briefing: Threat investigation completed. Stage: {current_stage}."

SYSTEM_PROMPT = """You are the Incident Commander (IC) for ARGUS — the Central Coordination Hub.
You are a seasoned CISO-level incident manager who coordinates multi-team cyber response.
You follow ICS (Incident Command System) protocols adapted for cybersecurity operations.

YOUR COORDINATION PROTOCOL:

PHASE 1 — INITIAL ALERT (when you receive a phishing alert from SOC-Alert-Sensor):
1. Acknowledge the alert and set incident severity to CRITICAL (pending assessment)
2. Call generate_status_update("PHASE 1: Initial Alert Received — assessing scope")
3. PARALLEL DISPATCH — send both messages using thenvoi_send_message:
   a. To room 'threat-intel-room': '@Threat-Intel ARGUS INCIDENT INITIATED. Analyze this alert: [full alert text]. Return threat report to incident-command-room.'
   b. To room 'recon-room': '@Recon ARGUS INCIDENT INITIATED. Map TechCorp network attack surface immediately. Report all vulnerable systems and exposed services to incident-command-room.'

PHASE 2 — AFTER THREAT INTEL AND RECON REPORT (you receive both reports):
1. Call build_incident_timeline() to begin chronological tracking
2. PARALLEL DISPATCH:
   a. To 'redteam-room': '@Red-Team Simulate attacker kill chain using this recon data: [recon_report]. Map full lateral movement path to CEO workstation and database. Report to incident-command-room.'
   b. To 'detection-room': '@Detection Scan email logs for sender domain from threat intel: [sender_domain]. Scan server logs for CEO workstation compromise evidence. Report all IOCs to incident-command-room.'
   c. To 'malware-room': '@Malware-Investigation Analyze suspicious attachment: [filename] hash: [hash]. Classify malware family, extract C2 IOCs, and provide containment commands. Report to incident-command-room.'

PHASE 3 — AFTER RED TEAM, DETECTION, AND MALWARE REPORTS:
1. Send to 'attack-path-room': '@Attack-Path Calculate final risk score using Red Team simulation and network topology. Identify crown jewels at risk. Report risk score and predicted next moves to incident-command-room.'

PHASE 4 — AFTER RISK SCORE RECEIVED (check score):
If risk score >= 70 (CRITICAL):
   PARALLEL DISPATCH:
   a. To 'blueteam-room': '@Blue-Team Generate prioritized defensive playbook. Use Red Team kill chain and Detection IOCs to build MITRE-mapped response. Include SOAR runbook commands. Report to incident-command-room.'
   b. To 'executive-room': '@Executive-Decision CRITICAL THREAT ESCALATION. Risk score: [score]/100. Convene boardroom for business decision. Full incident brief: [summary of all reports so far]. Report final CEO decision to incident-command-room.'

If risk score < 70:
   Send only to 'blueteam-room' (no executive escalation needed)

PHASE 5 — FINAL CONSOLIDATION (after Blue Team and Executive reports):
1. Call build_incident_timeline() with all collected reports
2. Call assess_escalation_needed() for final log
3. Call generate_status_update("PHASE 5: INCIDENT CONTAINED — all teams reported")
4. Compose and broadcast FINAL INCIDENT SUMMARY via thenvoi_send_event

CRITICAL RULES:
- Always forward FULL reports between agents, not summaries
- Track which reports you've received vs which are outstanding
- If an agent hasn't reported after expected time, re-dispatch to that room
- Always use @handles in messages: @Threat-Intel, @Recon, @Red-Team, @Attack-Path, @Detection, @Malware-Investigation, @Blue-Team, @Executive-Decision
- Your dispatches must include full context so each agent can work independently"""

class IncidentCommander(BaseAgent):
    def __init__(self):
        tools = [build_incident_timeline, assess_escalation_needed, generate_status_update]
        # Uses Gemini 1.5 Pro for maximum intelligence and coordination logic
        super().__init__(
            name="incident_commander",
            display_name="Incident Commander",
            room="incident-command-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash"
        )
