# ARGUS — Full Project Overview & Architecture Guide

Welcome to **ARGUS**, the Autonomous Cyber Defense Command Center. This document explains what ARGUS is, how it is structured, its key features, and how the 9 specialized AI agents collaborate to defend a company against attacks in plain, easy-to-understand language.

---

## 1. What is ARGUS? (The Big Picture)
Think of ARGUS as a **digital cybersecurity war room** run entirely by AI. Instead of a single AI trying to do everything, ARGUS uses a **swarm of 9 specialized AI agents** (like Threat Intel, Recon, Red Team, and Blue Team). 

When an alert comes in (like a phishing email), the agents talk to each other in real-time over the **Band AI Platform** (app.thenvoi.com) using `@mentions` to investigate, simulate, analyze, and defend the network, culminating in a boardroom decision by a CEO agent.

---

## 2. Core Features

### 📡 Real-Time WebSocket Collaboration
All 9 agents connect directly to Band.ai using live WebSocket connections. They listen to a shared chat room and **only wake up when explicitly `@mentioned`**. This keeps them coordinated and prevents them from talking over one another.

### 🧠 Shared Team Memory Graph
The agents share a memory graph. If the team has handled a specific attack before (like a known phishing technique), they query the memory graph, see what defensive actions worked, and reuse the solution. When a new defense works, they write it back to memory.

### 🛡️ Automatic LLM Fallback (Resilient Mode)
If the primary LLM (Groq or Gemini) fails (e.g., due to rate limits or API outage), the system automatically degrades to a **local simulation engine** (`/mock-llm`) running Server-Sent Events (SSE) streaming. This ensures the defense pipeline never crashes.

### 📊 Live Next.js Web Dashboard
A beautiful web dashboard with visual node graphs shows the real-time status of each agent, active incidents, memory logs, and allows users to trigger attack simulations.

---

## 3. How the Swarm Collaborates (Step-by-Step Flow)

Here is exactly how the agents hand off tasks to one another when a phishing email is detected:

```
[Trigger] ──> @Threat-Intel (Analyzes alert)
                   │
                   └──> @Incident-Commander (Coordinates the response)
                             │
                             ├──> @Recon (Maps vulnerable systems)
                             ├──> @Detection (Scans mail/server logs)
                             │
                             └──> [Reports returned to Commander]
                                       │
                                       ├──> @Red-Team (Simulates attack path)
                                       ├──> @Malware-Investigation (Analyzes file)
                                       │
                                       └──> [Reports returned to Commander]
                                                 │
                                                 └──> @Attack-Path (Calculates Risk Score)
                                                           │
                                                           └──> If Risk >= 70:
                                                                 ├──> @Blue-Team (Writes playbook)
                                                                 └──> @Executive-Decision (C-Suite Verdict)
```

---

## 4. The 9 Specialized Agents

Here is a summary of the 9 agents, their roles, and what tools they use:

| # | Agent Name | Band Handle | Role / Action | Key Tools |
|---|---|---|---|---|
| **1** | **Incident Commander** | `@baljotchohan23/incident-commander` | The brain and router. Monitors the chat, tracks the timeline, and recruits specialists. | `build_incident_timeline`, `assess_escalation_needed` |
| **2** | **Threat Intelligence** | `@baljotchohan23/threat-intel` | Analyzes incoming alerts, matches MITRE TTPs, and looks up CVEs. | `search_mitre_attack`, `lookup_cve` |
| **3** | **Recon** | `@baljotchohan23/recon` | Maps the digital twin network topology and exposes vulnerable ports. | `scan_network`, `check_exposed_services` |
| **4** | **Detection** | `@baljotchohan23/detection` | Scans email and server logs to find active indicators of compromise (IOCs). | `scan_email_logs`, `scan_server_logs` |
| **5** | **Red Team** | `@baljotchohan23/red-team` | Simulates what the attacker will do next to reach high-value targets. | `simulate_attack_path` |
| **6** | **Malware Investigation** | `@baljotchohan23/malware-investigation` | Analyzes file metadata and extracts C2 domains/persistence keys. | `analyze_file_metadata`, `classify_malware` |
| **7** | **Attack Path Analysis** | `@baljotchohan23/attack-path` | Predicts attacker probability and calculates the final risk score (1-100). | `calculate_risk_score`, `predict_next_moves` |
| **8** | **Blue Team Defense** | `@baljotchohan23/blue-team` | Generates a prioritized mitigation playbook mapped to MITRE defenses. | `generate_defense_actions`, `estimate_downtime` |
| **9** | **Executive Decision** | `@baljotchohan23/executive-decision` | Simulates CFO, Legal, Ops, and CEO sub-agents to issue a final verdict. | `cfo_financial_assessment`, `ceo_final_decision` |

---

## 5. Directory & File Structure

Here is a breakdown of the repository's folders and files:

```
argus/
├── agents/                     # 📂 Individual Agent Implementations
│   ├── incident_commander.py   # Orchestrator agent
│   ├── threat_intel.py         # Threat Intel agent
│   ├── recon.py                # Network scanner agent
│   ├── detection.py            # Log analyst agent
│   ├── red_team.py             # Attacker simulator agent
│   ├── malware.py              # File investigator agent
│   ├── attack_path.py          # Risk scorer agent
│   ├── blue_team.py            # Playbook writer agent
│   └── executive_decision.py   # Boardroom decision agent
│
├── core/                       # 📂 Shared Engine & Utilities
│   ├── base_agent.py           # Base agent configuration, LLM setups, & @mention filtering
│   ├── band_client.py          # Mock client room bus helper
│   ├── event_bus.py            # Event router for real-time dashboard updates
│   ├── mitre_lookup.py         # MITRE ATT&CK lookup database utility
│   ├── cve_lookup.py           # NVD CVE lookup database utility
│   └── memory_graph.py         # Shared memory database manager
│
├── api/                        # 📂 FastAPI Backend REST & WebSocket Services
│   ├── main.py                 # FastAPI application, trigger endpoint, & Mock LLM endpoint
│   ├── v1.py                   # REST API routes (incident details, history, chat)
│   └── state.py                # Swarm running state
│
├── frontend/                   # 📂 Dashboard User Interface (Next.js & Tailwind CSS)
│   ├── src/app/                # Dashboard pages (Chats, War Room Graph, Memory Logs)
│   └── package.json            # Frontend package details
│
├── data/                       # 📂 Static Scenarios & Templates
│   └── phishing_email.json     # Trigger data for the phishing simulation
│
├── agent_config.yaml           # ⚙️ Real Band.ai Agent IDs and Keys (API Keys)
├── .env                        # ⚙️ Environment variables (API credentials, Mock flag)
├── run.py                      # 🚀 Entry point to launch backend & all 9 WebSocket agents
└── requirements.txt            # 📦 Python packages dependencies
```

---

## 6. How to Run and Interact

### Step 1: Start the Dashboard (Terminal 1)
```bash
cd frontend
npm run dev
```

### Step 2: Start the Backend and Swarm (Terminal 2)
```bash
./.venv/bin/python run.py
```

### Step 3: Trigger the Attack
Open the dashboard at `http://localhost:3000` and click **Simulate**, or send a manual POST request:
```bash
curl -X POST http://localhost:8000/api/trigger-attack
```
Once triggered, the Threat Intel agent will wake up on the Band WebSocket, and the entire 9-agent chain will run end-to-end!
