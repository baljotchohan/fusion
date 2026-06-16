# FUSION — Project Memory File
> Drop this file in ~/Desktop/fusion/ as FUSION_MEMORY.md
> Claude Code reads this automatically for full project context.
> Last updated: Jun 13, 2026

---

## Who Is Building This

**Baljot** — 2nd year BCA student, Punjab India. AI builder + AI journalist.
Lead dev: Python, FastAPI, Band SDK, LangGraph, agent logic, memory, MCP, Hugging Face Spaces deploy.
Teammate: frontend — Next.js, React, boardroom UI, Vercel deploy.
Other projects: Lirox (local Python AI research agent, Ollama/RAG), Antigravity (lifestyle brand).
Tools: Gemini API key, Featherless $25 credits, AI/ML API $10 credits, Ollama local (Gemma/Kimi).

---

## What FUSION Is

**FUSION** is an AI Investment Committee — 5 specialist AI agents that independently investigate a startup pitch, debate findings via Band, and deliver a final INVEST/PASS/CONDITIONAL verdict with a weighted risk scorecard in under 5 minutes.

**Tagline:** *"Five agents. One boardroom. No bad investments."*

**The problem it solves:** VC due diligence takes weeks, costs $100k–$500k, and still misses things (WeWork, Theranos, FTX all passed human review). Specialists work in silos — the lawyer doesn't see what the engineer found. FUSION coordinates all domains simultaneously and makes agents debate conflicts before the decision.

**Hackathon:** Band of Agents Hackathon on lablab.ai. Jun 12–19, 2026. Track: Regulated & High-Stakes Workflows. Prize pool $10,000+. Team name: Agent Core.

---

## The 5 Agents

| Agent | Band Room | Domain | @mention |
|---|---|---|---|
| Managing Partner | managing-partner-room | Chair — orchestrates, no analysis, delivers verdict | @managing-partner |
| Financial Partner | finance-partner-room | Forensic accounting: revenue concentration, burn, LTV:CAC, margins | @financial-partner |
| Legal Partner | legal-partner-room | Litigation, IP, compliance, cap table, CFPB/licenses | @legal-partner |
| Technical Partner | tech-partner-room | Tech stack EOL, PCI-DSS, security posture, breaches, scalability | @technical-partner |
| Market Partner | market-partner-room | TAM validity, sector growth vs claims, competition, headwinds | @market-partner |

**Weighted Risk Scoring:**
- Financial: 30%
- Legal: 25%
- Technical: 25%
- Market: 20%

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Agent framework | LangGraph + Band SDK (thenvoi) |
| Band install | `pip install "band-sdk[langgraph]"` |
| Primary LLM | Google Gemini 2.0 Flash (`GOOGLE_API_KEY`) |
| Fallback chain | Groq → Featherless AI → AI/ML API |
| Memory | Graphify — JSON files in `fusion_memory/` |
| File parsing | pypdf (PDF), utf-8 (TXT/MD), json.loads (JSON) |
| Frontend | Next.js 14 + React + Tailwind CSS |
| Real-time | WebSockets (FastAPI → Next.js dashboard) |
| Deploy — Backend | Hugging Face Spaces (Docker) |
| Deploy — Frontend | Vercel |
| MCP server | `mcp_server.py` (stdio transport) |

---

## Project File Structure

```
~/Desktop/fusion/
├── run.py                    ← Entry point: starts FastAPI + 5 agents
├── .env                      ← API keys + BAND_MOCK setting
├── .env.example              ← Template
├── requirements.txt          ← Add: pypdf>=4.0.0
├── Dockerfile                ← Docker config (Hugging Face Spaces) (exists)
├── agent_config.yaml         ← 5 agent IDs + API keys + room names
├── FUSION_COOK.md            ← Master fix + deploy prompt (run with Claude Code)
├── FUSION_MEMORY.md          ← This file
│
├── api/
│   ├── main.py               ← FastAPI app, /trigger-deal, /status, /reset, /ws
│   ├── v1.py                 ← All endpoints: /chat, /upload-pitch, /generate-report
│   └── state.py              ← sim_state (SimulationState class)
│
├── core/
│   ├── base_agent.py         ← LangGraph agent base + Band client
│   ├── band_client.py        ← Band SDK wrapper (RealBandBus + MockBandBus)
│   ├── pitch_loader.py       ← Tool: loads pitch JSON sections for agents
│   ├── llm_router.py         ← Multi-provider LLM with auto-fallback
│   ├── event_bus.py          ← FastAPI WebSocket event bridge
│   └── memory_graph.py       ← Shared deal memory (Graphify)
│
├── agents/
│   ├── managing_partner.py
│   ├── financial_partner.py
│   ├── legal_partner.py
│   ├── technical_partner.py
│   └── market_partner.py
│
├── data/
│   ├── novapay_pitch.json    ← Primary demo company (12 hidden problems)
│   └── pitch_{deal_id}.json  ← Uploaded company files (auto-generated)
│
├── scripts/
│   └── setup_band_rooms.py   ← Creates 5 Band rooms from agent_config.yaml
│
├── fusion_memory/            ← Gitignored. Graphify JSON files.
│   ├── incidents.json
│   ├── patterns.json
│   ├── agent_profiles.json
│   └── chat_history.json
│
└── frontend/
    ├── pages/index.tsx       ← Main boardroom UI
    └── components/           ← ChatPanel, AgentCard, RiskScorecard, etc.
```

---

## Current Codebase State (Jun 13, 2026)

### ✅ Working
- FastAPI backend running on localhost:8000
- 5 agents wired to Band rooms (mock mode)
- Memory graph (Graphify) — incidents, patterns, chat history persist
- Managing Partner chat with LLM works (Gemini primary)
- Intent classification + thinking steps animation
- WebSocket event streaming to frontend
- Next.js frontend running on localhost:3000
- Verdict rendering (risk score, confidence, PASS/INVEST/CONDITIONAL)
- Download Research Report button (UI only, not wired)
- MCP server file exists

### ❌ Not Built Yet (FUSION_COOK.md fixes these)
- `/api/v1/upload-pitch` endpoint — does not exist
- `pitch_loader.py` is hardcoded to `novapay_pitch.json` regardless of upload
- `state.py` missing `active_pitch_file` field
- `@mention` routing — all chat goes to Managing Partner only
- `/api/v1/generate-report` endpoint — does not exist
- Frontend uploader wired to nothing
- Download Report button calls nothing
- `llm_router.py` system prompt says "cybersecurity expert / ARGUS SOC team" (wrong)
- `pypdf` not in requirements.txt

---

## What FUSION_COOK.md Does

Master prompt for Claude Code. Run it at `~/Desktop/fusion` to apply all fixes.

```bash
# Option 1 — Claude Code CLI
claude --print < FUSION_COOK.md

# Option 2 — paste into claude.ai chat
```

**5 phases:**
1. Backend fixes (state.py, pitch_loader.py, llm_router.py, upload endpoint, @mention routing, report generation)
2. Frontend fixes (wire uploader, wire download button)
3. Integration tests (upload SnapHire doc, @mention test, report test)
4. Hugging Face Spaces + Vercel deploy
5. Final test suite

---

## Demo Companies

### NovaPay Inc — Primary Demo
Fake BNPL fintech. Series A $10M at $40M post-money. Claims 200% YoY growth.
**12 hidden problems:**
- Financial: 78% ARR from Amazon (contract expires 3mo post-close), 8mo runway, LTV:CAC 2.5x
- Legal: Klarna lawsuit $8M damages (80% of raise), CFPB non-compliant, unlicensed 4 states
- Technical: Node.js 14 EOL, plaintext SSNs in MongoDB, no PCI-DSS, undisclosed 2024 breach
- Market: BNPL sector declining 12% YoY, VC funding down 67%, vs Klarna/Affirm/Block
**Expected verdict:** PASS, 91% confidence, 9.3/10 risk

### SnapHire Technologies — Test / Backup
Fake HR tech AI recruiting SaaS. Series B $15M at $60M post-money. Claims 200% YoY.
**Key problems:**
- Financial: 71% ARR from Microsoft (contract under "renewal review"), 7mo runway, 48% gross margin
- Legal: EEOC investigation for algorithmic bias, NY Local Law 144 non-compliant, LinkedIn scraping
- Technical: SOC2 Type 1 only (not Type 2), single-region AWS, original CTO departed (buried as "advisor")
- Market: HR tech VC funding down 58% YoY, competing vs LinkedIn/Greenhouse/Workday
**File location:** Claude outputs / copy to `data/snaphire_pitch_brief.md`

---

## @Mention System (How It Should Work)

User types in the chat bar:
```
@financial-partner what's the biggest red flag you found?
```

Backend parses the @mention → routes to Financial Partner agent with:
- Its own system prompt (forensic accountant persona)
- Its domain memory (findings from fusion_memory/)
- The active pitch data (financials section)

Financial Partner responds in-persona:
```
📊 Financial Partner: 71% ARR from a single Microsoft client whose 
contract is under "renewal review" is a cliff-edge scenario. Combined 
with 7 months runway, there is no margin for error if that contract 
slips. @managing-partner — I recommend flagging this as deal-breaking.
```

Managing Partner can pick it up and @mention Legal for contract review — **chain reaction visible in UI**.

**All @mention variants mapped in `_MENTION_MAP`:**
- `@financial-partner`, `@finance-partner` → financial-partner
- `@legal-partner` → legal-partner
- `@technical-partner`, `@tech-partner` → technical-partner
- `@market-partner` → market-partner
- `@managing-partner`, `@commander` → managing-partner

---

## Environment Variables

| Variable | Value | Where |
|---|---|---|
| `GOOGLE_API_KEY` | your Gemini key | Hugging Face Spaces + local .env |
| `FEATHERLESS_API_KEY` | BOA26 credits key | Hugging Face Spaces + local .env |
| `AIMLAPI_KEY` | your AI/ML API key | Hugging Face Spaces + local .env |
| `GROQ_API_KEY` | optional fallback | Hugging Face Spaces + local .env |
| `BAND_API_KEY` | from band.ai dashboard | Hugging Face Spaces + local .env |
| `BAND_MOCK` | `true` local, `false` prod | Hugging Face Spaces + local .env |
| `ALLOWED_ORIGINS` | Vercel URL | Hugging Face Spaces only |
| `NEXT_PUBLIC_API_URL` | HF Space URL | Vercel dashboard |
| `MAX_UPLOAD_MB` | `10` (default) | Hugging Face Spaces optional |

**API keys NEVER go in GitHub. Hugging Face / Vercel dashboard only.**

---

## Band Real Mode Setup

1. Go to band.ai dashboard
2. Create 5 External Agents (one per partner):
   - `managing-partner`, `financial-partner`, `legal-partner`, `technical-partner`, `market-partner`
3. **Save each `agent_id` + `api_key` immediately** — key shown ONCE
4. Update `agent_config.yaml` with new IDs and keys
5. Run `python scripts/setup_band_rooms.py` with `BAND_API_KEY` set
6. Set `BAND_MOCK=false` in `.env`
7. Trigger a deal, verify @mentions appear in band.ai rooms

Band Pro active: promo `BANDHACK26` — **cancel before 1 month to avoid $17.99/mo charge**
SDK docs: docs.band.ai

---

## Deployment

### Hugging Face Spaces (Backend)
```bash
# Push to HF Space remote (e.g. from main or deploy-hf branch)
git push hf main
# Make sure environment variables are set in HF Space settings
```

### Vercel (Frontend)
```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://baljot07-fusion.hf.space" > .env.local
vercel --prod
# Set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL in Vercel dashboard too
```

---

## Codebase Knowledge Graph (Graphify)

To update the codebase knowledge graph and the Obsidian vault after code changes:

```bash
# Update the core graph.json, GRAPH_REPORT.md, and HTML visualizations
graphify update .

# Export updated markdown notes to your Obsidian vault
graphify export obsidian --dir obsidian_vault
```

---

## Hackathon Checklist

### Remaining (as of Jun 13)
- [ ] Apply FUSION_COOK.md (upload + @mention + report gen)
- [ ] Band real mode — 5 new rooms + agent keys in agent_config.yaml
- [ ] Hugging Face Spaces backend live URL
- [ ] Vercel frontend live URL
- [ ] AI/ML API wired in llm_router (partner prize: $1k cash + $1k credits)
- [ ] End-to-end NovaPay demo run under 5 minutes
- [ ] Record video ≤5min (split screen: Boardroom UI left, band.ai right)
- [ ] Create slides (required — not optional)
- [ ] Cover image (boardroom + 5 agent cards + PASS verdict)
- [ ] Fill lablab.ai submission form
- [ ] Submit before Jun 19, 8:30 PM IST
- [ ] Tweet @lablabai @band @FeatherlessAI immediately after

### Done
- [x] Codebase built and running
- [x] 5 agents on Band rooms (mock mode)
- [x] Memory graph working
- [x] UI running with verdict rendering
- [x] Band Pro activated (BANDHACK26)
- [x] Featherless $25 credits claimed
- [x] AI/ML API $10 credits claimed
- [x] Team confirmed on lablab.ai
- [x] NovaPay demo data ready (12 problems)
- [x] SnapHire test document created
- [x] FUSION_COOK.md master prompt ready

---

## Submission Content (Ready to Paste)

**Title:** FUSION — AI Investment Committee

**Short description (155 chars):**
5 AI partner agents investigate startup pitches in parallel via Band, debate findings, deliver INVEST/PASS verdict with weighted risk scorecard in under 5 minutes.

**Track:** Regulated & High-Stakes Workflows

**Tech tags:** Band SDK, LangGraph, FastAPI, Next.js, Gemini, Featherless AI, AI/ML API, Python

**Cover image concept:** Dark boardroom aesthetic. 5 agent cards arranged around a table. Center: red PASS verdict badge. Confidence: 91%.

---

## Post-Hackathon Vision

**Product:** FUSION SaaS — AI investment committee in a box.

**Who buys it:**
- Seed/Series A VC firms — $50–200k/yr for autonomous first-pass screening
- Corporate M&A teams — replaces $300k due diligence engagements
- Angel syndicates — institutional-grade DD for individuals
- Investment banks — augment analyst workflow

**Plans:**
- Free: NovaPay demo only
- Pro: Custom uploads, 10 deals/mo
- Enterprise: Unlimited + MCP server + API access

**MCP integration:**
```python
# Enterprise client's Claude instance
result = await mcp.call("fusion", "run_due_diligence", {
    "company": "TechStartup Inc",
    "pitch_url": "https://...",
    "raise_amount": "$15M Series B"
})
# Returns: {decision, confidence, risk_scores, agent_findings, report_url}
```

**Path:** lablab NEXT accelerator → build-in-public (GitHub stars, X threads) → VC/M&A accelerators → YC (AI agents in regulated finance = on-thesis)

---

## Key Learnings

- Band judges check band.ai rooms **directly** — real @mentions required, not mock
- Featherless + AI/ML API = partner prizes. Both use OpenAI-compatible endpoints, one-hour integration
- Video is 80% of judge decision. NovaPay demo script: 15s setup → 90s parallel analysis → 60s debate → 30s verdict
- The agent **debate** (Financial vs Market conflict) is the visual differentiator — no other hackathon project shows agents disagreeing and a chair resolving in real time
- Port 8000 conflict on startup = leftover process. Fix: `lsof -ti:8000 | xargs kill -9`
- `thenvoi` 0.1.0 is installed and imports cleanly

---

*FUSION — Five agents. One boardroom. No bad investments.*
