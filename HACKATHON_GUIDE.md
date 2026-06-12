# Fusion — Hackathon Kickoff & Architecture Guide

> The autonomous 9-agent Command Center for TechCorp Inc. Cyber Defense.

---

## 📖 Introduction & Real-World Use Case

Fusion is a production-ready autonomous Security Operations Center (SOC) framework designed to handle incident response without human intervention. By deploying 9 specialized AI agents executing concurrent investigations and cooperating via standard protocols, Fusion reduces the **Mean Time to Detect (MTTD)** and **Mean Time to Respond (MTTR)** from hours or days to **less than 3 minutes**.

### TechCorp Inc. Case Study
TechCorp is a mid-sized enterprise running a hybrid network with Active Directory, local email gateways, customer databases with PII, and C-Suite workstations. 
- **The Threat**: A spearphishing email lands in the CEO's inbox containing a malicious attachment (`Invoice_2026_0891.exe`).
- **The Challenge**: Standard EDRs might quarantine the file, but lateral movement, C2 communication, data exfiltration risks, and legal notification compliance requirements remain unresolved.
- **The Solution**: Fusion launches an autonomous incident response pipeline. The Incident Commander recruits and task-directs specialists in parallel, resulting in a cohesive risk assessment, a localized blue-team mitigation playbook, and a binding business-level executive decision.

---

## 🏗️ System Architecture & Agent Registry

Fusion uses a multi-agent choreography pattern. Each agent is modeled as a LangGraph state graph wrapped in the Band AI SDK.

```
                      ┌──────────────────────┐
                      │    FastAPI Server    │
                      └──────────┬───────────┘
                                 │ (WebSocket Stream)
                                 ▼
                     ┌───────────────────────┐
                     │   Next.js War Room    │
                     └───────────────────────┘
                                 ▲
                                 │ (Simulate / REST trigger)
                                 ▼
                       [ SOC Alert Sensor ]
                                 │
                                 ▼ (threat-intel-room)
                     ╔═══════════════════════╗
                     ║ Threat Intelligence   ║
                     ╚══════════╦════════════╝
                                │
                                ▼ (@Incident-Commander)
                     ╔═══════════════════════╗
                     ║  Incident Commander   ║◄──────────────────┐
                     ╚══════════╦════════════╝                   │
                                │ (Parallel Dispatch)            │
          ┌─────────────────────┼─────────────────────┐          │
          ▼ (recon-room)        ▼ (detection-room)    ▼ (malware)│ (Specialist
    ╔═══════════╗         ╔═══════════╗         ╔═══════════╗    │  Reports)
    ║   Recon   ║         ║ Detection ║         ║  Malware  ║    │
    ╚═════╦═════╝         ╚═════╦═════╝         ╚═════╦═════╝    │
          └─────────────────────┴─────────────────────┼──────────┘
                                                      │
                                                      ▼ (@Incident-Commander)
                                            ╔═══════════════════════╗
                                            ║  Incident Commander   ║
                                            ╚═════╦═════════════════╝
                                                  │
                                                  ▼ (attack-path-room)
                                            ╔═══════════════════════╗
                                            ║  Attack Path Analysis ║
                                            ╚═════╦═════════════════╝
                                                  │
                                                  ▼ (@Incident-Commander)
                                            ╔═══════════════════════╗
                                            ║  Incident Commander   ║
                                            ╚═════╦═════════════════╝
                                                  │ (Parallel Dispatch)
                                   ┌──────────────┴──────────────┐
                                   ▼ (blueteam-room)             ▼ (executive-room)
                             ╔═══════════╗                 ╔═══════════════════╗
                             ║ Blue Team ║                 ║Executive Decision ║
                             ╚═══════════╝                 ║  (CFO/Legal/Ops)  ║
                                                           ╚═════════╦═════════╝
                                                                     │
                                                                     ▼ (CEO Verdict)
                                                           ┌───────────────────┐
                                                           │ Final Resolution  │
                                                           └───────────────────┘
```

### 1. Threat Intelligence Agent (`threat-intel-room`)
- **LLM**: Gemini 2.0 Flash
- **Mission**: Ingest raw alerts, extract structured metadata, identify corresponding CVEs and MITRE ATT&CK techniques, and assign an initial threat severity score.
- **Tools**: NVD CVE Lookup API, MITRE ATT&CK Enterprise database search.

### 2. Reconnaissance Agent (`recon-room`)
- **LLM**: Gemini 2.0 Flash
- **Mission**: Map the external and internal attack surface using TechCorp's network topology. Identify open ports, active hosts, and systems matching the threat vector.
- **Tools**: `scan_network`, `find_vulnerable_systems`, `check_exposed_services`.

### 3. Detection Agent (`detection-room`)
- **LLM**: Gemini 2.0 Flash
- **Mission**: Interrogate system logs, email records, and access history to identify indicators of compromise (IOCs) and establish the initial breach timeline.
- **Tools**: `scan_email_logs`, `scan_server_logs`, `correlate_iocs`.

### 4. Red Team Agent (`redteam-room`)
- **LLM**: Gemini 2.0 Flash
- **Mission**: Simulate the attacker's logical progression from initial access to the target destination. Predict lateral movement paths and estimate threat actor dwell time.
- **Tools**: `simulate_attack_path`, `estimate_dwell_time`.

### 5. Malware Agent (`malware-room`)
- **LLM**: Mistral 7B (via Featherless AI)
- **Mission**: Inspect file entropy, check hashes, classify the malware family (e.g. Trojan, Ransomware), extract C2 domains, and provide static removal rules.
- **Tools**: `analyze_file_metadata`, `classify_malware`, `extract_iocs`, `recommend_containment`.

### 6. Attack Path Analysis Agent (`attack-path-room`)
- **LLM**: Gemini 2.0 Flash
- **Mission**: Synthesize the Red Team simulation with network asset details to output a final consolidated risk score (1-100), identify critical assets at risk, and list high-probability next moves.
- **Tools**: `calculate_risk_score`, `predict_next_moves`, `identify_critical_assets`.

### 7. Blue Team Defense Agent (`blueteam-room`)
- **LLM**: Gemini 2.0 Flash
- **Mission**: Map technical indicators to MITRE mitigations and produce a prioritized recovery and defense playbook with downtime estimates.
- **Tools**: `generate_defense_actions`, `map_to_mitre_mitigations`, `estimate_downtime`.

### 8. Incident Commander (`incident-command-room`)
- **LLM**: Gemini 1.5 Pro
- **Mission**: The coordinator and brain of the system. Tracks incident status, routes context between specialist rooms, manages execution phases, and issues C-Suite escalations.
- **Tools**: `build_incident_timeline`, `assess_escalation_needed`, `generate_status_update`, plus Band SDK room discovery and recruitment tools.

### 9. Executive Decision Agent (`executive-room`)
- **LLM**: Gemini 1.5 Pro
- **Mission**: Evaluates technical threat reports against business impacts. Spawns four sequential sub-agents:
  - **CFO Sub-Agent**: Models breach costs vs. containment costs and insurance coverage.
  - **Legal Sub-Agent**: Flags regulatory deadlines (GDPR 72-hour window, India DPDP Act) and liability exposures.
  - **Operations Sub-Agent**: Models downtime windows and recovery timelines.
  - **CEO Sub-Agent**: Synthesizes inputs into a final verdict: **CONTAIN**, **SHUTDOWN**, or **ESCALATE**.

---

## 🔄 Phased Incident Response Playbook

Fusion operates across five distinct phases, managed dynamically by the **Incident Commander**:

| Phase | Description | Inputs | Actions | Outputs |
|---|---|---|---|---|
| **Phase 1** | Alert & Initial Scope | Phishing Email Payload | Dispatch alerts to Threat Intel & Recon in parallel. | Initial alert logged, server status set to `working`. |
| **Phase 2** | Technical Triage | Intel & Recon Reports | Trigger Red Team simulation, Detection log scanner, and Malware reverse engineering. | IOCs extracted, potential lateral movement paths mapped. |
| **Phase 3** | Risk Quantification | Simulation & Log Reports | Dispatch to Attack Path Analysis to compute combined threat score. | Critical assets identified, risk score (1-100) calculated. |
| **Phase 4** | Business Mitigation | Risk Score & Triage | If risk score $\ge$ 70, dispatch parallel briefs to Blue Team and Executive Boardroom. | Financial assessment, legal analysis, and CEO final verdict. |
| **Phase 5** | Incident Resolution | All final briefs | Consolidate timeline, close audit log, and broadcast dashboard completion. | Unified incident summary, system state reset to `idle`. |

---

## 🔌 Band AI Platform & WebSocket Connectivity

When running in **Real Mode** (`BAND_MOCK=false`), Fusion connects to the Band AI developer platform:

1. **Authentication**: Credentials are loaded from `agent_config.yaml`. Each agent requires an `agent_id` and `api_key` generated from **band.ai**.
2. **WebSocket Loop**: Under the hood, `BaseAgent` initializes `PlatformRuntime` and registers `FusionLangGraphAdapter` which connects to:
   `wss://app.thenvoi.com/api/v1/socket/websocket`
3. **Trigger Logic**: Agents filter incoming socket frames. An agent only wakes up and runs its LangGraph if it is explicitly `@mentioned` via its agent handle in the room or if it's the Incident Commander receiving a user message.
4. **Tool Execution**:
   - `thenvoi_send_message` forwards context and notifies peers using structured `@mentions`.
   - `thenvoi_send_event` broadcasts telemetry (thoughts, completed tasks, errors) to the FastAPI event bus, which forwards them directly to the React dashboard.

---

## 🛠️ Model Context Protocol (MCP) Integrations

Fusion is built to connect seamlessly with two MCP servers to translate AI analysis into real-world structures.

### 1. StitchMCP Integration
Stitch allows Fusion to generate visual mockups, UI screen variations, and unified design systems for the dashboard.
- **Dynamic War Room Screens**: If the threat severity escalates, the Incident Commander can call `generate_screen_from_text` to automatically create a custom mitigation screen tailored to the active threat (e.g. an isolated system telemetry screen).
- **Aesthetic Hardening**: Ensure UI layout updates (represented in the `frontend` Next.js codebase) follow consistent design principles by utilizing `create_design_system` and `apply_design_system`.

### 2. Notion MCP Server
Integrate incident tracking and corporate security wikis directly into Notion.
- **Incident Archival**: Upon Phase 5 completion, the Incident Commander posts the final markdown report to a Notion Database using `API-post-page`.
- **Knowledge Sharing**: Before beginning Phase 2, the Incident Commander can search existing corporate security policies and incident logs using `API-post-search` to verify if similar corporate assets were previously targeted.

---

## 🚀 Transitioning to Real-World Production

To take Fusion from a hackathon sandbox to a production-grade enterprise deployment:

### 1. Hardening Environment Keys
Replace the local `.env` with a secure cloud secret manager (e.g., Google Cloud Secret Manager). Inject keys as environment variables during container orchestration.

### 2. Real SIEM & EDR Ingestion
Modify the data tools in `agents/detection.py` and `agents/recon.py`:
- Replace static JSON mappings (`data/email_logs.json`) with live API calls to your **SIEM** (e.g., Splunk, Chronicle, Datadog) or email security gateway (e.g., Google Workspace Email Audit API).
- Connect `agents/malware.py` directly to an automated sandbox service (e.g., VirusTotal API, Joe Sandbox).

### 3. Automated Containment Actions
Add active orchestration tools to the **Blue Team Defense** agent:
- Call Cloud APIs (e.g. AWS IAM, GCP Firewall rules, Active Directory LDAP) to programmatically quarantine hosts, block outbound firewall IPs, or invalidate user session tokens.
