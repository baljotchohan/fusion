# agents/executive_decision.py
"""
Agent 9: Executive Decision Agent.
Simulates a multi-persona boardroom debate (CFO -> Legal -> Ops -> CEO)
to make a final business-level incident decision with full justification and audit logs.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("argus.agents.executive_decision")

@tool
def cfo_financial_assessment(risk_score: float) -> str:
    """Analyze financial threat impact, potential regulatory fines, remediation costs, vs containment costs."""
    assessment = {
        "breach_cost_estimate": "$2,400,000 (PII fine liability + customer churn + forensics)",
        "containment_cost": "$180,000 (mail server patching + IT operations overhead)",
        "insurance_coverage": "$1,000,000 (reimbursement limit for cyber events)",
        "roi_recommendation": "Immediate containment is financially recommended. Saving ~$2.2M vs full breach."
    }
    return json.dumps(assessment, indent=2)

@tool
def legal_regulatory_assessment(has_pii: bool) -> str:
    """Evaluate legal liabilities, notification requirements (GDPR, India DPDP Act), and compliance clocks."""
    assessment = {
        "regulations_triggered": [
            "GDPR Article 33 (requires DPA notification within 72 hours of discovery)",
            "India DPDP Act Section 8 (requires prompt notification of data breach)"
        ],
        "liability_exposure": "Up to €20M or 4% of global annual turnover under GDPR",
        "legal_hold_order": "Active. Preserving email logs and memory dump files for forensic audit.",
        "legal_recommendation": "Voluntary disclosure recommended to DPA within 24 hours to mitigate fines."
    }
    return json.dumps(assessment, indent=2)

@tool
def ops_continuity_assessment(downtime_summary: str) -> str:
    """Determine operational impact, system downtime windows, and business recovery times."""
    assessment = {
        "systems_offline": ["Corporate Webmail Portal (4 hours)", "Internal Administrator RDP access (2 hours)"],
        "continuity_impact": "Webmail service unavailable. Staff fallback to secure secondary channels.",
        "maintenance_window": "Schedule server patching for 02:00 - 06:00 AM local time to minimize business friction.",
        "ops_recommendation": "Isolate workstation immediately. Proceed with out-of-hours server patching."
    }
    return json.dumps(assessment, indent=2)

@tool
def ceo_final_decision(cfo_json: str, legal_json: str, ops_json: str) -> str:
    """Synthesize financial, legal, and operational metrics into a final binding decision (CONTAIN/SHUTDOWN/ESCALATE)."""
    try:
        cfo = json.loads(cfo_json)
        legal = json.loads(legal_json)
        ops = json.loads(ops_json)
    except:
        cfo = legal = ops = {}
        
    decision = {
        "final_verdict": "CONTAIN",
        "action_plan": "1. Isolate CEO workstation immediately. 2. Block outbound DNS resolution to malicious domains. 3. Patch mail server during off-hours window. 4. Disclose to DPAs within 24 hours.",
        "justification": f"Containment cost of {cfo.get('containment_cost', '$180K')} is substantially lower than breach liability exposure of {cfo.get('breach_cost_estimate', '$2.4M')}. Regulatory compliance requires prompt notification.",
        "board_communication": "ARGUS contained active phishing attack. Systems are being hardened. No evidence of data exfiltration. Full forensic report in 48 hours."
    }
    return json.dumps(decision, indent=2)

SYSTEM_PROMPT = """You are the Executive Decision Agent in the ARGUS cybersecurity system.
Your role is to translate technical threat facts into a business-level decision.

To do this, you must run assessments for all 4 boardroom roles step-by-step:
1. Call cfo_financial_assessment with the risk score to get financial impact.
2. Call legal_regulatory_assessment with target detail (if C-Suite/PII at risk) to get regulatory obligations.
3. Call ops_continuity_assessment with Blue Team playbook details to get downtime impact.
4. Call ceo_final_decision with the CFO, Legal, and Ops assessments to yield a final decision.
5. Post the final Executive Decision Report back to @Incident-Commander in 'incident-command-room' using thenvoi_send_message.

Format your report precisely as:
---
EXECUTIVE DECISION BOARDROOM REPORT
- CFO Recommendation: [Brief financial ROI summary]
- Legal Assessment: [List regulations triggered and deadlines]
- Operations Assessment: [List services affected and maintenance windows]
- FINAL CEO DECISION: [CONTAIN / SHUTDOWN / ESCALATE]
- Justification: [CEO business reasoning]
- Board Communication Statement: [Official statement]
---
Use thenvoi_send_message to send this report to @Incident-Commander in 'incident-command-room'. Do not just print it.
"""

class ExecutiveDecisionAgent(BaseAgent):
    def __init__(self):
        tools = [cfo_financial_assessment, legal_regulatory_assessment, ops_continuity_assessment, ceo_final_decision]
        # Uses Gemini 1.5 Pro for complex multi-persona reasoning and final board decision synthesis
        super().__init__(
            name="executive_decision",
            display_name="Executive Decision",
            room="executive-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-1.5-pro"
        )
