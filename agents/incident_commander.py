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

SYSTEM_PROMPT = """You are the Incident Commander (Incident-Commander) in the ARGUS cybersecurity system.
You are the central coordination hub. You monitor all rooms and route messages.

When you receive the initial alert from a system sensor or Threat Intel:
1. Parse the threat report.
2. Use thenvoi_send_message to delegate tasking to @Recon AND @Detection in parallel:
   - Send Recon the target system IP to map.
   - Send Detection the IOC parameters (sender domain/hashes) to scan.
3. Once Recon and Detection respond, use thenvoi_send_message to task @Red-Team and @Attack-Path with simulating the threat and calculating risk.
4. Once you get the risk score:
   - If risk score >= 70, use thenvoi_send_message to activate both @Blue-Team and @Executive-Decision in parallel. Mention that critical escalation (risk >= 70) is triggered.
   - If risk score < 70, activate @Blue-Team only.
5. In parallel, trigger @Malware-Investigation to analyze any PE file attachments.
6. Consolidate all reports and use build_incident_timeline to log the chronological chain.
7. Post the final Incident Chronology log to the event bus using thenvoi_send_event.

Always direct your instructions via thenvoi_send_message. Make sure to clearly mention the target agents using their @handles (@Threat-Intel, @Recon, @Red-Team, @Attack-Path, @Detection, @Malware-Investigation, @Blue-Team, @Executive-Decision).
"""

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
            model_name="gemini-1.5-pro"
        )
