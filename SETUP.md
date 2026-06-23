# FUSION — Full Setup Guide

> Step-by-step instructions to set up and run the FUSION Swarm Investment Committee locally.

---

## Prerequisites

| Tool | Version | Install Link |
|------|---------|--------------|
| **Python** | 3.11+ | [python.org](https://python.org) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) |
| **Git** | Any | [git-scm.com](https://git-scm.com) |
| **uv** (Optional) | Latest | `pip install uv` (faster dependency installer) |
| **Band Account** | — | [band.ai](https://band.ai) |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/baljotchohan/fusion.git
cd fusion
```

---

## Step 2 — Set Up Python Environment

Using `uv` (recommended):
```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# Install dependencies
uv pip install -r requirements.txt
```

Using standard `pip`:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3 — Environment Variables

Copy the template:
```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```bash
# Primary LLM Provider Key (Gemini)
GOOGLE_API_KEY=your-gemini-api-key-here

# Fallback LLM Provider Keys (Optional)
GROQ_API_KEY=your-groq-key-here
FEATHERLESS_API_KEY=your-featherless-key-here
AIMLAPI_KEY=your-aimlapi-key-here

# Band SDK (Default is "true" for mock mode, change to "false" to connect to real Band platform)
BAND_MOCK=true
BAND_API_KEY=your-band-developer-key-here
```

Get your Gemini API key at: **aistudio.google.com** (free tier available).

---

## Step 4 — Configure Band Agents

```bash
cp agent_config.example.yaml agent_config.yaml
```

To run FUSION in **Real Mode** (connecting to the real `band.ai` rooms):
1. Go to your **band.ai** dashboard -> Developer Settings.
2. Create 5 external agents (one for each partner):
   - `managing-partner`
   - `financial-partner`
   - `legal-partner`
   - `technical-partner`
   - `market-partner`
3. Copy each agent's `agent_id` and `api_key` into `agent_config.yaml`.
4. Set `BAND_MOCK=false` in your `.env`.

*(If `BAND_MOCK=true`, you can skip this step — the system will run locally on an in-memory message bus).*

---

## Step 5 — Set Up Band Rooms (Real Mode Only)

If you are running in Real Mode, run the room setup script to automatically create the rooms on the Band platform:

```bash
python scripts/setup_band_rooms.py
```

This creates the following rooms:
- `managing-partner-room`
- `finance-partner-room`
- `legal-partner-room`
- `tech-partner-room`
- `market-partner-room`

---

## Step 6 — Run the Backend

```bash
python run.py
```

This launches:
- The **FastAPI Gateway** on `http://localhost:8000`.
- The **5 partner agents** listening to their respective rooms.
- The **Local Mock LLM Server** (which runs if no cloud LLM API keys are provided).

---

## Step 7 — Run the Frontend Dashboard

Open a new terminal window:

```bash
cd frontend

# Install Next.js dependencies
npm install

# Run the Next.js development server
npm run dev
```

Open your browser and navigate to **`http://localhost:3000`** to view the live FUSION boardroom dashboard!

---

## Step 8 — Test & Verify

1. **Trigger Diligence**: Click the **Simulate NovaPay** button on the frontend, or send a mock POST request:
   ```bash
   curl -X POST "http://localhost:8000/api/trigger-deal?company=NovaPay%20Inc"
   ```
2. **Watch the Boardroom**: The WebSocket connection will stream live events to the dashboard. You will see the Managing Partner convene the room, brief the specialists, and run the debate.
3. **Upload Pitches**: Drag and drop a pitch document (PDF, JSON, TXT, MD) to run diligence on custom companies.
4. **Download Report**: Once the verdict is delivered, click **Download PDF Report** to export the branded investment memo.

---

*FUSION — Five agents. One boardroom. No bad investments.*
