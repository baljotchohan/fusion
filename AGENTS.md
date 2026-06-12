# Fusion — Agent Documentation

> Detailed specifications for all 9 agents in the Fusion Autonomous Cyber Defense Command Center.

---

## Agent Architecture

Every agent in Fusion follows the same pattern:

```
External Trigger / @mention from Band
         ↓
Band WebSocket receives message
         ↓
LangGraph graph activates
         ↓
Node 1: Parse input
Node 2: Run tools (MITRE, CVE, digital twin)
Node 3: Analyze with Gemini LLM
Node 4: Format output
         ↓
thenvoi_send_message → @mention next agent(s) in Band room
         ↓
FastAPI event_bus → broadcast status to dashboard
```

All agents extend `BaseAgent` and connect to Band via the LangGraph adapter.

---

## Agent 1 — Threat Intelligence

**Band Room:** `threat-intel-room`
**LLM:** Gemini 2.0 Flash
**Trigger:** Receives initial alert via `@Threat-Intel` @mention

### What It Does
Analyzes the incoming security alert and identifies the attack type, relevant MITRE ATT&CK techniques, and associated CVEs. Calculates a threat severity score and hands off to Incident Commander.

### Tools
- `search_mitre_attack(keyword)` — MITRE ATT&CK enterprise database search
- `lookup_cve(keyword)` — NVD CVE API query
- `parse_alert(alert_json)` — Extract structured fields from raw alert

### LangGraph Nodes
```
parse_alert → mitre_lookup → cve_lookup → score_threat → format_report → send_to_commander
```

### Output Format
```json
{
  "threat_type": "Spearphishing Attachment",
  "mitre_ttps": ["T1566", "T1566.001", "T1204.002"],
  "cves": [{"id": "CVE-2024-21378", "cvss": 9.8, "severity": "CRITICAL"}],
  "severity_score": 82,
  "target": {"email": "ceo@techcorp.com", "role": "CEO", "admin": true},
  "recommended_actions": ["Isolate mail server", "Block sender domain"]
}
```

### Band Coordination
Sends to: **@Incident-Commander** with full threat report

---

## Agent 2 — Recon

**Band Room:** `recon-room`
**LLM:** Gemini 2.0 Flash (or Featherless Llama 3.1 8B)
**Trigger:** @mention from Incident Commander

### What It Does
Maps the company's attack surface using the digital twin. Identifies vulnerable systems, open ports, exposed services, and potential entry points relevant to the current threat.

### Tools
- `scan_network(company_json)` — Parse digital twin network topology
- `find_vulnerable_systems(threat_type)` — Match company systems to known vulnerabilities
- `check_exposed_services()` — Identify services accessible from outside

### LangGraph Nodes
```
parse_context → scan_network → find_vulnerabilities → map_entry_points → format_report → send_to_commander
```

### Output Format
```json
{
  "attack_surface": {
    "vulnerable_servers": ["SRV-01 (Mail, CVE-2024-1234)", "SRV-03 (DB, Windows)"],
    "exposed_ports": [25, 443, 1433],
    "entry_points": ["Mail server SMTP", "CEO workstation (admin privileges)"]
  },
  "highest_risk_target": "Mail Server SRV-01",
  "internal_network": "192.168.1.0/24"
}
```

### Band Coordination
Sends to: **@Incident-Commander** with recon report

---

## Agent 3 — Red Team

**Band Room:** `redteam-room`
**LLM:** Gemini 2.0 Flash
**Trigger:** @mention from Incident Commander

### What It Does
Simulates what an attacker would do next using the recon data and MITRE ATT&CK techniques. Maps out the realistic attack progression from initial access to the likely target (database, credentials, etc.).

### Tools
- `simulate_attack_path(recon_data, ttps)` — Build attack progression tree
- `search_mitre_attack(technique_id)` — Get technique details and sub-techniques
- `estimate_dwell_time(attack_complexity)` — Estimate how long attacker could stay hidden

### LangGraph Nodes
```
parse_recon → select_attack_ttps → simulate_progression → estimate_impact → format_simulation → send_to_commander
```

### Output Format
```json
{
  "attack_stages": [
    {"stage": 1, "action": "Email opened, .exe executed", "ttp": "T1566.001"},
    {"stage": 2, "action": "Persistence established via scheduled task", "ttp": "T1053.005"},
    {"stage": 3, "action": "Lateral movement to SRV-03 via SMB", "ttp": "T1021.002"},
    {"stage": 4, "action": "Database exfiltration", "ttp": "T1041"}
  ],
  "likely_target": "Customer database SRV-03",
  "estimated_dwell_time": "4-8 hours before detection",
  "potential_data_exposed": ["Customer PII", "Financial records"]
}
```

### Band Coordination
Sends to: **@Incident-Commander** with simulation results

---

## Agent 4 — Attack Path Analysis

**Band Room:** `attack-path-room`
**LLM:** Gemini 2.0 Flash
**Trigger:** @mention from Incident Commander with Red Team results

### What It Does
Calculates a comprehensive risk score (1-100), predicts the most likely next attacker moves, identifies critical assets at risk, and prioritizes which systems need immediate protection.

### Tools
- `calculate_risk_score(attack_data, company_profile)` — Weighted risk scoring algorithm
- `predict_next_moves(attack_path)` — Predict attacker's next 3 probable actions
- `identify_critical_assets(company_json)` — Find crown jewels at risk

### LangGraph Nodes
```
parse_simulation → calculate_risk → predict_moves → identify_assets → format_analysis → send_to_commander
```

### Output Format
```json
{
  "risk_score": 87,
  "risk_level": "CRITICAL",
  "predicted_next_moves": [
    "Credential dumping (T1003) — 94% probability",
    "Data exfiltration via HTTPS (T1041) — 87% probability",
    "Ransomware deployment (T1486) — 61% probability"
  ],
  "critical_assets_at_risk": ["Customer DB", "CEO credentials", "Financial records"],
  "time_to_act": "Immediate — estimated 2-4 hours before lateral movement"
}
```

### Band Coordination
Sends to: **@Incident-Commander** with risk analysis

---

## Agent 5 — Detection

**Band Room:** `detection-room`
**LLM:** Gemini 2.0 Flash
**Trigger:** @mention from Incident Commander

### What It Does
Analyzes company logs (email logs, server logs, access logs from digital twin) to find indicators of compromise. Identifies which systems are already affected and confirms the initial alert.

### Tools
- `scan_email_logs(company_json, iocs)` — Search email logs for malicious indicators
- `scan_server_logs(server_id, time_range)` — Check server logs for anomalies
- `correlate_iocs(threat_report)` — Match threat intel IOCs against log data

### LangGraph Nodes
```
parse_context → scan_email_logs → scan_server_logs → correlate_iocs → confirm_breach → format_findings → send_to_commander
```

### Output Format
```json
{
  "confirmed_compromise": true,
  "affected_systems": ["CEO-WORKSTATION-01", "SRV-01-MAIL"],
  "iocs_found": [
    {"type": "email_sender", "value": "invoices@corp-billing.xyz", "seen": 3},
    {"type": "file_hash", "value": "a1b2c3d4...", "seen": 1}
  ],
  "timeline": [
    {"time": "08:45:00", "event": "Phishing email received"},
    {"time": "08:47:32", "event": "Attachment downloaded"},
    {"time": "08:47:45", "event": "Malicious process started"}
  ]
}
```

### Band Coordination
Sends to: **@Incident-Commander** with detection findings

---

## Agent 6 — Malware Investigation

**Band Room:** `malware-room`
**LLM:** Featherless AI (Mistral 7B)
**Trigger:** @mention from Incident Commander

### What It Does
Analyzes suspicious file metadata from the digital twin. Classifies the malware type, extracts indicators of compromise, and recommends specific containment actions.

### Tools
- `analyze_file_metadata(file_data)` — Parse file properties, entropy, suspicious strings
- `classify_malware(analysis)` — Identify malware family/type
- `extract_iocs(file_data)` — Pull out C2 domains, registry keys, file drops
- `recommend_containment(malware_type)` — Generate specific removal steps

### LangGraph Nodes
```
get_file_metadata → analyze_entropy → classify_type → extract_iocs → recommend_containment → send_to_commander
```

### Output Format
```json
{
  "file": "Invoice_2026_0891.exe",
  "classification": "Trojan.Dropper — likely Emotet variant",
  "risk": "CRITICAL",
  "iocs": {
    "c2_domains": ["update.corp-billing.xyz", "cdn.fast-delivery.net"],
    "registry_keys": ["HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\InvoiceSync"],
    "dropped_files": ["%TEMP%\\svchost32.exe"]
  },
  "containment": [
    "Delete %TEMP%\\svchost32.exe",
    "Block DNS: corp-billing.xyz, fast-delivery.net",
    "Remove registry persistence key",
    "Quarantine CEO workstation immediately"
  ]
}
```

### Band Coordination
Sends to: **@Incident-Commander** with malware report

---

## Agent 7 — Blue Team Defense

**Band Room:** `blueteam-room`
**LLM:** Gemini 2.0 Flash
**Trigger:** @mention from Incident Commander

### What It Does
Generates a prioritized list of specific defensive actions based on all gathered intelligence. Maps each action to a MITRE mitigation and assigns urgency levels.

### Tools
- `generate_defense_actions(full_context)` — Create prioritized action list
- `map_to_mitre_mitigations(ttps)` — Link defenses to official MITRE mitigations
- `estimate_downtime(actions)` — Predict business impact of each action

### LangGraph Nodes
```
gather_all_context → prioritize_threats → generate_actions → map_mitigations → estimate_impact → format_playbook → send_to_commander
```

### Output Format
```json
{
  "immediate_actions": [
    {"priority": 1, "action": "Isolate CEO workstation from network", "mitigation": "M1037", "downtime": "None"},
    {"priority": 2, "action": "Block outbound connections to corp-billing.xyz", "mitigation": "M1031", "downtime": "None"},
    {"priority": 3, "action": "Force password reset — CEO + IT Admin accounts", "mitigation": "M1027", "downtime": "10 min"}
  ],
  "short_term_actions": [
    {"action": "Patch SRV-01 mail server (CVE-2024-1234)", "timeline": "2 hours"},
    {"action": "Enable MFA on all admin accounts", "timeline": "4 hours"}
  ],
  "total_estimated_downtime": "4 hours (customer portal offline)"
}
```

### Band Coordination
Sends to: **@Incident-Commander** with defense playbook

---

## Agent 8 — Incident Commander ⭐

**Band Room:** `incident-command-room` (monitors ALL rooms)
**LLM:** Gemini 1.5 Pro (most capable — this is the brain)
**Trigger:** Initial alert from system; then continuously from all agents

### What It Does
The most critical agent. Coordinates the entire response by routing tasks, sharing context between agents, escalating decisions, and ensuring no step is skipped. Uses Band's `thenvoi_lookup_peers` to discover available agents and `thenvoi_add_participant` to dynamically recruit them.

### Tools
- All Band platform tools: `thenvoi_send_message`, `thenvoi_add_participant`, `thenvoi_lookup_peers`, `thenvoi_send_event`, `thenvoi_create_chatroom`
- `build_incident_timeline(all_reports)` — Aggregate chronological timeline
- `assess_escalation_needed(risk_score)` — Decide if executive needs to be activated
- `generate_status_update(progress)` — Create current situation report

### Coordination Logic
```
Receive initial alert
    → @mention Threat-Intel-Agent: "Analyze this alert"

Receive Threat Intel report
    → @mention Recon-Agent + Detection-Agent simultaneously
    → Share full threat context with both

Receive Recon + Detection reports
    → @mention Red-Team-Agent + Malware-Investigation-Agent
    → "Here's what we found — simulate the attack"

Receive Red Team + Malware reports
    → Calculate combined risk
    → @mention Attack-Path-Analysis
    → "Predict next moves and final risk score"

Receive Attack Path Analysis
    → If risk_score >= 70: @mention Blue-Team-Agent + Executive-Decision-Agent
    → If risk_score < 70: @mention Blue-Team-Agent only
    → Share FULL incident context (all previous reports)

Receive Blue Team playbook + Executive Decision
    → Build final incident report
    → Broadcast to dashboard via event_bus
    → Archive audit trail
```

### Band Platform Tools Usage
```python
# Discover available agents
peers = await thenvoi_lookup_peers()

# Dynamically recruit Recon and Detection in parallel
await thenvoi_add_participant(room="incident-command-room", agent="@Recon-Agent")
await thenvoi_add_participant(room="incident-command-room", agent="@Detection-Agent")

# Share context across rooms
await thenvoi_send_message(
    room="recon-room",
    message="@Recon-Agent Full threat context: [...]"
)
```

### Band Coordination
Orchestrates ALL agents. The hub through which every message passes.

---

## Agent 9 — Executive Decision

**Band Room:** `executive-room`
**Architecture:** 4 sequential sub-agents (CFO → Legal → Ops → CEO)
**LLM:** Gemini 1.5 Pro
**Trigger:** @mention from Incident Commander when risk score ≥ 70

### What It Does
Translates the technical incident into a business-level decision. Four sub-agents each analyze from their domain perspective, then the CEO agent synthesizes all inputs into a final, binding decision with full justification.

### Sub-Agents

#### CFO Sub-Agent
```
Input: Risk score, affected systems, breach probability
Output:
  - Estimated breach cost (regulatory fines + remediation + reputational)
  - Cost of proposed containment actions
  - Cyber insurance coverage assessment
  - ROI of immediate shutdown vs continued operation
```

#### Legal Sub-Agent
```
Input: Data types at risk, countries involved, incident timeline
Output:
  - Regulatory obligations (GDPR 72h notification, India DPDP Act)
  - Potential liability exposure
  - Required notifications (customers, regulators, law enforcement)
  - Legal hold requirements for forensic evidence
```

#### Operations Sub-Agent
```
Input: Blue Team playbook, affected systems, business hours
Output:
  - Business continuity impact assessment
  - Systems that must go offline and for how long
  - Stakeholder communication plan
  - Recovery time estimate
```

#### CEO Sub-Agent
```
Input: CFO report + Legal report + Ops report + Incident Commander brief
Output:
  - FINAL DECISION: one of three paths:
    A) CONTAIN: Isolate affected systems, continue operations
    B) SHUTDOWN: Take all systems offline, full forensic investigation
    C) ESCALATE: Notify law enforcement, engage external incident response
  - Justification (3-4 sentences)
  - Immediate next steps
  - Communication to board
```

### Output Format
```json
{
  "executive_decision": {
    "cfo": {
      "breach_cost_estimate": "$2,400,000",
      "containment_cost": "$180,000",
      "insurance_coverage": "$1,000,000",
      "recommendation": "Immediate containment is 13x cheaper than breach"
    },
    "legal": {
      "regulations_triggered": ["GDPR Article 33", "India DPDP Act Section 8"],
      "notification_deadline": "72 hours from detection",
      "liability_exposure": "Up to €20M or 4% annual turnover",
      "recommendation": "Notify DPA within 24h to demonstrate good faith"
    },
    "operations": {
      "systems_offline": ["Customer portal (4h)", "Internal email (2h)"],
      "business_impact": "Customer portal unavailable during maintenance window",
      "recovery_estimate": "6-8 hours to full operations",
      "recommendation": "Schedule maintenance for 2:00-6:00 AM to minimize impact"
    },
    "ceo": {
      "decision": "CONTAIN",
      "action": "Isolate all affected systems immediately. Notify data protection authorities within 24 hours. Engage legal team. Customer portal offline for scheduled maintenance window.",
      "justification": "Containment cost ($180K) is substantially lower than projected breach cost ($2.4M). Regulatory obligations require timely disclosure. Customer impact minimized by off-hours maintenance window.",
      "board_communication": "Security incident contained. Systems being hardened. No evidence of data exfiltration. Full post-incident report within 48 hours."
    }
  },
  "decision_timestamp": "2026-06-19T08:52:33Z",
  "audit_trail_id": "FUSION-INC-2026-001"
}
```

### Band Coordination
Final step in the chain. Sends complete decision to Incident Commander for archiving.

---

## Adding New Agents

To add a new agent to Fusion:

1. Create `/agents/your_agent.py` extending `BaseAgent`
2. Define your LangGraph `StateGraph` with typed state
3. Register the agent in `run.py`
4. Create a new Band room in `scripts/setup_band_rooms.py`
5. Update Incident Commander's routing logic
6. Add the agent node to the React Flow graph in the dashboard

---

*Fusion — 9 agents. All seeing. Never sleeps.*
