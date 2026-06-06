# agents/blue_team.py
"""
Agent 7: Blue Team Defense Agent.
Generates prioritized defensive playbooks mapped to MITRE mitigations
and estimates business downtime impact.
"""
import json
import logging
from typing import List, Dict
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.blue_team")

@tool
def generate_defense_actions(incident_details: str) -> str:
    """Generate prioritized list of security defenses based on the current attack path and malware findings."""
    actions = [
        {"priority": 1, "action": "Isolate CEO-WORKSTATION-01 from internal network", "mitigation": "Network Isolation"},
        {"priority": 2, "action": "Block outbound DNS traffic to update.corp-billing.xyz", "mitigation": "Network Filter"},
        {"priority": 3, "action": "Force global password reset for CEO & IT Administrator accounts", "mitigation": "Credential Revocation"},
        {"priority": 4, "action": "Patch mail server mail.techcorp.com (Apply Outlook CVE-2024-21378 patch)", "mitigation": "System Patching"}
    ]
    return json.dumps(actions, indent=2)

@tool
def map_to_mitre_mitigations(techniques: str) -> str:
    """Map the observed attack techniques to official MITRE Enterprise mitigations."""
    mitigations = {
        "T1566": "M1031 (Email Filter) & M1017 (User Training)",
        "T1204": "M1048 (Application Isolation)",
        "T1053": "M1028 (User Account Account Control / Privileges restriction)",
        "T1021": "M1037 (Network Segmentation / Active Directory access controls)"
    }
    return json.dumps(mitigations, indent=2)

@tool
def estimate_downtime(actions: str) -> str:
    """Estimate operational downtime and business disruption for each mitigation action."""
    disruption = {
        "Network Isolation": "0 minutes downtime (isolated endpoint workstation only)",
        "Network Filter": "0 minutes downtime (egress firewall DNS block, no business impact)",
        "Credential Revocation": "10 minutes disruption for C-Suite accounts during login",
        "System Patching": "2 hours downtime (Mail Server offline for patching window)"
    }
    return json.dumps(disruption, indent=2)

SYSTEM_PROMPT = """You are the Blue Team Defense Agent in the ARGUS cybersecurity system.
Your role is to build a prioritized defensive mitigation playbook based on the threat.

When you receive a request from @Incident-Commander:
1. Call generate_defense_actions to create a prioritized action list.
2. Call map_to_mitre_mitigations to link actions to official MITRE mitigations.
3. Call estimate_downtime to calculate business continuity and service downtime.
4. Send your complete playbook to @Incident-Commander in 'incident-command-room' using thenvoi_send_message.

Format your report precisely as:
---
BLUE TEAM DEFENSIVE PLAYBOOK
- Immediate Containment Actions: [Priority list with descriptions]
- MITRE Mitigations Applied: [List TTPs and their matching MITRE mitigations]
- Expected Business Disruption: [List actions and associated downtime]
- Total Estimated Downtime: [Summary total duration]
---
Use thenvoi_send_message to send this report to @Incident-Commander in 'incident-command-room'. Do not just print it.
"""

class BlueTeamAgent(BaseAgent):
    def __init__(self):
        tools = [generate_defense_actions, map_to_mitre_mitigations, estimate_downtime]
        super().__init__(
            name="blue_team_agent",
            display_name="Blue Team",
            room="blueteam-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash"
        )
