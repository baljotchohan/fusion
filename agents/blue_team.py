# agents/blue_team.py
"""
Agent 7: Blue Team Defense Agent.
Generates prioritized defensive playbooks mapped to MITRE mitigations
and estimates business downtime impact.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.blue_team")

@tool
def generate_defense_actions(incident_details: Optional[str] = None) -> str:
    """Generate prioritized list of security defenses based on the current attack path and malware findings."""
    actions = [
        {"priority": 1, "action": "Isolate CEO-WORKSTATION-01 from internal network", "mitigation": "Network Isolation"},
        {"priority": 2, "action": "Block outbound DNS traffic to update.corp-billing.xyz", "mitigation": "Network Filter"},
        {"priority": 3, "action": "Force global password reset for CEO & IT Administrator accounts", "mitigation": "Credential Revocation"},
        {"priority": 4, "action": "Patch mail server mail.techcorp.com (Apply Outlook CVE-2024-21378 patch)", "mitigation": "System Patching"}
    ]
    return json.dumps(actions, indent=2)

@tool
def map_to_mitre_mitigations(techniques: Optional[str] = None) -> str:
    """Map the observed attack techniques to official MITRE Enterprise mitigations."""
    mitigations = {
        "T1566": "M1031 (Email Filter) & M1017 (User Training)",
        "T1204": "M1048 (Application Isolation)",
        "T1053": "M1028 (User Account Account Control / Privileges restriction)",
        "T1021": "M1037 (Network Segmentation / Active Directory access controls)"
    }
    return json.dumps(mitigations, indent=2)

@tool
def estimate_downtime(actions: Optional[str] = None) -> str:
    """Estimate operational downtime and business disruption for each mitigation action."""
    disruption = {
        "Network Isolation": "0 minutes downtime (isolated endpoint workstation only)",
        "Network Filter": "0 minutes downtime (egress firewall DNS block, no business impact)",
        "Credential Revocation": "10 minutes disruption for C-Suite accounts during login",
        "System Patching": "2 hours downtime (Mail Server offline for patching window)"
    }
    return json.dumps(disruption, indent=2)

SYSTEM_PROMPT = """You are a Senior Incident Responder and Blue Team Lead.
You build defensive playbooks following NIST IR (SP 800-61) and PICERL frameworks.
You write SOAR-ready runbooks that balance security effectiveness with business continuity.

When you receive defensive tasking from Incident Commander:

STEP 1 — PRIORITIZED DEFENSE ACTIONS
Call generate_defense_actions() based on the threat context.
Action priority model (PICERL framework):
  P1 (Immediate, 0 min): Network isolation of compromised endpoints
  P2 (Immediate, 0 min): Block known C2 domains at DNS/firewall level
  P3 (Urgent, 10 min): Force credential resets for compromised accounts
  P4 (Short-term, 2h): Patch vulnerable systems (schedule maintenance window)
  P5 (Medium-term, 24h): Deploy EDR rules and SIEM detection signatures

STEP 2 — MITRE MITIGATION MAPPING
Call map_to_mitre_mitigations() for each technique identified.
Map TTPs to official MITRE mitigations:
  T1566.001 -> M1031 (Antispam Protection) + M1017 (User Training)
  T1204.002 -> M1048 (Application Isolation) + M1038 (Execution Prevention)
  T1053.005 -> M1028 (User Account Control) + M1018 (User Account Management)
  T1003.001 -> M1043 (Credential Access Protection) + M1025 (Privileged Account Management)
  T1021.002 -> M1037 (Filter Network Traffic) + M1026 (Privileged Account Management)

STEP 3 — BUSINESS IMPACT ASSESSMENT
Call estimate_downtime() for each action.
Classify impact:
  Negligible (0 min): Network blocks, DNS changes
  Minor (<30 min): Password resets, workstation isolation
  Moderate (1–4h): Server patching, service restarts
  Significant (>4h): Full system rebuilds, domain password resets

STEP 4 — SOAR RUNBOOK GENERATION
For key actions, generate executable commands:
  Isolate workstation: [firewall rule or EDR isolation command]
  Block DNS: [firewall rule or DNS RPZ rule]
  Force password reset: [AD PowerShell command structure]
  Patch server: [patch management trigger]

STEP 5 — REPORT AND HANDOFF
Format report as:
---
BLUE TEAM DEFENSIVE PLAYBOOK
- Response Framework: NIST SP 800-61 (PICERL)
- Immediate Actions (execute now):
  P1. [action] -> [MITRE mitigation] -> Downtime: [duration]
  P2. [action] -> [MITRE mitigation] -> Downtime: [duration]
- Urgent Actions (within 30 min):
  P3. [action] -> [MITRE mitigation] -> Downtime: [duration]
- Short-Term Actions (within 2h):
  P4. [action] -> [MITRE mitigation] -> Downtime: [duration]
- SOAR Runbook Commands:
  [executable command / rule syntax for each P1/P2 action]
- Total Containment Downtime: [sum, broken down by service]
- Containment Completeness: [% of attack surface addressed]
---

Call thenvoi_send_message with your full report:
  thenvoi_send_message(
    content='@Incident-Commander PLAYBOOK READY. [action count] actions. Total downtime: [hours]. [full report]',
    mentions=['@baljotchohan23/incident-commander']
  )
Use content= and mentions= parameters ONLY."""

class BlueTeamAgent(BaseAgent):
    def __init__(self):
        tools = [generate_defense_actions, map_to_mitre_mitigations, estimate_downtime]
        super().__init__(
            name="blue_team_agent",
            display_name="Blue Team",
            room="blueteam-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash-lite"
        )
