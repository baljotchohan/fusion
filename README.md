# FUSION ⚡
### AI-Powered Venture Capital Investment Committee Swarm

> **Five specialist AI agents coordinating through Band to autonomously audit startup pitch decks, conduct inter-agent debates, and deliver a final INVEST/PASS verdict with a weighted risk scorecard in under 5 minutes.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![Band SDK](https://img.shields.io/badge/Band-SDK-purple.svg)](https://docs.thenvoi.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://langchain-ai.github.io/langgraph)
[![Status](https://img.shields.io/badge/status-production_ready-brightgreen.svg)]()

---

## What is FUSION?

Venture Capital due diligence takes weeks, costs upwards of $100k–$500k in legal and technical audits, and still fails to flag critical deal-breakers (FTX, Theranos, and WeWork all passed human diligence). Specialist auditors work in silos—the legal counsel rarely coordinates with the software architect, leaving massive blindspots.

**FUSION solves this.**

FUSION deploys a swarm of 5 specialized AI partner agents that coordinate over the **Band AI** platform. When a startup pitch is uploaded, the partners execute independent audits, debate conflicting findings, resolve details on shared memory, and deliver a unified investment verdict with a weighted risk scorecard.

```
Startup Pitch Uploaded (JSON/PDF)
            │
            ▼
┌──────────────────────────────────────┐
│  💼 Managing Partner (Chair)         │
└──────┬────────────────────────┬──────┘
       │                        │
       ├─► 📊 Financial Partner  ├─► ⚖️ Legal Partner
       │   (burn, LTV:CAC, concentration)   (litigation, compliance, IP)
       │                        │
       ├─► 🔧 Technical Partner  ├─► 📈 Market Partner
       │   (EOL runtimes, leaks, CVEs)    (TAM, headwinds, competitors)
       │                        │
       ▼                        ▼
┌──────────────────────────────────────┐
│  Shared Memory Incident Graph        │
└──────┬────────────────────────┬──────┘
       │                        │ (Debate resolution)
       ▼                        ▼
┌──────────────────────────────────────┐
│  ⚖️ Committee Verdict Synthesis      │
│  - INVEST / CONDITIONAL / PASS       │
│  - Weighted Risk Scorecard (1-10)     │
└──────┬────────────────────────┬──────┘
       │
       ├─► 📄 Publication-grade PDF Report
       └─► 🔌 MCP Server (Claude Desktop tools)
```

---

## The 5 Investment Partners

| Partner | Band Room | Domain Focus | Weight | @mention |
|---|---|---|---|---|
| **💼 Managing Partner** | `managing-partner-room` | Committee Chair; orchestrates deliberations, triggers audits, and synthesizes final verdict. | **Chair** | `@managing-partner` |
| **📊 Financial Partner** | `finance-partner-room` | Forensic accounting, runway, margins, LTV:CAC, contract concentration. | **30%** | `@financial-partner` |
| **⚖️ Legal Partner** | `legal-partner-room` | Litigation, state licenses, regulatory compliance (CFPB, SEC), cap tables. | **25%** | `@financial-partner` |
| **🔧 Technical Partner** | `tech-partner-room` | Tech stack viability, EOL runtimes, security posture (PCI-DSS), code leak scans. | **25%** | `@technical-partner` |
| **📈 Market Partner** | `market-partner-room` | TAM validation, growth claims, competitive landscapes, industry headwinds. | **20%** | `@market-partner` |

---

## Features

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
│                    │  Memory   │ │ Gemini /  │ │ GitHub     │  │
│                    │  Graph    │ │ Groq /    │ │ ReportLab  │  │
│                    │ (Graphify)│ │Featherless│ │  (PDF)     │  │
│                    └───────────┘ └───────────┘ └────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MCP Server — external AI apps recruit the partner swarm   │  │
│  │  chat_with_managing_partner · get_deal_record · etc.     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
*   Python 3.11+
*   Node.js 18+
*   Gemini API Key from [Google AI Studio](https://aistudio.google.com)

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/fusion.git
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
# LLM Providers
GOOGLE_API_KEY=your_gemini_api_key

# Band Platform Settings (set to false to connect to real ws://app.thenvoi.com)
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

FUSION exposes its entire investment committee to external AI tools (such as Claude Desktop) using standard stdio transport.

### Register FUSION with Claude Desktop
Open your Claude Desktop config file:
*   **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the FUSION server:
```json
{
  "mcpServers": {
    "fusion-committee": {
      "command": "python3",
      "args": ["/Users/baljotchohan/Desktop/fusion/mcp_server.py"],
      "env": {
        "FUSION_API_URL": "http://localhost:8000"
      }
    }
  }
}
```
Restart Claude Desktop. You can now chat directly with the FUSION Managing Partner:
> *"Analyze this startup Pitch deck for RetailPulse. Tell me what the technical and financial risk is, and whether the committee recommends investing."*

---

## 📄 Professional PDF Generator

The ReportLab engine in [core/pdf_generator.py](file:///Users/baljotchohan/Desktop/fusion/core/pdf_generator.py) produces institutional-grade diligence reports.
*   **Cover Page:** Outlines target company metadata alongside a color-coded **Verdict Badge** (Emerald Green for `INVEST`, Orange for `CONDITIONAL`, Crimson Red for `PASS`).
*   **Structured Scorecards:** Renders risk scorecards in clean grids indicating weighted risk score distribution.
*   **Debate Timeline:** Compiles cron logs, timestamps, and partner findings into clean cards, wrapping paragraphs to prevent orphan line page-breaks.

---

## 🚀 Deployment

### Backend (Railway)
FUSION is configured for instant deployment on Railway using the included [railway.json](railway.json) configuration and `Procfile`.
1. Connect your GitHub repository to Railway.
2. Add your environment variables (`GOOGLE_API_KEY`, etc.).
3. Railway will build and serve the application automatically.

### Frontend (Vercel)
Deploy the Next.js frontend to Vercel:
1. Specify `frontend` as the **Root Directory**.
2. Add the environment variables:
   - `NEXT_PUBLIC_API_URL` = `https://your-backend.railway.app`
   - `NEXT_PUBLIC_WS_URL` = `wss://your-backend.railway.app/ws`
3. Vercel will host the boardroom interface statically.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.