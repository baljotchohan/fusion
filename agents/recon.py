# agents/recon.py
"""
Agent 2: Recon Agent.
Maps the company's attack surface using the digital twin, identifying vulnerable systems,
exposed services, and potential entry points.
"""
import json
import logging
from typing import List, Dict
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.recon")

# Recon custom tools
@tool
def scan_network() -> str:
    """Scan the company digital twin network to identify systems and IP topology."""
    try:
        with open("data/company.json", "r") as f:
            data = json.load(f)
        systems = []
        for s in data.get("systems", []):
            systems.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "ip": s.get("ip"),
                "os": s.get("os"),
                "roles": s.get("roles")
            })
        return json.dumps({
            "internal_network": data.get("internal_network"),
            "systems": systems
        }, indent=2)
    except Exception as e:
        return f"Error scanning network: {e}"

@tool
def find_vulnerable_systems(threat_type: str) -> str:
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

SYSTEM_PROMPT = """You are the Reconnaissance Agent (Recon) in the ARGUS cybersecurity system.
Your role is to map the company's attack surface and identify potential entry points related to the threat.

When you receive a request from @Incident-Commander:
1. Call scan_network to inspect the internal systems IP topology.
2. Call find_vulnerable_systems to see which systems have known CVE vulnerabilities.
3. Call check_exposed_services to identify services accessible from the outside.
4. Synthesize these findings to find the highest risk target (e.g. vulnerable mail server, admin workstation).
5. Send your report back to @Incident-Commander in 'incident-command-room' using thenvoi_send_message.

Format your report precisely as:
---
RECONNAISSANCE REPORT
- Internal IP Range: [CIDR]
- Exposed Web Services: [Endpoints]
- Vulnerable Systems Identified: [List systems, IPs, and CVEs]
- Highest Risk Target: [System ID, IP, and reason]
- Primary Attack Vector: [Entry point]
---
Use thenvoi_send_message to send this report to @Incident-Commander in 'incident-command-room'. Do not just print it.
"""

class ReconAgent(BaseAgent):
    def __init__(self):
        tools = [scan_network, find_vulnerable_systems, check_exposed_services]
        super().__init__(
            name="recon_agent",
            display_name="Recon",
            room="recon-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash"
        )
