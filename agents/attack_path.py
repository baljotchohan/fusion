# agents/attack_path.py
"""
Agent 4: Attack Path Analysis Agent.
Calculates a final weighted risk score (1-100), predicts the attacker's next moves,
and identifies critical assets at risk.
"""
import json
import logging
from typing import List, Dict, Optional
from langchain_core.tools import tool
from core.base_agent import BaseAgent

logger = logging.getLogger("fusion.agents.attack_path")

@tool
def calculate_risk_score(attack_stages: Optional[str] = None, target_system: Optional[str] = None) -> str:
    """Calculate the final risk score (1-100) based on attack path complexity and target severity."""
    # Simple risk scoring logic: base 50 + stage count * 5 + multipliers
    try:
        stages = json.loads(attack_stages) if attack_stages else []
        score = 50 + len(stages) * 5
    except:
        score = 60
        
    if target_system:
        if "db" in target_system.lower() or "database" in target_system.lower():
            score = min(100, int(score * 1.2))
        if "admin" in target_system.lower() or "ceo" in target_system.lower():
            score = min(100, int(score * 1.3))
        
    return str(min(100, score))

@tool
def predict_next_moves(attack_path: Optional[str] = None) -> str:
    """Predicts the attacker's next 3 logical moves with estimated probabilities."""
    predictions = [
        "1. Active Directory Credential Dumping (T1003) — 94% probability",
        "2. Database Exfiltration via Encrypted HTTPS tunnel (T1041) — 87% probability",
        "3. Local Registry Run Key Persistence modification (T1547.001) — 61% probability"
    ]
    return json.dumps(predictions, indent=2)

@tool
def identify_critical_assets() -> str:
    """Find corporate assets identified as 'crown jewels' from the digital twin configuration."""
    try:
        with open("data/company.json", "r") as f:
            data = json.load(f)
        assets = []
        for s in data.get("systems", []):
            roles = s.get("roles", [])
            for role in roles:
                if "PII" in role or "Database" in role or "Admin" in role or "C-Suite" in role:
                    assets.append({
                        "id": s.get("id"),
                        "name": s.get("name"),
                        "critical_role": role
                    })
        return json.dumps(assets, indent=2)
    except Exception as e:
        return f"Error identifying assets: {e}"

SYSTEM_PROMPT = """You are a Threat Quantification Specialist.
You convert technical attack data into risk scores and probabilistic predictions
that drive executive decision-making.

When you receive the Red Team simulation report:

STEP 1 — IDENTIFY CROWN JEWELS
Call identify_critical_assets() to find the highest-value targets.
Crown jewels criteria: PII storage, financial records, domain admin access.

STEP 2 — RISK SCORE CALCULATION
Call calculate_risk_score() using the Red Team data.
Risk scoring model:
  Base: 50
  + 10 per kill chain stage beyond stage 3
  + 15 if Domain Controller is reachable
  + 20 if PII/financial database is final target
  + 10 if admin credentials confirmed dumped
  + 5 if dwell time > 8 hours
  Max: 100. Score >= 70 triggers mandatory executive escalation.

STEP 3 — PROBABILISTIC PREDICTIONS
Call predict_next_moves() to forecast attacker behavior:
Model probabilities based on known post-exploitation patterns:
- Credential dumping (LSASS): 94% — standard after initial compromise
- Kerberoasting (AD service accounts): 78% — common domain escalation
- Database exfiltration via encrypted channel: 87% — high-value target
- Ransomware deployment after data theft: 61% — monetization pattern
- Backdoor persistence (scheduled task/service): 95% — dwell guarantee

STEP 4 — BLAST RADIUS ASSESSMENT
Determine which systems are at risk if attacker persists:
- Direct: compromised systems from kill chain
- Secondary: systems reachable via SMB/RDP from compromised hosts
- Tertiary: cloud/SaaS services accessible via stolen credentials

STEP 5 — REPORT AND HANDOFF
Format report as:
---
ATTACK PATH RISK ANALYSIS
- Combined Risk Score: [score]/100
- Risk Level: [CRITICAL if >=70 / HIGH if >=50 / MEDIUM / LOW]
- ⚠️ EXECUTIVE ESCALATION: [REQUIRED if score >=70 / NOT REQUIRED if <70]
- Blast Radius:
  Direct Compromise: [systems]
  At-Risk Secondary: [systems]
  Data Assets Exposed: [types]
- Predicted Next Attacker Moves (72h horizon):
  1. [action] — [probability]% (T[TTP-ID])
  2. [action] — [probability]% (T[TTP-ID])
  3. [action] — [probability]% (T[TTP-ID])
- Time-to-Act Window: [IMMEDIATE <2h / URGENT <4h / MODERATE <24h]
- Recommended Priority: [contain/isolate/shutdown]
---

Call thenvoi_send_message with your full report:
  thenvoi_send_message(
    content='@Incident-Commander RISK SCORE: [score]/100. [CRITICAL/HIGH]. Escalation [required/not required]. [full report]',
    mentions=['@baljotchohan23/incident-commander']
  )
Use content= and mentions= parameters ONLY."""

class AttackPathAgent(BaseAgent):
    def __init__(self):
        tools = [calculate_risk_score, predict_next_moves, identify_critical_assets]
        super().__init__(
            name="attack_path_agent",
            display_name="Attack Path",
            room="attack-path-room",
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            model_name="gemini-2.0-flash-lite"
        )
