# ARGUS — Full Setup Guide

> Step-by-step setup from zero to running ARGUS locally.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | Any | [git-scm.com](https://git-scm.com) |
| uv | Latest | `pip install uv` |
| Band Account | — | [band.ai](https://band.ai) |

---

## Step 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/argus.git
cd argus
```

---

## Step 2 — Python environment

```bash
# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# Install all dependencies
uv pip install -r requirements.txt
```

---

## Step 3 — Environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```bash
# LLM Keys
GOOGLE_API_KEY=your-gemini-api-key-here
FEATHERLESS_API_KEY=your-featherless-key-here

# Band (add on June 12 at hackathon kickoff)
# BAND_API_KEY=will-be-provided-at-kickoff

# App Config
FASTAPI_PORT=8000
FRONTEND_PORT=3000
LOG_LEVEL=INFO
```

Get your Gemini API key at: **aistudio.google.com** (free)

---

## Step 4 — Band agent credentials

```bash
cp agent_config.example.yaml agent_config.yaml
```

After getting your Band API key on June 12:
1. Go to **band.ai** → Developer Settings
2. Create 9 agents (one per ARGUS agent)
3. Copy each agent's `agent_id` and `api_key` into `agent_config.yaml`

---

## Step 5 — Download MITRE ATT&CK data

```bash
python scripts/download_mitre.py
```

This downloads the MITRE ATT&CK Enterprise JSON (~50MB) to `/data/enterprise-attack.json`. Takes about 1 minute. Only needs to be done once.

Alternatively, download manually:
- Go to: **github.com/mitre-attack/attack-stix-data**
- Download: `enterprise-attack/enterprise-attack.json`
- Save to: `data/enterprise-attack.json`

---

## Step 6 — Set up Band rooms (June 12+)

```bash
python scripts/setup_band_rooms.py
```

This creates all 9 Band rooms automatically:
- `threat-intel-room`
- `recon-room`
- `redteam-room`
- `attack-path-room`
- `detection-room`
- `malware-room`
- `blueteam-room`
- `incident-command-room`
- `executive-room`

---

## Step 7 — Frontend setup

```bash
cd frontend
npm install
cd ..
```

---

## Step 8 — Run ARGUS

```bash
# Option A: Run everything at once
python run.py

# Option B: Run separately (for debugging)
# Terminal 1 — Backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Agents
python agents/run_all.py

# Terminal 3 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Step 9 — Test the demo

1. Open the War Room dashboard at `http://localhost:3000`
2. Confirm all 9 agent status cards show **IDLE** (green dot)
3. Click **SIMULATE ATTACK**
4. Watch the phishing attack trigger all 9 agents in sequence
5. Final CEO decision should appear in the Executive panel within 2-3 minutes

---

## Pre-hackathon mode (before June 12)

Before you have a Band API key, run in **mock mode**:

```bash
BAND_MOCK=true python run.py
```

Mock mode simulates Band room coordination locally using an in-memory message bus. All 9 agents still run their full LangGraph logic — they just don't connect to real Band rooms. On June 12, remove `BAND_MOCK=true` and add your real Band API key.

---

## Troubleshooting

**Agents not activating:**
- Check `agent_config.yaml` has correct agent IDs and API keys
- Verify Band WebSocket connection: look for `Connected to Band — agent: [name]` in logs

**MITRE lookup returns empty:**
- Run `python scripts/download_mitre.py` again
- Check `data/enterprise-attack.json` exists and is >40MB

**Gemini API errors:**
- Verify `GOOGLE_API_KEY` in `.env`
- Check free tier rate limits (15 req/min) — if exceeded, fallback to Featherless kicks in

**Dashboard not loading:**
- Confirm FastAPI is running on port 8000
- Check CORS settings in `api/main.py`
- Verify Next.js is on port 3000

**React Flow graph not animating:**
- Check WebSocket connection to `ws://localhost:8000/ws`
- Browser console → Network tab → look for WS connection

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `FEATHERLESS_API_KEY` | Yes (June 12+) | Featherless AI key from hackathon |
| `BAND_API_KEY` | Yes (June 12+) | Band API key from hackathon kickoff |
| `BAND_MOCK` | No | Set `true` for local testing without Band |
| `FASTAPI_PORT` | No | Default: 8000 |
| `LOG_LEVEL` | No | Default: INFO |

---

## Requirements

See `requirements.txt` for full list. Key packages:

```
band-sdk[langgraph]
langchain-google-genai
langchain-openai
langgraph
fastapi
uvicorn
aiohttp
python-dotenv
pyyaml
```

---

*ARGUS — 9 agents. All seeing. Never sleeps.*
