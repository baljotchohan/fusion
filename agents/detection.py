# agents/detection.py
"""
Agent 5: Detection Agent.
Scans fake email logs and system logs for Indicators of Compromise (IOCs)
to confirm active system breaches.
"""
import json
import logging
from typing import List, Dict
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.detection")

@tool
def scan_email_logs(sender_domain: str, file_hash: str) -> str:
    """Scan corporate email logs for suspicious emails matching a sender domain or attachment file hash."""
    try:
        with open("data/email_logs.json", "r") as f:
            logs = json.load(f)
        
        matches = []
        for log in logs:
            sender = log.get("sender", "")
            attachment = log.get("attachment", "")
            
            if (sender_domain.lower() in sender.lower() or 
                (file_hash and file_hash.lower() in attachment.lower())):
                matches.append(log)
                
        return json.dumps(matches, indent=2)
    except Exception as e:
        return f"Error scanning email logs: {e}"

@tool
def scan_server_logs(server_id: str) -> str:
    """Scans specific server security event logs for process anomalies, connections, or login spikes."""
    # Mock log response
    logs = [
        {"timestamp": "2026-06-19T08:47:32Z", "event": "File download detected: Invoice_2026_0891.exe", "source": "ceo-workstation"},
        {"timestamp": "2026-06-19T08:47:45Z", "event": "Process spawned: CMD.EXE spawning Invoice_2026_0891.exe", "source": "ceo-workstation", "privilege": "SYSTEM"},
        {"timestamp": "2026-06-19T08:49:12Z", "event": "SMB Connection established to 192.168.1.20 (SRV-03-DB)", "source": "ceo-workstation"}
    ]
    return json.dumps(logs, indent=2)

SYSTEM_PROMPT = """You are the Detection Agent in the ARGUS cybersecurity system.
Your role is to scan email and server logs to find active Indicators of Compromise (IOCs) and confirm the breach.

When you receive a request from @Incident-Commander:
1. Call scan_email_logs with the threat sender domain and attachment details from the threat intel.
2. Call scan_server_logs for key endpoints to trace process executions.
3. Establish a precise timeline of the compromise.
4. Send your findings back to @Incident-Commander in 'incident-command-room' using thenvoi_send_message.

Format your report precisely as:
---
DETECTION FINDINGS REPORT
- Compromise Confirmed: [Yes/No]
- Affected Systems: [List of system names and IPs]
- Indicators of Compromise Found: [List senders, hashes, processes]
- Incident Timeline:
  - [Timestamp] [Event description]
---
Use thenvoi_send_message to send this report to @Incident-Commander in 'incident-command-room'. Do not just print it.
"""

class DetectionAgent(BaseAgent):
    def __init__(self):
        tools = [scan_email_logs, scan_server_logs]
        super().__init__(
            name="detection_agent",
            display_name="Detection",
            room="detection-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash"
        )
