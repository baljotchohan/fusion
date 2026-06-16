---
title: FUSION
emoji: ⚡
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# FUSION ⚡
### AI-Powered Venture Capital Investment Committee Swarm

> **Five specialist AI partners collaborating over Band to autonomously audit startup pitch decks, conduct inter-agent boardroom debates, and deliver a unified investment verdict with a weighted risk scorecard in under 5 minutes.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![Band SDK](https://img.shields.io/badge/Band-SDK-purple.svg)](https://docs.thenvoi.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://langchain-ai.github.io/langgraph)
[![Status](https://img.shields.io/badge/status-production_ready-brightgreen.svg)]()

---

## 💡 What is FUSION?

Venture Capital due diligence is notoriously slow, costly ($100k–$500k in legal/technical professional fees), and prone to silos. The corporate lawyer checking for IP liability rarely speaks to the systems architect auditing the codebase. This coordination failure explains how massive startups (FTX, Theranos, WeWork) pass human due diligence before collapsing.

**FUSION solves this.**

FUSION deploys a swarm of 5 specialized AI partner agents that coordinate over the **Band AI** platform. When a startup pitch is uploaded, the partners execute independent audits, debate conflicting findings in real-time, resolve details on shared memory, and deliver a unified investment verdict with a weighted risk scorecard.

```
                  Startup Pitch Uploaded (JSON/PDF)
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ 💼 Managing Partner      │
                  │   (Committee Chair)      │
                  └─────┬──────────────┬─────┘
                        │              │
         ┌──────────────┴──┐        ┌──┴──────────────┐
         ▼                 ▼        ▼                 ▼
 📊 Financial Partner  ⚖️ Legal   🔧 Tech Partner   📈 Market
   (ARR, burn, LTV)    Partner    (GitHub clone,   (TAM, CAGR,
                       (IP, law)   leaks, CVEs)    headwinds)
         │                 │        │                 │
         └──────────────┬──┴────────┴──┬──────────────┘
                        │              │
                        ▼              ▼
                  ┌──────────────────────────┐
                  │  Shared Memory Graph     │
                  │  (Debate & Resolution)   │
                  └─────────────┬────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ ⚖️ Committee Verdict      │
                  │  - INVEST / REJECT       │
                  │  - Weighted Risk Score   │
                  └─────────────┬────────────┘
                                │
         ┌──────────────────────┴──────────────────────┐
         ▼                                             ▼
📄 styled PDF Diligence Report             🔌 MCP Server (Claude/Cursor)
```

---

## 💼 The 5 Investment Partners

| Partner | Band Room | Domain Focus | Weight | Default Handle |
| :--- | :--- | :--- | :--- | :--- |
| **💼 Managing Partner** | `managing-partner-room` | Committee Chair; orchestrates deliberations, triggers audits, and synthesizes final verdict. | **Chair** | `@managing-partner` |
| **📊 Financial Partner** | `finance-partner-room` | Forensic accounting, runway, margins, LTV:CAC, contract concentration. | **30%** | `@financial-partner` |
| **⚖️ Legal Partner** | `legal-partner-room` | Litigation, state licenses, regulatory compliance (CFPB, SEC), cap tables. | **25%** | `@legal-partner` |
| **🔧 Technical Partner** | `tech-partner-room` | Tech stack viability, EOL runtimes, security posture (PCI-DSS), code leak scans. | **25%** | `@technical-partner` |
| **📈 Market Partner** | `market-partner-room` | TAM validation, growth claims, competitive landscapes, industry headwinds. | **20%** | `@market-partner` |

---

## ✨ Key Features

*   **Real-time Boardroom UI:** Dynamic war-room dashboard showing WebSocket-streamed logs, audit timeline, and live agent status.
*   **Weighted Risk Engine:** Aggregates partner risk scores (1-10) into a single weighted score, with automatic **diligence overrides** for fatal flaws (e.g., operating fintech without money transmitter licenses).
*   **Real Connectors:** Integrated GitHub Repository Scanner that clones startup codebases, audits packages for End-of-Life, and scans for leaked credentials.
*   **Branded PDF Exporter:** Compiles raw Markdown audits into styled, publication-ready PDF briefs via a custom ReportLab layout.
*   **Model Context Protocol (MCP):** Exposes the entire investment committee as tools so any external AI client (like Claude Desktop) can run audits directly from a chat window.

---

## 🛠️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FUSION Platform                          │
│                                                                 │
│  ┌─────────────────┐      ┌──────────────────┐                 │
│  │  Web UI (Next)  │◄────►│  REST API        │                 │
│  │ - Boardroom log │      │  FastAPI :8000   │                 │
│  │ - Risk Gauge    │      │  /api/v1/*       │                 │
│  │ - PDF Downloader│      │  WebSockets      │                 │
│  └─────────────────┘      └────────┬─────────┘                 │
│                                    │                            │
│                          ┌─────────▼─────────┐                  │
│                          │  Event Bus (async)│                  │
│                          └─────────┬─────────┘                 │
│         ┌─────────────┐  ┌─────────▼──────────────────────┐    │
│         │  Band SDK   │◄─┤  5 Partner Swarm (LangGraph)   │    │
│         │ WebSocket   │  │  Managing · Financial · Legal  │    │
│         │ @mentions   │  │  · Technical · Market Partner  │    │
│         └─────────────┘  └──┬─────────┬──────────┬────────┘    │
│                             │         │          │             │
│                    ┌────────▼──┐ ┌────▼──────┐ ┌─▼──────────┐  │
│                    │  Shared   │ │ LLM Router│ │ Connectors │  │
│                    │  Memory   │ │ AimleAPI/ │ │ GitHub     │  │
│                    │  Graph    │ │Featherless│ │  (PDF)     │  │
│                    └───────────┘ └───────────┘ └────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP Server — external AI apps recruit the partner swarm   │  │
│  │  chat_with_managing_partner · get_deal_record · etc.     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
*   Python 3.11+
*   Node.js 18+

### 1. Clone and Install

```bash
git clone https://github.com/baljotchohan/fusion.git
cd fusion

# Setup Python Virtual Environment & Install Dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Frontend Dependencies
cd frontend
npm install
cd ..
```

### 2. Configure Environment

Create a `.env` file in the root folder:
```bash
cp .env.example .env
```
Edit the `.env` with your API keys:
```env
# LLM Providers (e.g. AimLAPI, Featherless, etc.)
AIML_API_KEY=your_aimlapi_key

# Band Platform Settings
BAND_MOCK=true
BAND_API_KEY=your_band_api_key
```

### 3. Run the Platform

Start the FastAPI backend and Next.js frontend concurrently:

```bash
# Terminal 1: Start Backend Server
source .venv/bin/activate
python run.py

# Terminal 2: Start Frontend Dashboard
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the FUSION Boardroom.

---

## 🔌 Model Context Protocol (MCP) Workflow

FUSION exposes its entire investment committee to external AI clients (Claude Desktop, Cursor, custom agents) as **5 tools**:
*   `chat_with_managing_partner`
*   `get_deal_record`
*   `get_boardroom_verdict`
*   `query_deal_vault`
*   `learn_risk_pattern`

Discover them live at `GET /api/v1/system/mcp`.

### Option A — Remote URL (no install, works for anyone) ⭐
Once FUSION is running (`python run.py`), the committee is served over **streamable-HTTP** at **`/mcp`** on the same port. Add it as a remote MCP server by URL:

* **Local:** `http://localhost:8000/mcp`
* **Deployed:** `https://<your-deploy>/mcp`

```bash
# Claude Code example:
claude mcp add --transport http fusion https://<your-deploy>/mcp
```

### Option B — Local stdio
If you have the repo, the bundled `.mcp.json` registers FUSION automatically in Claude Code. For Claude Desktop, edit the config file:
*   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fusion": {
      "command": "python",
      "args": ["/path/to/fusion/mcp_server.py"],
      "env": { "FUSION_API_URL": "http://localhost:8000" }
    }
  }
}
```

---

## 📄 Professional PDF Generator

The ReportLab engine in `core/pdf_generator.py` produces institutional-grade diligence reports:
*   **Cover Page:** Outlines target company metadata alongside a color-coded **Verdict Badge** (Emerald Green for `INVEST`, Orange for `CONDITIONAL`, Crimson Red for `REJECT`).
*   **Structured Scorecards:** Renders risk scorecards in clean grids indicating weighted risk score distribution.
*   **Debate Timeline:** Compiles cron logs, timestamps, and partner findings into clean cards, wrapping paragraphs to prevent orphan line page-breaks.

---

## 🚀 Deployment

### Backend (Hugging Face Spaces)
FUSION is configured for deployment on Hugging Face Spaces as a Docker Space.
1. Create a new Space on Hugging Face and choose **Docker** as the SDK (with the Blank template, or Dockerfile will be detected).
2. Set your environment variables (like `AIMLAPI_KEY`, `GOOGLE_API_KEY`, `FEATHERLESS_API_KEY`, etc.) in the Space settings.
3. Push your repository to the Hugging Face Space remote (e.g., using `git push hf main` or via the `deploy-hf` branch workflow to clean history).

### Frontend (Vercel)
Deploy the Next.js frontend to Vercel:
1. Connect your GitHub repository to Vercel and specify `frontend` as the **Root Directory**.
2. Add the environment variables in Vercel:
   * `NEXT_PUBLIC_API_URL` = `https://your-space-name.hf.space` (e.g., `https://baljot07-fusion.hf.space`)
   * `NEXT_PUBLIC_WS_URL` = `wss://your-space-name.hf.space/ws` (e.g., `wss://baljot07-fusion.hf.space/ws`)
3. Vercel will host the boardroom interface statically.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.