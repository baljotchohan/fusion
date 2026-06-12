# Fusion — Project Memory & Agent Guide
This file serves as the persistent, single-source-of-truth project memory for **fusion** (formerly ACDCC). It contains the complete system architecture, data models, developer guidelines, and hackathon win-conditions so that any developer or AI coding agent can immediately understand the project and build features.

---

## 1. System Overview & Core Goal
**fusion** is an Autonomous Cyber Defense Command Center built for the Band of Agents Hackathon (June 2026).
* **The Problem:** Modern Security Operations Centers (SOCs) can detect threats, but responding to a live incident requires manual human coordination across Security, IT, Legal, Finance, and the C-Suite, taking hours or days.
* **The Solution:** fusion automates this entire response chain using 9 specialized AI agents coordinating in real time through **Band** chat rooms, reducing response and business-decision time to under 3 minutes.
* **The Payoff:** The system scales from technical detection up to a business-level CEO decision (e.g., Contain, Shutdown, or Escalate) backed by financial, legal, and operational assessments with a full audit log.

---

## 2. Technology Stack & Directory Structure

### Stack Components
* **Orchestration / Bus:** [Band SDK](https://docs.thenvoi.com) (Python wrapper: `thenvoi`)
* **Agent Flow / State:** [LangGraph](https://langchain-ai.github.io/langgraph)
* **API / WebSockets:** Python 3.11 + FastAPI + Uvicorn
* **Primary LLM:** Google Gemini 2.0 Flash (high-speed reasoning)
* **Backup/Partner LLM:** Featherless AI (running Qwen 2.5 72B / Llama 3.1 8B for partner prizes)
* **Database & Static Data:** Local JSON files for digital twin (`company.json`), email logs, and MITRE ATT&CK (`enterprise-attack.json`)
* **Dashboard Front-end:** Next.js 14 + React + Tailwind CSS + React Flow (agent graph visualization)

### Directory Structure
```
fusion/
├── README.md               ← High-level project readme
├── AGENTS.md               ← Detailed agent documentation
├── SETUP.md                ← Step-by-step setup guide
├── CONTRIBUTING.md         ← Code guidelines
├── requirements.txt        ← Backend dependencies
├── run.py                  ← Entry point (starts FastAPI + all agents)
├── .env.example            ← Env variables template
├── agent_config.example.yaml ← Band credentials template
├── research.md             ← Hackathon research & playbook
│
├── core/                   ← Shared library code
│   ├── base_agent.py       ← Base agent class inheriting Band client
│   ├── band_client.py      ← Band API/WS connections wrapper
│   ├── mitre_lookup.py     ← Local MITRE ATT&CK query utility
│   ├── cve_lookup.py       ← Async NVD CVE API query utility
│   └── event_bus.py        ← Local event broadcaster (FastAPI WS bridge)
│
├── agents/                 ← The 9 Band agents
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
├── api/                    ← FastAPI backend application
│   ├── main.py             ← API routes and websocket server
│   └── schemas.py          ← Pydantic schemas
│
├── data/                   ← Data mockups
│   ├── company.json        ← Digital twin profile of TechCorp Inc
│   ├── network_map.json    ← Corporate network graph
│   ├── email_logs.json     ← Log files for IOC scanning
│   └── enterprise-attack.json ← MITRE ATT&CK Database (Downloaded)
│
└── frontend/               ← Next.js Dashboard
    ├── pages/index.tsx     ← War Room Dashboard main view
    ├── components/
    │   ├── AgentGraph.tsx  ← React Flow graph view
    │   ├── AgentCard.tsx   ← Agent status cards
    │   └── LiveLog.tsx     ← WS log streamer
    └── hooks/
        └── useAgentWebSocket.ts
```

---

## 3. The 9 Security & Executive Agents
Each agent has a specific room in the Band workspace and maps to a LangGraph `StateGraph` flow:

| # | Agent Name | Band Room | Key Responsibility / Logic Nodes |
|---|---|---|---|
| 1 | **Threat Intelligence** | `threat-intel-room` | Analyzes trigger alerts; queries MITRE ATT&CK & NVD CVE; outputs threat severity score. |
| 2 | **Recon** | `recon-room` | Inspects target systems in `company.json` digital twin; maps vulnerable systems & open ports. |
| 3 | **Red Team** | `redteam-room` | Simulates attacker's next lateral moves; outputs an attack path tree. |
| 4 | **Attack Path Analysis** | `attack-path-room` | Evaluates likelihood of lateral movement; outputs weighted risk score (1-100). |
| 5 | **Detection** | `detection-room` | Scans corporate logs/emails for Indicators of Compromise (IOCs) to confirm active compromise. |
| 6 | **Malware Investigation** | `malware-room` | Analyzes file hashes, metadata, entropy, and recommends containment steps. |
| 7 | **Blue Team Defense** | `blueteam-room` | Creates mitigation playbooks mapped to MITRE mitigations; calculates downtime. |
| 8 | **Incident Commander** | `incident-command-room` | Coordinates the workflow; monitors all rooms; routes messages; recruits agents dynamically. |
| 9 | **Executive Decision** | `executive-room` | Sequential sub-agents (CFO $\rightarrow$ Legal $\rightarrow$ Ops $\rightarrow$ CEO) debate and output final containment decision. |

---

## 4. Band SDK & Handoff Coordination
* **Chat-Room Mentions:** Communication must happen through Band using `@mentions`. Non-mentioned agents ignore messages to reduce noise.
* **Platform Tools:** Every agent uses tools like `thenvoi_send_message` to speak, and `thenvoi_send_event` to report operational updates to the event bus.
* **Dynamic Recruitment:** The Incident Commander agent uses `thenvoi_lookup_peers()` and `thenvoi_add_participant()` to recruit agents into rooms dynamically during an active threat.

---

## 5. Development Guidelines
1. **Always Use Async/Await:** Network and API operations must be non-blocking. Use `aiohttp` instead of `requests`.
2. **Strict Project Naming:** Use the name **fusion** (all lowercase in folders/configs, or **Fusion** in documentation). Do not use the old name "ACDCC".
3. **Mock Mode (`BAND_MOCK=true`):** For offline testing, configure an in-memory mock bus in `core/band_client.py` so agents can communicate locally without connecting to real Band WebSocket servers.
4. **Data Sources:** 
   * Maintain the downloaded `data/enterprise-attack.json` file.
   * Query the NVD CVE API with rate limits in mind (stagger requests).
5. **Dashboard WebSockets:** Ensure all status changes (idle $\rightarrow$ working $\rightarrow$ done/alert) are broadcasted to the Next.js War Room using FastAPI WebSocket manager.

---

## 6. Memory Optimization via Graphify
To reduce token consumption and help agents navigate the codebase instantly, the `graphifyy` tool maps this repository into a structured knowledge graph.

### Graphify Setup & Command Reference
* **Installation:**
  `uv tool install graphifyy` or `pip install graphifyy`
* **Project Registration:**
  `graphify install --project` (Runs once to bind Graphify to the local workspace)
* **Index/Map Codebase:**
  `graphify .` (Generates the knowledge graph structure)
* **Output Artifacts (created in `graphify-out/`):**
  * `graph.json`: The queryable node-link structure representing file dependency mapping.
  * `graph.html`: Visual codebase network representation.
  * `GRAPH_REPORT.md`: Highlighted architectural guide.
* **Querying Codebase via CLI:**
  * Search paths: `graphify query "recon_agent"`
  * Path tracing: `graphify path core/base_agent.py agents/recon.py`

*Tip for agents:* Before performing large file reads, read `graphify-out/GRAPH_REPORT.md` or query `graph.json` to pinpoint exactly which modules contain the definitions you need to modify.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
