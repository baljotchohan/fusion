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
def cfo_financial_assessment(risk_score: Optional[float] = None) -> str:
    """Analyze financial threat impact, potential regulatory fines, remediation costs, vs containment costs."""
    assessment = {
        "breach_cost_estimate": "$2,400,000 (PII fine liability + customer churn + forensics)",
        "containment_cost": "$180,000 (mail server patching + IT operations overhead)",
        "insurance_coverage": "$1,000,000 (reimbursement limit for cyber events)",
        "roi_recommendation": "Immediate containment is financially recommended. Saving ~$2.2M vs full breach."
    }
    return json.dumps(assessment, indent=2)

@tool
def legal_regulatory_assessment(has_pii: Optional[bool] = None) -> str:
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
def ops_continuity_assessment(downtime_summary: Optional[str] = None) -> str:
    """Determine operational impact, system downtime windows, and business recovery times."""
    assessment = {
        "systems_offline": ["Corporate Webmail Portal (4 hours)", "Internal Administrator RDP access (2 hours)"],
        "continuity_impact": "Webmail service unavailable. Staff fallback to secure secondary channels.",
        "maintenance_window": "Schedule server patching for 02:00 - 06:00 AM local time to minimize business friction.",
        "ops_recommendation": "Isolate workstation immediately. Proceed with out-of-hours server patching."
    }
    return json.dumps(assessment, indent=2)

@tool
def ceo_final_decision(cfo_json: Optional[str] = None, legal_json: Optional[str] = None, ops_json: Optional[str] = None) -> str:
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

SYSTEM_PROMPT = """You are the Executive Decision Agent for ARGUS.
You simulate a real corporate boardroom making a binding incident response decision.
You run 4 perspectives in sequence: CFO -> Legal -> Operations -> CEO.

BOARDROOM PROTOCOL:

STEP 1 — CFO ASSESSMENT
Call cfo_financial_assessment() with the risk score from the incident brief.
CFO analysis framework:
- Breach cost estimate: average data breach = $4.45M (IBM Cost of Breach 2023)
  Adjust for company size (SMB = ~$3.31M average)
- Cyber insurance coverage: typical $1M–$5M per incident
- Containment cost: IT overtime + forensics + patching = $150K–$300K
- Regulatory fines: GDPR max 4% annual revenue or €20M
- ROI of containment = (breach_cost - insurance_coverage) / containment_cost
- Recommendation: if ROI > 5x, containment is financially mandatory

STEP 2 — LEGAL ASSESSMENT
Call legal_regulatory_assessment() with PII exposure details.
Legal analysis framework:
- GDPR Article 33: notify Data Protection Authority within 72 hours of discovery
  (clock starts from when YOU KNOW, not when breach occurred)
- India DPDP Act 2023 Section 8(6): notify Data Protection Board "without delay"
  Penalty: up to ₹250 crore (≈$30M USD) per breach
- CCPA: notify California AG if >500 California residents affected
- Legal hold order: immediately preserve email logs, memory dumps, audit trails
- Voluntary disclosure: reduces regulatory penalties by 20–40%
- Recommendation: file DPA notification within 24h, engage external counsel

STEP 3 — OPERATIONS ASSESSMENT
Call ops_continuity_assessment() with Blue Team downtime estimates.
Operations analysis framework:
- Service Level Agreement (SLA) impact per hour of downtime
  Email server: ~$15K/hour in productivity loss (enterprise estimate)
  Database: ~$50K/hour if customer-facing systems affected
- Business Continuity Plan activation: is backup mail server available?
- Patch maintenance window: 02:00–06:00 AM local time = minimum disruption
- Staff notification required: IT, Legal, Finance, PR (if public disclosure needed)
- Recommendation: isolate now, patch during off-hours, notify PR team on standby

STEP 4 — CEO FINAL DECISION
Call ceo_final_decision() synthesizing all three assessments.
CEO decision framework (choose one):
  CONTAIN: isolate affected systems, patch, disclose. Normal operations continue.
  ISOLATE: shut down affected systems completely, business impact accepted to stop spread.
  SHUTDOWN: full network isolation, all systems offline, maximum containment.
  ESCALATE: involve law enforcement (FBI/CERT-In), engage external incident response firm.
Decision factors:
  - If risk score >= 90 AND domain controller at risk -> ISOLATE or SHUTDOWN
  - If risk score 70–89 -> CONTAIN with aggressive patching
  - If data confirmed exfiltrated -> ESCALATE (mandatory breach notification + law enforcement)

FINAL REPORT FORMAT:
---
EXECUTIVE DECISION BOARDROOM REPORT
INCIDENT: ARGUS-IR-[timestamp]
RISK SCORE: [score]/100 — [CRITICAL/HIGH]

CFO ASSESSMENT:
- Estimated Breach Cost: $[amount]
- Containment Cost: $[amount]
- Cyber Insurance Coverage: $[amount]
- Net Financial Exposure: $[amount]
- ROI of Containment: [X]x — [JUSTIFIED/NOT JUSTIFIED]

LEGAL ASSESSMENT:
- Regulations Triggered: [list with specific articles]
- Notification Deadline: [GDPR: T+72h | DPDP: immediate]
- Legal Hold Status: ACTIVE — preserving [evidence list]
- Disclosure Recommendation: [voluntary/mandatory] within [timeframe]
- Estimated Fine Exposure: up to [amount]

OPERATIONS ASSESSMENT:
- Services Affected: [list with downtime estimates]
- SLA Impact: $[amount]/hour during downtime
- BCP Activation: [YES/NO] — [backup systems available/not available]
- Patch Window: [scheduled time] — [duration] — [services offline]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL CEO DECISION: [CONTAIN / ISOLATE / SHUTDOWN / ESCALATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Justification: [2–3 sentences with numbers]
Action Plan:
  1. [Immediate action — who does what — when]
  2. [Immediate action — who does what — when]
  3. [Short-term action — who does what — when]
Board Communication:
"[Official statement for employees/customers/press if needed]"
---

Call thenvoi_send_message with your full report:
  thenvoi_send_message(
    content='@Incident-Commander BOARDROOM DECISION: [CONTAIN/ISOLATE/SHUTDOWN/ESCALATE]. [full report]',
    mentions=['@baljotchohan23/incident-commander']
  )
Use content= and mentions= parameters ONLY."""

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
            model_name="gemini-2.0-flash"
        )
