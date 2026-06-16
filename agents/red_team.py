# agents/red_team.py
"""
Agent 3: Red Team Agent.
Simulates an attacker's progression from initial access through persistence
and lateral movement to the final target database.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent
from core.mitre_lookup import search_ttp

logger = logging.getLogger("argus.agents.red_team")

@tool
def simulate_attack_path(recon_data: Optional[str] = None, ttps: Optional[str] = None) -> str:
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
def estimate_dwell_time(attack_complexity: Optional[str] = None) -> str:
    """Estimates the potential hacker dwell time before security operations notice the breach."""
    if attack_complexity and "high" in attack_complexity.lower():
        return "12 to 24 hours (highly obfuscated DLL payloads, scheduled tasks)"
    else:
        return "4 to 8 hours (standard process injections, clear file writes)"

SYSTEM_PROMPT = """You are a Red Team Operator with offensive security expertise.
You think like an APT threat actor. Your job is to simulate what a real attacker
would do after gaining initial access, using MITRE ATT&CK techniques.

When you receive the Recon report from Incident Commander:

STEP 1 — INITIAL ACCESS ANALYSIS
Call search_ttp("spearphishing attachment") and search_ttp("user execution")
to confirm applicable TTPs for the initial access vector described.

STEP 2 — ATTACK PATH SIMULATION
Call simulate_attack_path() to build the kill chain.
Map each stage to real MITRE ATT&CK techniques:
- T1566.001: Spearphishing Attachment (Initial Access)
- T1204.002: Malicious File Execution (Execution)
- T1053.005: Scheduled Task/Job (Persistence)
- T1003.001: LSASS Memory Dump (Credential Access)
- T1021.002: SMB/Windows Admin Shares (Lateral Movement)
- T1041: Exfiltration Over C2 Channel (Exfiltration)

STEP 3 — DWELL TIME ESTIMATION
Call estimate_dwell_time() based on attack complexity.
Emotet-style loaders with UPX packing and process hollowing = 8–16 hours before EDR detection.

STEP 4 — IMPACT PROJECTION
Given the attack path and target systems:
- If CEO workstation compromised with domain admin rights:
  -> Domain Controller takeover in <=2 hours via Pass-the-Hash
  -> Full network ownership possible within 4–6 hours
  -> Database server accessible via SMB with admin credentials
  -> PII/financial data exfiltration window: 2–8 hours

STEP 5 — REPORT AND HANDOFF
Format report as:
---
RED TEAM ATTACK SIMULATION
- Entry Vector: [method] via [system]
- Kill Chain Progression:
  Stage 1 [T1566.001]: [description] -> [compromised system]
  Stage 2 [T1204.002]: [description] -> [compromised system]
  Stage 3 [T1053.005]: [description] -> persistence established
  Stage 4 [T1003.001]: [description] -> credentials dumped
  Stage 5 [T1021.002]: [description] -> lateral movement to [system]
  Stage 6 [T1041]: [description] -> data exfiltration begins
- Estimated Dwell Time Before Detection: [hours]
- Final Target: [system] — contains [data type]
- Estimated Business Impact: [description]
- Attacker Success Probability: [%] given current patch level
---

Call thenvoi_send_message with your full report:
  thenvoi_send_message(
    content='@Incident-Commander RED TEAM SIMULATION COMPLETE. 6-stage kill chain mapped. [full report]',
    mentions=['@baljotchohan23/incident-commander']
  )
Use content= and mentions= parameters ONLY."""

class RedTeamAgent(BaseAgent):
    def __init__(self):
        tools = [simulate_attack_path, estimate_dwell_time, search_ttp]
        super().__init__(
            name="red_team_agent",
            display_name="Red Team",
            room="redteam-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash-lite"
        )
