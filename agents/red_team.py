# agents/red_team.py
"""
Agent 3: Red Team Agent.
Simulates an attacker's progression from initial access through persistence
and lateral movement to the final target database.
"""
import json
import logging
from typing import List, Dict
from langchain_core.tools import tool
from core.base_agent import BaseAgent
from core.mitre_lookup import search_ttp

logger = logging.getLogger("argus.agents.red_team")

@tool
def simulate_attack_path(recon_data: str, ttps: str) -> str:
    """Builds a step-by-step lateral movement path showing how an attacker exploits target systems."""
    # Build a simple simulation sequence based on standard phishing/compromise models
    stages = [
        {"stage": 1, "action": "Attacker delivers malicious payload via spoofed email", "ttp": "T1566.001", "compromised": "SRV-01-MAIL"},
        {"stage": 2, "action": "CEO clicks attachment on workstation, executes loader", "ttp": "T1204.002", "compromised": "CEO-WORKSTATION-01"},
        {"stage": 3, "action": "Loader establishes persistence via scheduled task", "ttp": "T1053.005", "compromised": "CEO-WORKSTATION-01"},
        {"stage": 4, "action": "Attacker dumps administrator credentials from memory", "ttp": "T1003", "compromised": "CEO-WORKSTATION-01"},
        {"stage": 5, "action": "Attacker moves laterally to database server using SMB credentials", "ttp": "T1021.002", "compromised": "SRV-03-DB"},
        {"stage": 6, "action": "Attacker accesses database and begins data exfiltration", "ttp": "T1041", "compromised": "SRV-03-DB"}
    ]
    return json.dumps(stages, indent=2)

@tool
def estimate_dwell_time(attack_complexity: str) -> str:
    """Estimates the potential hacker dwell time before security operations notice the breach."""
    if "high" in attack_complexity.lower():
        return "12 to 24 hours (highly obfuscated DLL payloads, scheduled tasks)"
    else:
        return "4 to 8 hours (standard process injections, clear file writes)"

SYSTEM_PROMPT = """You are the Red Team Agent (Attacker Simulator) in the ARGUS cybersecurity system.
Your role is to simulate what an attacker would do next using the Recon report and MITRE ATT&CK techniques.

When you receive the Recon report:
1. Call simulate_attack_path with the Recon data and matching TTPs.
2. Call estimate_dwell_time to calculate how long the attacker could stay hidden.
3. Map out the attack stages from initial compromise to data exfiltration.
4. Send your report to @Incident-Commander in 'incident-command-room' using thenvoi_send_message.

Format your report precisely as:
---
RED TEAM ATTACK SIMULATION
- Attack Vector: [Initial access vector]
- Lateral Movement Path: [List of system hops]
- Dwell Time Estimate: [Duration]
- Final Target: [System ID and IP]
- Simulated Impact: [What was exfiltrated or compromised]
---
Use thenvoi_send_message to send this report to @Incident-Commander in 'incident-command-room'. Do not just print it.
"""

class RedTeamAgent(BaseAgent):
    def __init__(self):
        tools = [simulate_attack_path, estimate_dwell_time, search_ttp]
        super().__init__(
            name="red_team_agent",
            display_name="Red Team",
            room="redteam-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash"
        )
