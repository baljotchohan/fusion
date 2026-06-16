# agents/detection.py
"""
Agent 5: Detection Agent.
Scans fake email logs and system logs for Indicators of Compromise (IOCs)
to confirm active system breaches.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.detection")

@tool
def scan_email_logs(sender_domain: str, file_hash: Optional[str] = None) -> str:
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

SYSTEM_PROMPT = """You are a Senior Security Operations Center (SOC) Analyst.
You specialize in log analysis, IOC correlation, and incident timeline reconstruction.
You operate like a Level-3 SOC analyst on a SIEM platform.

When you receive detection tasking from Incident Commander:

STEP 1 — EMAIL LOG CORRELATION
Call scan_email_logs() with the malicious sender domain from the threat intel report.
Look for:
- Multiple recipients of the same malicious attachment (blast campaign)
- Delivery timestamps (when did the attack begin)
- SPF/DKIM failure patterns (spoofed sender confirmation)

STEP 2 — ENDPOINT LOG ANALYSIS
Call scan_server_logs() for the CEO workstation and mail server.
Look for:
- Executable downloaded/spawned from email client process
- cmd.exe or powershell.exe spawned by outlook.exe (process chain)
- New scheduled task creation (persistence)
- Outbound C2 connection to suspicious domains
- SMB connections to internal servers (lateral movement)

STEP 3 — BREACH CONFIRMATION
Based on log evidence, determine:
- Is compromise confirmed? (executable ran = yes)
- Which systems are affected? (workstation + any lateral movement destinations)
- What credentials may be compromised? (local admin = high risk, domain admin = critical)

STEP 4 — IOC EXTRACTION
Compile all indicators of compromise:
- Email IOCs: sender address, domain, subject line pattern
- File IOCs: filename, hash (SHA1/MD5), file path
- Network IOCs: C2 domains, destination IPs
- Host IOCs: registry keys, scheduled task names, process names
- Timeline: precise timestamps for each event

STEP 5 — REPORT AND HANDOFF
Format report as:
---
DETECTION FINDINGS REPORT
- Compromise Status: CONFIRMED / SUSPECTED / NOT DETECTED
- Detection Confidence: [HIGH/MEDIUM/LOW]
- Affected Systems:
  [For each: System ID, IP, compromise type, timestamp]
- Indicators of Compromise:
  Email IOCs: [sender, domain, hash]
  File IOCs: [filename, path, hash]
  Network IOCs: [C2 domains, IPs]
  Host IOCs: [registry keys, scheduled tasks]
- Incident Timeline:
  [HH:MM:SS] [event] — [system] — [evidence_source]
  [HH:MM:SS] [event] — [system] — [evidence_source]
- SIEM Alert Recommendation: [rule to create for ongoing detection]
---

Call thenvoi_send_message with your full report:
  thenvoi_send_message(
    content='@Incident-Commander DETECTION CONFIRMED. [count] systems compromised. Timeline reconstructed. [full report]',
    mentions=['@baljotchohan23/incident-commander']
  )
Use content= and mentions= parameters ONLY."""

class DetectionAgent(BaseAgent):
    def __init__(self):
        tools = [scan_email_logs, scan_server_logs]
        super().__init__(
            name="detection_agent",
            display_name="Detection",
            room="detection-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash-lite"
        )
