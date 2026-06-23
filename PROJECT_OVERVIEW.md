# FUSION — Full Project Overview & Architecture Guide

Welcome to **FUSION**, the AI-Powered Venture Capital Investment Committee. This document explains what FUSION is, how it is structured, its key features, and how the 5 specialized AI VC partner agents collaborate to conduct due diligence, debate issues in real-time, and deliver a unified investment verdict.

---

## 1. What is FUSION? (The Big Picture)

FUSION is a **digital venture capital war room** run entirely by AI. Instead of evaluating startups in separate silos (where the lawyer doesn't speak to the system architect, and the financial analyst misses the patent litigation), FUSION deploys a **swarm of 5 specialized AI partner agents** to audit a startup simultaneously:

1. **Managing Partner** (Committee Chair — orchestrates the review and delivers the final verdict)
2. **Financial Partner** (Forensic Accounting — TAM, burn rate, LTV:CAC, runway)
3. **Legal Partner** (M&A Legal — litigation exposure, state licensing, regulatory compliance, IP status)
4. **Technical Partner** (System Architecture & Security — EOL stacks, SSN storage, data security, scalability)
5. **Market Partner** (Market Research — sector growth, competition, industry headwinds)

The swarm collaborates via the **Band AI Platform** using `@mentions` to share findings, identify contradictions in the data room, run boardroom debates, and compute a final weighted risk scorecard.

---

## 2. Core Features

### 📡 Real-Time WebSocket Collaboration
All 5 partner agents connect directly to the Band AI Platform (or an in-process mock bus). They communicate via WebSocket channels and **only activate when explicitly `@mentioned`**, allowing them to hold structured boardroom conversations without talking over one another.

### 🧠 Shared Team Memory Graph (Graphify)
The agents share a JSON-backed memory graph (located under `fusion_memory/`). FUSION logs every deal history, timeline, and learned risk pattern. If a startup presents a pattern the team has audited before, the agents reference past precedents to make faster, more consistent recommendations.

### 🛡️ Automatic LLM Fallback (Resilient Mode)
To ensure the diligence pipeline never crashes, the `llm_router.py` features a multi-provider fallback chain (Gemini -> Groq -> Featherless -> AI/ML API). If all cloud providers fail or keys are absent, the system degrades to a **local simulation engine** (`/mock-llm`) running OpenAI-compatible mock responses that stream deterministic, calculation-backed outcomes.

### 📊 Live Next.js Web Dashboard
A beautiful, real-time web dashboard showing the status of each agent (idle, auditing, debating), active deal timelines, live discussion logs, and the final interactive risk scorecard. It also supports custom pitch uploads (JSON, PDF, TXT, MD) and downloads of generated reports.

### 📄 Branded Report Generator
A ReportLab-based document compiler (`pdf_generator.py`) that exports publication-grade diligence reports. It formats the final committee verdict, risk scorecard, SWOT metrics, partner report cards, and targeted questions into Markdown and print-ready PDFs.

### 🔌 Model Context Protocol (MCP) Server
An enterprise-ready MCP server (`mcp_server.py`) that exposes the Investment Committee's capabilities as tools (`chat_with_managing_partner`, `get_deal_record`, etc.) to external AI clients like Claude Desktop.

---

## 3. How the Swarm Collaborates (Step-by-Step Flow)

Here is how the partners coordinate when a pitch deck is uploaded:

```
[Pitch Uploaded / Trigger Deal]
              │
              ▼
      💼 Managing Partner
              │
              ├─► @financial-partner (Audits unit economics, burn, runway)
              ├─► @legal-partner     (Audits lawsuits, licenses, regulatory risks)
              ├─► @technical-partner (Audits EOL tech debt, plaintext PII leaks)
              └─► @market-partner    (Audits TAM validity, industry headwinds)
              │
              ▼
    [Specialists Report Back to Room]
              │
              ▼
   👥 Boardroom Debate Round (Managing Partner resolves partner disagreements)
              │
              ▼
    ⚖️ Weighted Committee Verdict (Calculates exact 1-10 risk scorecard)
              │
              ▼
    📄 Publication-Grade PDF/MD Report Compiled
```

---

## 4. Directory & File Structure

Here is a breakdown of the repository's folders and files:

```
fusion/
├── agents/                     # 📂 Individual Agent Implementations
│   ├── managing_partner.py     # IC Chair: orchestrates audits and debates
│   ├── financial_partner.py    # Forensic accountant: unit economics & runway
│   ├── legal_partner.py        # M&A attorney: compliance & IP litigation
│   ├── technical_partner.py    # Systems architect: security & stack health
│   └── market_partner.py       # Market researcher: TAM & sector analysis
│
├── core/                       # 📂 Shared Engine & Utilities
│   ├── base_agent.py           # Base agent logic, model router & mock Band adapter
│   ├── band_client.py          # Band client wrapper (MockBandBus & RealBandBus)
│   ├── diligence_engine.py     # Deterministic scoring, SWOT, and question engine
│   ├── pitch_loader.py         # Data room reader: loads sections and parses uploads
│   ├── llm_router.py           # Multi-provider LLM router with fallbacks
│   ├── pdf_generator.py        # ReportLab PDF diligence report compiler
│   ├── memory_graph.py         # Shared memory database manager (Graphify)
│   ├── event_bus.py            # Local WebSocket pub/sub event bridge
│   └── rtdb.py                 # Firebase Realtime Database connector
│
├── api/                        # 📂 FastAPI Backend
│   ├── main.py                 # WebSocket server, /mock-llm and operational endpoints
│   ├── v1.py                   # Managing Partner chat, file uploads, settings
│   └── state.py                # sim_state: session tracking & concurrency lock
│
├── data/                       # 📂 Startup Data Rooms / Pitches
│   ├── novapay_pitch.json      # Primary demo company (12 hidden red flags)
│   ├── helios_pitch.json       # Clean energy demo
│   └── ...                     # Additional JSON and Markdown pitch files
│
├── fusion_memory/              # 📂 JSON databases for Graphify memory (Gitignored)
│
├── frontend/                   # 📂 Next.js Boardroom Dashboard
│   ├── pages/index.tsx         # Main dashboard war room UI
│   ├── components/             # UI widgets: RiskScorecard, AgentCard, ChatPanel
│   └── hooks/                  # WebSocket listener hooks
│
├── mcp_server.py               # 🔌 Model Context Protocol stdio adapter
└── run.py                      # 🚀 Server launcher (FastAPI + all 5 agents)
```

---

*FUSION — Five agents. One boardroom. No bad investments.*
