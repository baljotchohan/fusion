# agents/threat_intel.py
"""
Agent 1: Threat Intelligence Agent.
Analyzes incoming security alerts, maps them to MITRE ATT&CK techniques
and CVE vulnerabilities, and posts a threat report to the Incident Commander.
"""
import logging
from core.base_agent import BaseAgent
from core.mitre_lookup import search_ttp
from core.cve_lookup import get_cves

logger = logging.getLogger("argus.agents.threat_intel")

SYSTEM_PROMPT = """You are a Threat Intelligence Analyst agent in the ARGUS cybersecurity system.
Your role is to analyze raw security alerts and provide a structured threat report.

When you receive a security alert:
1. Parse the alert to extract key indicators (e.g. sender email, target email, attachment name/hash, ports, IPs).
2. Call search_ttp with keywords related to the attack type (e.g. "phishing", "spearphishing", "attachment") to identify relevant MITRE ATT&CK techniques.
3. Call get_cves with keywords related to the target software or attack vector (e.g. "email remote code", "outlook") to discover relevant vulnerabilities.
4. Calculate a threat severity score (0 to 100) based on the target (C-suite targets increase score), CVE CVSS scores, and threat vector.
5. Use thenvoi_send_message to send the complete threat report to the incident commander in 'incident-command-room'.

Format your report precisely as:
---
THREAT INTELLIGENCE REPORT
- Threat Type: [Spearphishing Attachment/etc]
- Target: [Role/Email/Admin Privilege]
- MITRE ATT&CK TTPs: [IDs and Names]
- Associated CVEs: [IDs, CVSS scores, and descriptions]
- Threat Severity Score: [0-100]
- Recommended Containment: [Immediate actions]
---
Use thenvoi_send_message to notify @Incident-Commander in 'incident-command-room' with this report. Do not just print it.
"""

class ThreatIntelAgent(BaseAgent):
    def __init__(self):
        # Tools exposed to the LLM
        tools = [search_ttp, get_cves]
        super().__init__(
            name="threat_intel_agent",
            display_name="Threat Intelligence",
            room="threat-intel-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash"
        )
