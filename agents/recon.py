# agents/recon.py
"""
Agent 2: Recon Agent.
Maps the company's attack surface using the digital twin, identifying vulnerable systems,
exposed services, and potential entry points.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.recon")

# Recon custom tools
@tool
def scan_network() -> str:
    """Scan the company digital twin network to enumerate all systems, services, and topology."""
    try:
        with open("data/company.json", "r") as f:
            data = json.load(f)
        result = {
            "company": data.get("company_name"),
            "domain": data.get("domain"),
            "internal_network": data.get("internal_network"),
            "total_systems": len(data.get("systems", [])),
            "systems": []
        }
        for s in data.get("systems", []):
            result["systems"].append({
                "id": s.get("id"),
                "name": s.get("name"),
                "ip": s.get("ip"),
                "os": s.get("os"),
                "roles": s.get("roles", []),
                "open_ports": s.get("open_ports", []),
                "services": s.get("services", []),
                "vuln_count": len(s.get("vulnerabilities", [])),
                "critical_vulns": [
                    v for v in s.get("vulnerabilities", [])
                    if v.get("cvss", 0) >= 9.0
                ]
            })
        result["exposed_services"] = data.get("exposed_services", [])
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Network scan error: {e}"

@tool
def find_vulnerable_systems(threat_type: Optional[str] = None) -> str:
    """Find systems that have vulnerabilities matching a specific threat type or keyword."""
    try:
        with open("data/company.json", "r") as f:
            data = json.load(f)
        vulnerable = []
        for s in data.get("systems", []):
            vulns = s.get("vulnerabilities", [])
            if vulns:
                vulnerable.append({
                    "id": s.get("id"),
                    "ip": s.get("ip"),
                    "vulnerabilities": vulns
                })
        return json.dumps(vulnerable, indent=2)
    except Exception as e:
        return f"Error finding vulnerable systems: {e}"

@tool
def check_exposed_services() -> str:
    """Identify corporate services exposed directly to the public internet."""
    try:
        with open("data/company.json", "r") as f:
            data = json.load(f)
        return json.dumps(data.get("exposed_services", []), indent=2)
    except Exception as e:
        return f"Error checking exposed services: {e}"

SYSTEM_PROMPT = """You are a Senior Penetration Tester and Network Reconnaissance Specialist.
You conduct authorized attack surface assessments for enterprise clients.

When you receive reconnaissance tasking from Incident Commander:

STEP 1 — NETWORK TOPOLOGY SCAN
Call scan_network() to enumerate all systems, IPs, and services.
Identify: subnet range, total host count, domain structure.

STEP 2 — VULNERABILITY SURFACE
Call find_vulnerable_systems() to identify unpatched CVEs per host.
For each vulnerable system, assess:
- CVE severity (CRITICAL >= 9.0 CVSS, HIGH >= 7.0)
- Exploitability (network-accessible = more critical)
- Privilege impact (SYSTEM/admin privilege escalation risk)

STEP 3 — EXPOSED SERVICES
Call check_exposed_services() to find internet-facing services.
Key risk indicators:
- SMTP port 25 open = email relay/spoofing risk
- RDP port 3389 open = brute force / credential spray target
- MSSQL port 1433 open = SQL injection / data exfil path
- Kerberos port 88 open = Kerberoasting attack surface

STEP 4 — ATTACK SURFACE MAPPING
Identify the most likely initial access paths:
- Email server as entry point (phishing delivery)
- CEO workstation as initial compromise target (admin creds)
- Domain Controller as lateral movement destination (domain takeover)
- Database server as crown jewel target (PII/financial data)

STEP 5 — REPORT AND HANDOFF
Format report as:
---
RECONNAISSANCE REPORT
- Target Network: [subnet]
- Systems Enumerated: [count]
- Critical Vulnerabilities Found:
  [For each: System ID, IP, CVE-ID, CVSS, Attack Vector, Privilege Impact]
- Exposed Internet Services:
  [For each: Service, Endpoint, Risk Level, Attack Vector]
- Identified Attack Paths:
  Path 1 (Most Likely): [email server -> CEO workstation -> AD -> DB]
  Path 2 (Alternative): [direct RDP brute force -> DB server]
- Highest Risk System: [system ID] — [reason]
- Estimated Time to Exploitation: [hours] given CVE availability
---

Call thenvoi_send_message to send to 'incident-command-room'.
Message: '@Incident-Commander RECON COMPLETE. Critical systems mapped. [report]'"""

class ReconAgent(BaseAgent):
    def __init__(self):
        tools = [scan_network, find_vulnerable_systems, check_exposed_services]
        super().__init__(
            name="recon_agent",
            display_name="Recon",
            room="recon-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash-lite"
        )
