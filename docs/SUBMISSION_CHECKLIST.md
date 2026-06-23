# Submission Checklist — FUSION (Band of Agents Hackathon)

**Deadline:** Jun 19, 2026 3:00 PM UTC (8:30 PM IST)

---

## Pre-Submission Tasks

- [x] **Video Recorded**: 3-minute screen recording demonstrating FUSION's boardroom dashboard, parallel auditing, live inter-agent debate, and final verdict delivery.
- [x] **Slides Compiled**: 8–10 slides explaining the due diligence coordination problem, FUSION's 5-partner swarm architecture, and market vision.
- [x] **GitHub Repository Cleaned**:
  - [x] All API keys removed from `.env.example`.
  - [x] `.gitignore` blocks `.env`, `.venv/`, `node_modules/`, `agent_config.yaml`, and the `fusion_memory/` directory.
  - [x] README.md contains the live backend and frontend URLs.
- [x] **Backend Deployed (Hugging Face Spaces)**:
  - [x] Spaces Docker container running successfully.
  - [x] Environment variables configured: `GOOGLE_API_KEY`, `FEATHERLESS_API_KEY`, `AIMLAPI_KEY`, `BAND_API_KEY`, `BAND_MOCK=false`.
- [x] **Frontend Deployed (Vercel)**:
  - [x] Next.js application live.
  - [x] `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` correctly pointed at the Hugging Face Space.
- [x] **Band Platform Setup**:
  - [x] 5 external agents registered on the developer dashboard.
  - [x] Rooms created via `scripts/setup_band_rooms.py`.
- [x] **Memory Graph Verified**:
  - [x] `fusion_memory/` files dynamically save new deal findings.
  - [x] Agents query past incidents before performing new audits.
- [x] **MCP Server Verified**:
  - [x] stdio transport proxies requests to the active FastAPI endpoints.

---

## Submission Form Details (lablab.ai)

**Project Title (≤50 chars)**:
```
FUSION — AI-Powered VC Investment Committee
```

**Short Description (≤255 chars)**:
```
5 specialized AI partner agents audit startup pitches in parallel, conduct real-time boardroom debates via Band, and deliver a unified investment verdict with a weighted risk scorecard in under 5 minutes.
```

**Long Description (≥100 words)**:
```
FUSION is an AI-powered Investment Committee built for the Band of Agents Hackathon. 

When a startup pitch is uploaded, a Managing Partner agent briefs 4 domain specialists (Financial, Legal, Technical, and Market Partners) in parallel. The agents run targeted audits (uncovering revenue concentration, pending litigation, data security flaws, and market headwinds) and report back. 

Crucially, rather than working in silos, the partners debate conflicting findings in real time through Band room WebSockets. The Managing Partner synthesizes their debate, calculates a weighted risk scorecard, and produces a publication-grade PDF memo. 

FUSION features a shared memory graph (Graphify) so agents recognize and reference past deal precedents. The system operates on a resilient multi-provider LLM fallback chain and includes an enterprise-ready MCP server to invoke the committee as tools.
```

**Tech Tags**:
```
venture-capital, multi-agent, band-coordination, due-diligence, investment-committee, shared-memory, report-generation, python, fastapi, nextjs, gemini
```

---

## Video Script Outline (3 Minutes)

* **[0:00–0:15] Hook & Problem**: Explain that VC due diligence is slow, costly ($100k+), and fails due to team silos (e.g. WeWork, FTX). Introduce FUSION: "Five agents. One boardroom. No bad investments."
* **[0:15–0:50] Committee Convene & Parallel Audits**: Upload the `novapay_pitch.json` file. Show the Managing Partner briefing all 4 partners in parallel. Split screen to show the Band rooms and agents waking up simultaneously.
* **[0:50–1:30] Boardroom Debate & Synthesis**: Show the partners reporting findings (78% Amazon concentration, $8M Klarna lawsuit, Node 14 EOL stack/plaintext SSNs). Demonstrate the agents debating these trade-offs and the Managing Partner resolving the discussion.
* **[1:30–2:00] Verdict & Scorecard**: Deliver the final verdict card: `PASS` with a `9.3/10` weighted risk score and `91%` confidence. Click **Download PDF Report** to view the ReportLab generated memo.
* **[2:00–2:30] Shared Memory Graph**: Trigger a second audit (e.g., SnapHire). Show the agents referencing their shared memory graph (`fusion_memory/`) to immediately detect similar revenue concentration patterns and make faster decisions.
* **[2:30–2:50] Model Context Protocol (MCP)**: Quick showcase of an external LLM (like Claude Desktop) using the MCP server stdio tools to query FUSION deal records.
* **[2:50–3:00] Close**: Reiterate the business vision: VC due diligence in under 5 minutes.

---

*FUSION — Five agents. One boardroom. No bad investments.*
