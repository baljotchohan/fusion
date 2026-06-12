# VERDICT — AI Investment Committee | Project Memory & Agent Guide
This file is the persistent, single-source-of-truth for **VERDICT** — the pivot from ARGUS.
Contains complete architecture, agent roles, Band room mapping, and hackathon win-conditions.

---

## 1. System Overview & Core Goal
**VERDICT** is an AI-Powered Venture Capital Investment Committee built for the Band of Agents Hackathon (June 2026).
* **The Problem:** M&A due diligence and startup investment decisions take weeks, cost hundreds of thousands of dollars, and still fail — because human specialists work in silos and miss cross-domain risks.
* **The Solution:** VERDICT deploys 5 specialized AI partner agents that independently investigate a startup pitch across Finance, Legal, Technical, and Market domains — then debate findings through **Band** chat rooms — and deliver a final INVEST / PASS / CONDITIONAL verdict with confidence score.
* **The Payoff:** VC-grade due diligence in under 5 minutes. Visible agent debate. From pitch upload to committee decision — fully autonomous.
* **Demo:** Upload NovaPay Inc pitch → 5 agents discover 12 hidden red flags → Managing Partner delivers PASS at 91% confidence.

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
argus/
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

## 3. The 5 VERDICT Partner Agents
Each agent has a dedicated Band room and independently investigates one domain of the pitch:

| # | Agent | File | Band Room | Core Responsibility |
|---|---|---|---|---|
| 1 | **Managing Partner** | `agents/managing_partner.py` | `managing-partner-room` | Orchestrator — convenes committee, briefs all partners, synthesizes debate, delivers final verdict. |
| 2 | **Financial Partner** | `agents/financial_partner.py` | `finance-partner-room` | Revenue quality, burn rate, unit economics, customer concentration, valuation math. |
| 3 | **Legal Partner** | `agents/legal_partner.py` | `legal-partner-room` | Litigation exposure, IP status, regulatory compliance, founder background, data privacy. |
| 4 | **Technical Partner** | `agents/technical_partner.py` | `tech-partner-room` | Tech stack health, security posture, PCI-DSS, scalability, tech debt assessment. |
| 5 | **Market Partner** | `agents/market_partner.py` | `market-partner-room` | TAM validation, competitive landscape, sector timing, regulatory headwinds, defensibility. |

### Decision Flow
```
User submits deal → Managing Partner convenes committee
         ↓ (sends pitch brief to all 4 partner rooms simultaneously)
Financial Partner    Legal Partner    Technical Partner    Market Partner
         ↓                ↓                  ↓                   ↓
    findings ──────────────────────────────────────── findings
         ↓
Managing Partner synthesizes → INVEST / PASS / CONDITIONAL + confidence score
```

### Demo Company: NovaPay Inc (data/novapay_pitch.json)
Fake Series A fintech startup with 5 hidden red flags baked in:
1. **Financial**: 78% ARR from single Amazon client; contract expires 3 months post-close
2. **Legal**: Klarna patent lawsuit — $8M potential damages = 80% of the raise
3. **Technical**: Node.js 14 + MongoDB EOL, PII in plaintext, never had a pentest
4. **Market**: BNPL sector declining 12% YoY vs company's 200% growth claim
5. **Team**: CEO's prior startup investigated by SEC (case closed, no charges)

---

## 4. Band SDK & Handoff Coordination
* **Chat-Room Mentions:** Communication must happen through Band using `@mentions`. Non-mentioned agents ignore messages to reduce noise.
* **Platform Tools:** Every agent uses tools like `thenvoi_send_message` to speak, and `thenvoi_send_event` to report operational updates to the event bus.
* **Dynamic Recruitment:** The Incident Commander agent uses `thenvoi_lookup_peers()` and `thenvoi_add_participant()` to recruit agents into rooms dynamically during an active threat.

---

## 5. Development Guidelines
1. **Always Use Async/Await:** Network and API operations must be non-blocking. Use `aiohttp` instead of `requests`.
2. **Strict Project Naming:** Use the name **argus** (all lowercase in folders/configs, or **ARGUS** in documentation). Do not use the old name "ACDCC".
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
