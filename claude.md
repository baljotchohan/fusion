# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**FUSION** is an AI-powered VC investment committee built for the Band of Agents Hackathon. Five specialist partner agents (Managing, Financial, Legal, Technical, Market) independently investigate a startup pitch, debate findings through **Band** (thenvoi) chat rooms, and deliver a final INVEST / PASS / CONDITIONAL verdict with a weighted risk score. The repo was pivoted from a cybersecurity project ("ARGUS") — the codebase still carries that name in env var prefixes (`ARGUS_*`), the `[ARGUS_AGENT: ...]` prompt marker, legacy agents, and legacy data. Treat **FUSION** as the current product name.

> Legacy note: `agents/` still contains 9 cybersecurity agents (`threat_intel.py`, `recon.py`, `red_team.py`, etc.) and `data/` holds `enterprise-attack.json`, `company.json`, `network_map.json`, `email_logs.json`. These are **not launched** by `run.py` and are dead weight from the ARGUS era — ignore them unless explicitly asked. The active agents are the 5 partners only.

## Commands

### Backend (Python 3.11+, repo root)
```bash
pip install -r requirements.txt           # install deps (use the .venv that exists)
python run.py                             # start FastAPI + all 5 partner agents on :8000
PORT=8001 python run.py                   # override port (run.py hard-fails if PORT is busy)
python test_fusion.py                     # full local test suite (env, data, imports, agents, API, chain, WS)
python test_band_connection.py            # smoke-test a single REAL Band WebSocket connection
python mcp_server.py                       # MCP stdio server (proxies to the running REST API)
```
There is no pytest setup — `test_fusion.py` and `test_argus.py` are standalone scripts run directly. They expect the backend importable from repo root and largely run in mock mode.

### Frontend (`frontend/`, Next.js 16 + React 19, **pages** router)
```bash
cd frontend
npm install
npm run dev        # next dev --webpack (dashboard on :3000)
npm run build
npm run lint       # eslint (flat config: eslint.config.mjs)
```
⚠️ Per `frontend/AGENTS.md`, this is a **non-standard, breaking-change build of Next.js** — read the relevant guide under `node_modules/next/dist/docs/` before writing frontend code; do not assume training-data Next.js conventions. The dashboard talks to the backend over `NEXT_PUBLIC_*` URLs and the `/ws` + `/api/v1/ws/chat` WebSockets.

### Graphify (codebase knowledge graph in `graphify-out/`)
For codebase questions prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, `graphify explain "<concept>"` over raw grep — they return a scoped subgraph. Read `graphify-out/GRAPH_REPORT.md` only for broad architecture. After changing code, run `graphify update .` (AST-only, no API cost).

## Run modes — the single most important thing to understand

Behavior is controlled by **`BAND_MOCK`** (default `"true"`) and by which LLM keys are present. There are two orthogonal switches:

1. **Transport: mock bus vs real Band** (`core/band_client.py`, `is_mock_mode()`)
   - `BAND_MOCK=true` → agents register with an in-process `MockBandBus` singleton. Messages route between rooms by an in-memory `ROOM_MAPPING` (+ fuzzy match). No network. This is what the demo and tests use.
   - `BAND_MOCK=false` → agents connect to `wss://app.thenvoi.com` via the thenvoi SDK using credentials from `agent_config.yaml` (falls back to `agent_config.example.yaml`). Requires `python scripts/setup_band_rooms.py` first.

2. **Reasoning: real LLM vs deterministic local engine** (`core/base_agent.py`)
   - If a provider key is set (`GOOGLE_API_KEY` / `GROQ_API_KEY` / `FEATHERLESS_API_KEY` / `AIMLAPI_KEY`), agents reason with that LLM via LangGraph `create_react_agent`, wrapped in `ResilientChatModel` (retries 429s, then falls back).
   - With no key — or after a fatal provider error trips the **process-wide degradation window** (`degrade_llm()` / `llm_degraded()`, default 15 min via `ARGUS_LLM_COOLDOWN`) — agents fall back to a **local LLM pointed at this server's own `/mock-llm` endpoint** (`api/main.py::mock_llm_completions`). That endpoint is a deterministic OpenAI-compatible fake that scripts the entire boardroom handoff and emits real, evidence-backed reports.

**Key consequence:** the actual numbers, red flags, scores, and verdict are computed deterministically by `core/diligence_engine.py::run_diligence_calculations()`, fed from `core/pitch_loader.py`. The mock-LLM server and the chat fallbacks in `api/v1.py` both call it. The LLM (when present) mostly drives narration/tone and the agent-to-agent handoff choreography — it does **not** invent the verdict. When changing scoring, weights, red-flag logic, or the verdict card, edit `diligence_engine.py`, not the agent prompts.

## Architecture

### Agent layer (`agents/` + `core/base_agent.py`)
Every partner subclasses `BaseAgent(name, display_name, room, system_prompt, tools, model_name)`. `BaseAgent` prepends a shared `ARGUS_DOCTRINE` + appends a `MEMORY_PROTOCOL_PROMPT`, wires up the LLM (`_setup_llm`), and compiles a LangGraph react agent. In mock mode it registers on `mock_bus` and `handle_mock_message()` runs the executor when mentioned; in real mode `ArgusLangGraphAdapter.on_message` gates on @-mention before the SDK runs the agent. Re-entrancy is guarded by `_is_busy`. The 5 partners and their rooms:

| Agent | File | Room |
|---|---|---|
| Managing Partner (orchestrator) | `agents/managing_partner.py` | `managing-partner-room` |
| Financial Partner | `agents/financial_partner.py` | `finance-partner-room` |
| Legal Partner | `agents/legal_partner.py` | `legal-partner-room` |
| Technical Partner | `agents/technical_partner.py` | `tech-partner-room` |
| Market Partner | `agents/market_partner.py` | `market-partner-room` |

**Flow:** a deal trigger sends a brief to `managing-partner-room` → Managing Partner @-mentions all 4 specialists in parallel → each loads its pitch section via `load_deal_brief(...)`, runs diligence, and reports `"... ANALYSIS COMPLETE"` back to `managing-partner-room` → once all 4 are in, Managing Partner emits the final decision card (contains `DECISION:`). Weights: Financial 30%, Legal 25%, Technical 25%, Market 20%; score 1–4 INVEST, 5–6 CONDITIONAL, 7–10 PASS.

### Core engine (`core/`)
- `diligence_engine.py` — deterministic scoring/verdict, scenario analysis, auto-generated VC questions, citations/grounding, contradiction & gap detection. The source of truth for all numbers.
- `pitch_loader.py` — loads the active pitch JSON from `data/` and exposes the `load_deal_brief`, `get_company_name`, `get_red_flags` agent tools. Resolves the active pitch from `sim_state.active_pitch_file` or `pitch_{incident_id}.json`, defaulting to `novapay_pitch.json`.
- `llm_router.py` — async multi-provider router with a fallback chain (`ARGUS_LLM_PRIMARY` first, then the rest). Used by the **chat/persona** endpoints in `api/v1.py` (distinct from the LangGraph LLM the agents use).
- `memory_graph.py` — shared cross-deal memory ("incidents"/deals, timelines, learned risk patterns, persisted chat history). Backed by JSON under `fusion_memory/` (legacy `argus_memory/` also present).
- `event_bus.py` — in-process pub/sub; agents `broadcast(agent, status, data)` and FastAPI forwards every event to dashboard WebSockets.
- `base_agent.py` — base class, `ResilientChatModel`, LLM degradation window, mock Band tools, memory tools.

### API layer (`api/`)
- `main.py` — app factory, CORS, the `/ws` dashboard socket, ops endpoints (`/api/trigger-deal`, `/api/trigger-attack` compat alias, `/api/status`, `/api/reset`), and the deterministic **`/mock-llm/chat/completions`** server. Registers `broadcast_event_to_websockets` on the event bus; auto-releases the run lock when the Managing Partner emits `DECISION:` or any agent emits `alert`.
- `v1.py` — product-facing `/api/v1/*`: Managing Partner chat (`/chat`, `/ws/chat`) with deterministic intent routing + persona replies, deal/incident memory queries, file/PDF pitch upload, system settings & MCP registry. Falls back from real LLM → deterministic engine.
- `state.py` — `sim_state` singleton: the run lock (`running`), per-agent status, active deal/pitch, dispatched-deal set, and `is_stale()` (90s watchdog so a dead chain can't wedge the lock forever).

### Frontend (`frontend/`)
Next.js pages-router dashboard. `pages/index.tsx` is the war room; `hooks/useAgentWebSocket.ts` consumes the event stream; components render agent cards/graph, the live log, chat, and the executive verdict panel. Styling is Tailwind v4 (`@tailwindcss/postcss`) + framer-motion + lucide-react.

### MCP (`mcp_server.py`)
Exposes the committee to external MCP clients (Claude Desktop, etc.) as 5 tools (`chat_with_managing_partner`, `get_deal_record`, `get_boardroom_verdict`, `query_deal_vault`, `learn_risk_pattern`) that proxy to the running REST API at `FUSION_API_URL` (default `http://localhost:8000`).

### Demo deal — NovaPay Inc (`data/novapay_pitch.json`)
Fake Series A fintech with planted red flags the committee is expected to surface: 78% ARR from one Amazon client (contract expiring), Klarna ~$8M patent lawsuit, EOL Node 14 / MongoDB + plaintext PII / no pentest, BNPL sector declining ~12% YoY vs a 200% growth claim, and a founder SEC history. `snaphire`/`snapscore` is a second supported demo company (see the regex extractor in `api/v1.py`).

## Conventions & gotchas
- **Async everywhere** — network/IO is non-blocking; agents and the event bus are coroutine-driven.
- **Env vars are `ARGUS_`-prefixed** despite the FUSION rename: `ARGUS_LLM_PRIMARY`, `ARGUS_MOCK_PACE` (mock-LLM pacing, default 0.6), `ARGUS_LLM_COOLDOWN`, `ARGUS_<PROVIDER>_MODEL`. Copy `.env.example` → `.env`.
- **Room names are exact strings** matched/fuzzed in `core/band_client.py::ROOM_MAPPING`; add new agents there and to `run.py`.
- **The run lock** (`sim_state.running`) prevents concurrent committee sessions — clears on verdict, on `alert`, or via the staleness watchdog / `/api/reset`.
- When verifying behavior end-to-end, run mock mode (`BAND_MOCK=true`, no keys needed) and hit `POST /api/trigger-deal`, then watch `/ws`.

## Deployment
`Procfile` / `railway.json` / `render.yaml` all run `python run.py`. Railway healthcheck is `/api/status`. Render presets `BAND_MOCK=true` and expects provider keys as unsynced secrets. See `FUSION_MEMORY.md` for current deploy targets/state.
