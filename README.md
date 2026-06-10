# ⚡ ARGUS
### Autonomous Cyber Defense Command Center

> **9 AI agents coordinating through Band to autonomously defend against cyberattacks — from threat detection all the way to CEO-level business decision.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Band SDK](https://img.shields.io/badge/Band-SDK-purple.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

---

## What is ARGUS?

Modern companies can detect cyberattacks. The real bottleneck is the **human coordination** required to respond — pulling in IT, Legal, Finance, and the CEO during a live incident takes precious hours.

**ARGUS eliminates that bottleneck.**

When a threat is detected, ARGUS deploys 9 specialized AI agents that coordinate in real time through Band — triaging the threat, simulating the attack, building defenses, and delivering a final CEO-level business decision with a full audit trail. All autonomous. All in minutes.

```
Employee clicks phishing email
         ↓
[1] Threat Intel    → identifies attack techniques (MITRE ATT&CK)
[2] Recon           → maps the company's attack surface
[3] Red Team        → simulates what the attacker will do next
[4] Attack Path     → scores risk and predicts movement (87/100 CRITICAL)
[5] Detection       → scans logs for indicators of compromise
[6] Malware Inv.    → analyzes suspicious files
[7] Blue Team       → generates defensive countermeasures
[8] Incident Cmdr   → coordinates all agents through Band rooms
[9] Executive       → CFO + Legal + Ops + CEO make the business call
         ↓
Full audit trail exported. Incident closed.
```

---

## The 9 Agents

| # | Agent | Role | Input | Output |
|---|-------|------|-------|--------|
| 1 | **Threat Intelligence** | Identifies attack TTPs from MITRE ATT&CK + CVE data | Alert event | Threat report with severity score |
| 2 | **Recon** | Maps the company's attack surface | Company digital twin | Vulnerable systems list |
| 3 | **Red Team** | Simulates attacker's next moves using MITRE techniques | Recon report | Attack simulation path |
| 4 | **Attack Path Analysis** | Scores risk, predicts lateral movement | Red Team report | Risk score 1–100, predicted paths |
| 5 | **Detection** | Scans logs for indicators of compromise | Company logs | IOCs found, affected systems |
| 6 | **Malware Investigation** | Analyzes suspicious files and attachments | File metadata | Classification, containment actions |
| 7 | **Blue Team Defense** | Generates specific defensive countermeasures | Attack analysis | Action list (block, patch, isolate) |
| 8 | **Incident Commander** | Coordinates all agents via Band rooms | All reports | Routing, escalation, shared context |
| 9 | **Executive Decision** | CFO + Legal + Ops + CEO make business call | Full incident brief | Final decision + audit log |

> All agents coordinate through **Band** — real @mentions, task handoffs, and shared context across rooms.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARGUS Platform                           │
│                                                                 │
│  ┌─────────────────┐      ┌──────────────────┐                 │
│  │  Web UI (Next)  │◄────►│  REST API        │                 │
│  │ - Commander chat│      │  FastAPI :8000   │                 │
│  │ - Agent cards   │      │  /api/v1/*       │                 │
│  │ - Dev mode      │      │  WebSockets      │                 │
│  └─────────────────┘      └────────┬─────────┘                 │
│                                    │                            │
│                          ┌─────────▼─────────┐                  │
│                          │  Event Bus (async)│                  │
│                          └─────────┬─────────┘                  │
│         ┌─────────────┐  ┌─────────▼──────────────────────┐    │
│         │  Band SDK   │◄─┤  9 Agents (LangGraph)          │    │
│         │ Real rooms  │  │  Threat Intel · Recon · Red    │    │
│         │ @mentions   │  │  Team · Attack Path · Detect   │    │
│         └─────────────┘  │  · Malware · Blue Team ·       │    │
│                          │  Commander · Executive Board   │    │
│                          └──┬─────────┬──────────┬────────┘    │
│                             │         │          │             │
│                    ┌────────▼──┐ ┌────▼──────┐ ┌─▼──────────┐  │
│                    │  Shared   │ │ LLM Router│ │ Connectors │  │
│                    │  Memory   │ │ Gemini /  │ │ GitHub /   │  │
│                    │  Graph    │ │ Groq /    │ │ NVD CVE /  │  │
│                    │ (Graphify)│ │Featherless│ │ MITRE      │  │
│                    │           │ │/ AI/ML API│ │            │  │
│                    └───────────┘ └───────────┘ └────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP Server — external AI apps recruit the agent team    │  │
│  │  run_security_scan · analyze_threat · query_team_memory  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Coordination | [Band SDK](https://docs.thenvoi.com) |
| Agent Framework | [LangGraph](https://langchain-ai.github.io/langgraph) |
| LLMs (BYO keys) | Gemini (primary) · Groq · Featherless · AI/ML API — auto-fallback router |
| Shared Memory | Graphify incident graph (`argus_memory/`) — agents learn across incidents |
| Backend | Python 3.11 + FastAPI + WebSocket |
| Agent Recruitment | MCP server (`mcp_server.py`) for external AI apps |
| Real Connectors | GitHub API (secrets, Dependabot), NVD CVE API, MITRE ATT&CK |
| Frontend | Next.js + React + Tailwind CSS |
| Visualization | React Flow + D3.js |
| Total Cost | $0 |

---

## Demo Scenario

**Phishing attack on the CEO → full autonomous response in under 3 minutes**

1. Employee receives spearphishing email with malicious `.exe` attachment
2. ARGUS detects the event and deploys all 9 agents via Band coordination
3. Threat Intel identifies `T1566.001` (Spearphishing Attachment) — CVSS 9.8 CVE found
4. Recon maps 3 vulnerable servers on the internal network
5. Red Team simulates lateral movement — attack path to database server identified
6. Risk score: **87/100 — CRITICAL**
7. Blue Team generates: block IP, patch mail server, isolate CEO workstation
8. Executive Decision:
   - CFO: "Estimated breach cost $2.4M vs $180k containment"
   - Legal: "GDPR notification required within 72h — India DPDP also applies"
   - Ops: "Customer portal must go offline for 4 hours"
   - **CEO: "DECISION: Isolate all systems. Notify authorities. Engage legal team immediately."**
9. Full audit trail exported as incident report

## 🚀 Deployment

You can deploy the ARGUS system completely live for free:

### 1. Backend (Render)
Deploy the FastAPI backend + all 9 background agents to Render using the one-click button below:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/baljotchohan/argus)

**Configuration on Render:**
- Render will automatically parse the [render.yaml](file:///Users/baljotchohan/Desktop/argus/render.yaml) blueprint.
- During deployment, Render will prompt you to enter your LLM API keys (`GOOGLE_API_KEY`, etc.).
- Render will boot up the persistent server using `python run.py`.
- Once deployed, copy your Render service URL (e.g., `https://argus-backend.onrender.com`).

### 2. Frontend (Vercel)
Deploy the Next.js War Room Dashboard to Vercel:
1. Push your repository to GitHub.
2. Log into [vercel.com](https://vercel.com) and click **Add New Project**.
3. Select your `argus` repository and specify `frontend` as the **Root Directory** of the project.
4. Add the following **Environment Variables** in Vercel:
   - `NEXT_PUBLIC_API_URL` = `https://your-render-url.onrender.com` (your Render backend URL)
   - `NEXT_PUBLIC_WS_URL` = `wss://your-render-url.onrender.com/ws` (your Render WebSocket URL)
5. Click **Deploy**. Vercel will build and host the dashboard automatically.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- `uv` package manager (`pip install uv`)
- Band account at [band.ai](https://band.ai)
- Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/argus.git
cd argus

# Python backend
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Download MITRE ATT&CK Data

```bash
python scripts/download_mitre.py
```

### 4. Run ARGUS

```bash
# Terminal 1 — Backend + all agents
python run.py

# Terminal 2 — Dashboard
cd frontend && npm run dev

# Open http://localhost:3000
# Click SIMULATE ATTACK to start the demo
```

> **Hackathon note:** On June 12, add your Band API key and run `python scripts/setup_band_rooms.py` to create all 9 Band rooms instantly.

---

## 🧠 Shared Memory Graph

Agents don't work in isolation. Every incident is logged to a shared memory graph (`argus_memory/`) that all 9 agents read and write:

```json
{
  "INC-20260610-110117": {
    "metadata": {"trigger": "phishing_email", "threat_level": 7},
    "timeline": [
      {"agent": "threat_intel_agent", "finding": "Found CVE-2024-21378...", "tags": ["T1566.001"]},
      {"agent": "red_team_agent", "finding": "Simulated attack chain: 4 steps...", "tags": ["T1566.001", "T1021.002"]}
    ],
    "final_decision": "FINAL CEO DECISION: CONTAIN..."
  }
}
```

- Every agent has `query_team_memory`, `get_defense_recipe`, and `record_defense_recipe` tools.
- Blue Team countermeasures are automatically distilled into **learned defense recipes** per MITRE technique.
- Next phishing incident? The team queries memory: *"We've seen T1566.001 before — blocking these IoCs worked 85% of the time."* **Run #2 is faster than run #1.**

---

## 💬 Commander Chat & REST API

### Chat with the Incident Commander (plain English)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Are we under attack?"}'
```

Reporting an attack ("we got a phishing email") **activates the full 9-agent swarm**. Informational questions get answered from team memory. Also available as a live WebSocket at `/api/v1/ws/chat`.

### Scan a real GitHub repository

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo", "scan_type": "full"}'
```

Pulls **real** secret-scanning alerts, Dependabot vulnerabilities, and dependency manifests (set `GITHUB_TOKEN`), correlates them against live NVD CVE data, and returns a 1–10 threat level with recommendations.

### Analyze an IoC

```bash
curl -X POST http://localhost:8000/api/v1/analyze-threat \
  -H "Content-Type: application/json" \
  -d '{"indicator": "corp-billing.xyz", "ioc_type": "domain"}'
```

### Query incident memory

```bash
curl http://localhost:8000/api/v1/incidents                 # all incidents
curl http://localhost:8000/api/v1/incident/INC-20260610-110117
curl http://localhost:8000/api/v1/memory/stats              # what the team has learned
curl http://localhost:8000/api/v1/memory/similar/T1566.001  # similar past incidents
```

---

## 🔌 MCP Server — Recruit ARGUS from Any AI App

Expose the 9-agent team as tools to Claude (or any MCP client):

```bash
python mcp_server.py   # stdio transport; needs `python run.py` running
```

Claude Desktop config:

```json
{
  "mcpServers": {
    "argus": {"command": "python", "args": ["/path/to/argus/mcp_server.py"]}
  }
}
```

Tools exposed: `run_security_scan`, `analyze_threat`, `chat_with_commander`, `get_incident`, `get_team_decision`, `query_team_memory`, `learn_attack_pattern`.

---

## 🎮 UI Features

- **Agent cards** — real-time status (Standby → Active → Complete) with plain-English findings
- **Commander chat** — talk to the Incident Commander; it recruits the team
- **Threat gauge** — visual 0–100 combined risk level
- **Dev mode toggle** — `{ }` button flips every card and the chat to raw JSON event streams for hackers
- **Interactive handoff graph** — watch agents @mention each other through Band rooms live

---

## Project Structure

```
argus/
├── README.md
├── AGENTS.md               ← Detailed agent documentation
├── SETUP.md                ← Full setup guide
├── requirements.txt
├── run.py                  ← Entry point: starts everything
├── .env.example
├── agent_config.example.yaml
│
├── agents/                 ← 9 Band agents
│   ├── threat_intel.py
│   ├── recon.py
│   ├── red_team.py
│   ├── attack_path.py
│   ├── detection.py
│   ├── malware.py
│   ├── blue_team.py
│   ├── incident_commander.py
│   └── executive_decision.py
│
├── core/                   ← Shared utilities
│   ├── base_agent.py       ← LangGraph agent base + memory tools
│   ├── band_client.py      ← Band SDK wrapper (real + mock bus)
│   ├── memory_graph.py     ← Shared incident memory (Graphify)
│   ├── llm_router.py       ← Multi-provider LLM router w/ fallback
│   ├── mitre_lookup.py
│   ├── cve_lookup.py
│   └── event_bus.py        ← Async event bus + RealBandBus
│
├── connectors/             ← Real-world integrations
│   └── github_scanner.py   ← Live GitHub secrets/Dependabot scanning
│
├── api/                    ← FastAPI backend
│   ├── main.py             ← App, dashboard WS, demo trigger
│   └── v1.py               ← Chat, scan, analyze-threat, incidents
│
├── mcp_server.py           ← MCP server: recruit agents from AI apps
│
├── data/                   ← Static data
│   ├── company.json        ← Digital twin (TechCorp Inc)
│   ├── phishing_email.json ← Demo trigger
│   └── network_map.json
│
├── scripts/
│   ├── download_mitre.py
│   └── setup_band_rooms.py
│
└── frontend/               ← Next.js War Room Dashboard
    ├── pages/index.tsx
    ├── components/
    └── hooks/
```

---

## Team

**Agent Core** — Band of Agents Hackathon 2026 | lablab.ai

- **Baljot** — Lead Developer (Python, Band SDK, Agent Logic)
- **[Friend]** — Frontend & Co-Developer (Next.js, Dashboard)

---

## Band AI Integration

ARGUS uses Band as the real coordination layer. Each agent connects to a dedicated
Band room and communicates exclusively via @mentions and message handoffs.

```
threat-intel-room ──→ incident-command-room ──→ executive-room
recon-room ────────────────────↑
detection-room ─────────────────↑
redteam-room ───────────────────↑
malware-room ────────────────────↑
attack-path-room ────────────────↑
blueteam-room ───────────────────↑
```

Mock mode (`BAND_MOCK=true`) routes the same @mention handoffs through an in-process
`MockBandBus`, so the full 9-agent chain runs offline with zero API keys. Flip
`BAND_MOCK=false` to connect to live Band rooms — see [BAND_SWAP.md](BAND_SWAP.md).

## Track

**Regulated & High-Stakes Workflows** — autonomous multi-agent coordination
for enterprise incident response, from threat detection to CEO-level decision.

---

## Built With

- [Band AI](https://band.ai) — Multi-agent coordination infrastructure
- [LangGraph](https://langchain-ai.github.io/langgraph) — Agent framework
- [Google Gemini](https://aistudio.google.com) — LLM
- [Featherless AI](https://featherless.ai) — Open-source LLM inference
- [MITRE ATT&CK](https://attack.mitre.org) — Security intelligence
- [NVD CVE](https://nvd.nist.gov) — Vulnerability database

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*ARGUS — 9 agents. All seeing. Never sleeps.*