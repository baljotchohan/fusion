# ⚖️ VERDICT — AI-Powered Venture Capital Investment Committee

> *"VC-grade due diligence in under 5 minutes. Five expert agents debate. One verdict."*

**Band of Agents Hackathon | June 2026 | Track: Regulated & High-Stakes Workflows**

---

## The Problem

Every year, billions of dollars are lost on bad acquisitions and failed startup investments.

The reason isn't a lack of smart people. It's a coordination failure.

When a VC firm evaluates a startup, they need:
- A **financial analyst** to stress-test the revenue model
- A **corporate lawyer** to check for lawsuits, IP risk, and regulatory violations
- A **technical expert** to audit the product and security posture
- A **market researcher** to validate the market size claim and competitive landscape
- A **committee chair** to synthesize all findings into a final decision

This process takes **weeks to months**, costs **$100,000–$500,000** in professional fees, and still fails. Companies like WeWork, Theranos, and FTX all passed human due diligence before catastrophic collapse.

The root cause: **specialists work in silos**. The lawyer doesn't talk to the engineer. The financial analyst doesn't know about the pending patent lawsuit. The market researcher doesn't see the cap table. Nobody reconciles conflicts until it's too late.

---

## The Solution: VERDICT

**VERDICT** is an AI Investment Committee — five specialized AI partner agents that independently investigate every domain of a startup pitch, then **debate their findings in real time through Band**, and deliver a final investment decision with a confidence score.

From pitch submission to committee verdict: **under 5 minutes**.

```
Founder submits pitch deck
           ↓
   Managing Partner convenes committee
           ↓
┌──────────────────────────────────────────────────────┐
│  PARALLEL INVESTIGATION (all 4 partners work at once) │
│                                                        │
│  Financial Partner   Legal Partner   Tech Partner      │
│  ─────────────────   ────────────   ────────────       │
│  Revenue quality     Lawsuits        Stack health      │
│  Burn rate           IP status       Security          │
│  Unit economics      Compliance      Scalability       │
│  Valuation math      Cap table       Tech debt         │
│                                                        │
│              Market Partner                            │
│              ────────────                              │
│              TAM validation                            │
│              Competition                               │
│              Sector timing                             │
└──────────────────────────────────────────────────────┘
           ↓
   Managing Partner collects all findings
           ↓
   COMMITTEE DEBATE (agents flag conflicts)
           ↓
╔══════════════════════════════════════════╗
║   DECISION:    PASS                      ║
║   CONFIDENCE:  91%                       ║
║   WEIGHTED RISK SCORE: 8.1 / 10          ║
╚══════════════════════════════════════════╝
```

---

## Why This Wins the Hackathon

### Perfect Band of Agents Fit

The hackathon challenge is **"Build a Band, not a soloist."**

VERDICT is not one agent. It's not a wrapper. It's a genuine multi-agent committee where:
- Each agent has **its own Band room** and exclusive domain authority
- Agents **cannot see each other's rooms** — findings are truly independent
- The Managing Partner uses `@mentions` to brief specialists and collect reports
- Conflicts between partners are **explicitly debated** before the final decision

This is exactly what the judges are scoring: real coordination, clear task handoffs, shared context through Band.

### Judges Will Remember This One

When judges have reviewed 30 projects, most will be security dashboards, HR bots, and code review agents. VERDICT shows them **an AI boardroom arguing about a $10M investment decision**. That's memorable.

More importantly — every judge at a tech hackathon either works with VCs, has pitched VCs, or has invested in startups. They **personally feel this problem**. Nothing else in the room will hit them that personally.

### The Debate Is the Product

Most multi-agent projects collect outputs from agents and concatenate them. VERDICT shows agents **disagreeing**:

> *"Financial Partner: Revenue growth is excellent — 200% YoY."*  
> *"Market Partner: BNPL sector is declining 12% YoY in the US. That growth contradicts sector reality."*  
> *"Managing Partner: Market Partner's concern outweighs the revenue headline. We're buying a growing company in a shrinking market."*

That visible reasoning is what separates this from everything else.

---

## The 5 Partner Agents

### 1. Managing Partner — `managing-partner-room`
**File:** `agents/managing_partner.py`

The investment committee chair. Does not perform analysis — **orchestrates** the committee.

**What it does:**
- Receives the deal brief and convenes all 4 specialist partners simultaneously
- Sends `@mentions` to each partner room with the pitch brief
- Waits for all 4 reports to arrive
- Identifies conflicts between partner findings
- Applies a weighted risk scoring model (Financial 30%, Legal 25%, Technical 25%, Market 20%)
- Delivers the final `INVEST / PASS / CONDITIONAL` decision with confidence percentage
- Generates the formal investment committee memo

**Verdict format it produces:**
```
╔══════════════════════════════════════════════════════════╗
║         VERDICT INVESTMENT COMMITTEE DECISION            ║
╠══════════════════════════════════════════════════════════╣
║ Company:    NovaPay Inc                                  ║
║ Deal:       $10M Series A at $40M post-money             ║
║ Date:       June 12, 2026                                ║
╠══════════════════════════════════════════════════════════╣
║  DECISION:    PASS                                       ║
║  CONFIDENCE:  91%                                        ║
╚══════════════════════════════════════════════════════════╝
```

---

### 2. Financial Partner — `finance-partner-room`
**File:** `agents/financial_partner.py`

Acts as a forensic accountant. Stress-tests every financial claim in the pitch.

**What it investigates:**
- Revenue concentration (any single customer >40% ARR is a red flag)
- Contract expiry dates — does revenue survive the close date?
- Burn rate vs runway — is there enough runway for the growth plan?
- Unit economics: LTV:CAC must exceed 3x for a credible Series A thesis
- Valuation multiple: is the asking price fair for the sector and stage?
- Gross margin health: <50% is a concern for SaaS/fintech
- YoY growth claim — does the customer breakdown actually support it?

**Red flags it will find in NovaPay:**

| Finding | Severity |
|---------|----------|
| 78% of ARR from single Amazon client | 🔴 CRITICAL |
| Amazon contract expires 3 months post-close | 🔴 CRITICAL |
| Only 8 months runway at current burn | 🟠 HIGH |
| LTV:CAC of 2.5x (below 3x Series A benchmark) | 🟡 MEDIUM |
| Valuation at 8x ARR in a declining sector | 🟡 MEDIUM |

**Risk Score Output:** `9/10`  
**Recommendation:** `PASS`

---

### 3. Legal Partner — `legal-partner-room`
**File:** `agents/legal_partner.py`

Acts as a corporate M&A attorney. Finds legal landmines before money moves.

**What it investigates:**
- Active litigation: damages exposure vs raise amount
- IP portfolio status: provisional ≠ granted patents
- Regulatory compliance: licenses, CFPB rules, state-by-state requirements
- Data privacy: SOC2, CCPA, GDPR exposure
- Cap table cleanliness: anti-dilution ratchets, unusual terms
- Founder background: prior SEC/DOJ scrutiny, failed startup history
- Contract risks: customer agreements, vendor dependencies

**Red flags it will find in NovaPay:**

| Finding | Severity |
|---------|----------|
| Klarna patent lawsuit — $8M potential damages (80% of raise) | 🔴 CRITICAL |
| CFPB non-compliance (rules effective Jan 2026) | 🔴 CRITICAL |
| Operating without money transmitter licenses in 4 states | 🔴 CRITICAL |
| CEO's prior startup under SEC investigation (case closed) | 🟠 HIGH |
| No SOC2 certification — blocks enterprise sales | 🟠 HIGH |
| CCPA compliance unverified | 🟡 MEDIUM |

**Risk Score Output:** `10/10`  
**Recommendation:** `PASS` — Klarna lawsuit alone is a dealbreaker

---

### 4. Technical Partner — `tech-partner-room`
**File:** `agents/technical_partner.py`

Acts as a CTO-level auditor. Assesses whether the product can actually scale — and whether it will blow up post-investment.

**What it investigates:**
- Tech stack currency: EOL runtimes = unpatched CVEs in production
- PCI-DSS compliance: mandatory for any company processing payments
- Security posture: pentest history, PII encryption, MFA enforcement
- Architecture scalability: monolith vs cloud-native, load testing limits
- Tech debt: contractor-written code with no documentation = bus factor risk
- Undisclosed security incidents
- Remediation cost to bring the product to enterprise grade

**Red flags it will find in NovaPay:**

| Finding | Severity |
|---------|----------|
| Node.js 14 (EOL Oct 2023) — unpatched in a payment processor | 🔴 CRITICAL |
| PII and SSNs stored in plaintext MongoDB | 🔴 CRITICAL |
| No PCI-DSS compliance (cannot legally process payments at scale) | 🔴 CRITICAL |
| Never had a penetration test | 🔴 CRITICAL |
| Undisclosed 2024 data breach (3,200 records) — not reported | 🔴 CRITICAL |
| No MFA for admin accounts | 🟠 HIGH |
| Monolithic architecture — no horizontal scaling beyond 10k users | 🟡 MEDIUM |

**Remediation Cost Estimate:** $800k–$1.4M (85–140% of the engineering allocation)  
**Risk Score Output:** `10/10`  
**Recommendation:** `PASS` — security profile is pre-catastrophe

---

### 5. Market Partner — `market-partner-room`
**File:** `agents/market_partner.py`

Acts as a market research director. Validates or disproves the market thesis.

**What it investigates:**
- TAM claim: bottom-up vs top-down validation
- Actual sector growth vs company's growth claim
- Competitive landscape: can this company survive against funded incumbents?
- Sector timing: is VC conviction in this space growing or dying?
- Regulatory headwinds: is the regulatory environment helping or hurting?
- Defensibility: network effects, data moat, switching costs, brand

**Red flags it will find in NovaPay:**

| Finding | Severity |
|---------|----------|
| US BNPL sector declining 12% YoY — contradicts 200% growth claim | 🔴 CRITICAL |
| VC funding into BNPL down 67% YoY — terrible sector timing | 🔴 CRITICAL |
| Competing vs Klarna ($6.7B), Affirm ($8B), Block ($29B acquisition) | 🔴 CRITICAL |
| CFPB credit reporting mandate (Q3 2026) projected to cut BNPL usage 15-25% | 🟠 HIGH |
| Defensibility score: 8/25 — no moat | 🟠 HIGH |

**Risk Score Output:** `8/10`  
**Recommendation:** `PASS` — sector headwinds kill the growth story

---

## The Demo Company: NovaPay Inc

**A fake startup built specifically for the demo. Every problem is intentional.**

### Surface Level (What They Pitch)
- **Industry:** Fintech / Buy Now Pay Later (BNPL)
- **Stage:** Series A
- **Raise:** $10M at $40M post-money valuation
- **ARR:** $5M (claims 200% YoY growth)
- **Users:** 50,000
- **NPS:** 72
- **Team:** Stanford MBA CEO, ex-Stripe CTO, 23 employees
- **Pitch:** "AI-powered credit scoring that reduces defaults by 40%"

**On paper: looks solid.**

### What the Agents Find
Under the surface, NovaPay has **12 hidden problems** across 5 domains:

```
📊 FINANCIAL (4 problems)
  ├── 78% revenue from single Amazon client
  ├── Amazon contract expires 3 months post-close
  ├── Only 8 months runway ($380k/month burn)
  └── LTV:CAC = 2.5x (below 3x Series A benchmark)

⚖️ LEGAL (4 problems)  
  ├── Klarna patent lawsuit — $8M potential damages
  ├── CFPB non-compliance since January 2026
  ├── Money transmitter unlicensed in 4 states
  └── CEO's prior startup under SEC investigation

🔧 TECHNICAL (4 problems)
  ├── Node.js 14 + MongoDB 4.2 (both End-of-Life)
  ├── PII + SSNs stored in plaintext
  ├── Never had a penetration test
  └── Undisclosed 2024 data breach (3,200 records)

📈 MARKET (3 problems)
  ├── BNPL sector declining 12% YoY (contradicts 200% growth)
  ├── VC funding into BNPL down 67% YoY
  └── CFPB mandate will reduce BNPL usage 15-25% by Q3 2026

👥 TEAM (2 problems)
  ├── No General Counsel (active lawsuit with no legal lead)
  └── First-time CFO with no scale experience
```

### What the Committee Concludes

```
╔══════════════════════════════════════════════════════════╗
║         VERDICT INVESTMENT COMMITTEE DECISION            ║
╠══════════════════════════════════════════════════════════╣
║ Company:    NovaPay Inc                                  ║
║ Deal:       $10,000,000 Series A at $40,000,000 post     ║
╠══════════════════════════════════════════════════════════╣
║  DECISION:    PASS                                       ║
║  CONFIDENCE:  91%                                        ║
╚══════════════════════════════════════════════════════════╝

RISK SCORECARD:
  Financial Risk:  9/10  (weight: 30%) → 2.70
  Legal Risk:     10/10  (weight: 25%) → 2.50
  Technical Risk: 10/10  (weight: 25%) → 2.50
  Market Risk:     8/10  (weight: 20%) → 1.60
  ─────────────────────────────────────────────
  WEIGHTED SCORE:  9.3/10

PRIMARY REASONS:
1. Klarna patent lawsuit ($8M potential damages = 80% of raise) is an
   existential risk that must be resolved before any capital is deployed.
2. Amazon client concentration (78% ARR) with contract expiry 3 months
   post-close creates a cliff-edge revenue scenario.
3. Security posture (no PCI-DSS, plaintext PII, no pentest, undisclosed
   breach) is pre-catastrophe for a licensed payments processor.
```

---

## Technical Architecture

### Stack
| Layer | Technology |
|-------|-----------|
| Agent Coordination | Band SDK (`thenvoi`) — real WebSocket rooms |
| Agent Framework | LangGraph (ReAct agents) |
| Primary LLM | Google Gemini 2.0 Flash |
| Fallback LLM | Groq (llama-3.3-70b) → Featherless AI |
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Frontend | Next.js 14 + React + Tailwind CSS |
| Real-time | WebSockets (FastAPI → Next.js dashboard) |
| Mock Mode | In-process `MockBandBus` (no API keys needed) |

### Band Room Architecture

```
                    ┌─────────────────────────┐
   Deal Intake ──▶  │  managing-partner-room   │
                    │  Managing Partner Agent  │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
   ┌──────────────────┐  ┌───────────────┐  ┌──────────────────┐
   │ finance-partner  │  │ legal-partner │  │  tech-partner    │
   │      -room       │  │     -room     │  │      -room       │
   │ Financial Partner│  │ Legal Partner │  │ Technical Partner│
   └─────────┬────────┘  └──────┬────────┘  └────────┬─────────┘
             │                  │                     │
             └──────────────────┼─────────────────────┘
                                │ (all report back)
             ┌──────────────────┼─────────────────────┐
             ▼                                         ▼
   ┌──────────────────┐               ┌─────────────────────────┐
   │  market-partner  │               │   managing-partner-room  │
   │      -room       │──────────────▶│   Synthesis + Verdict   │
   │  Market Partner  │               └─────────────────────────┘
   └──────────────────┘
```

### How Messages Flow (Mock Mode)

```
1. POST /api/trigger-deal  →  MockBandBus
2. MockBandBus → managing-partner-room
3. Managing Partner wakes up, calls load_deal_brief()
4. Managing Partner sends @mentions to all 4 partner rooms simultaneously
5. Each partner wakes up, loads their pitch section, produces report
6. Each partner sends findings to managing-partner-room via @mention
7. Managing Partner receives all 4 reports, synthesizes, delivers verdict
8. Event bus broadcasts each step to Next.js dashboard via WebSocket
```

---

## Project File Structure

```
fusion/  (project folder — VERDICT lives here)
│
├── VERDICT.md              ← This file
├── CLAUDE.md               ← Agent/AI coding guide
├── run.py                  ← Entry point: starts FastAPI + 5 agents
├── .env                    ← API keys + BAND_MOCK setting
│
├── agents/                 ← The 5 VERDICT partner agents
│   ├── managing_partner.py ← Chair — orchestrates + delivers verdict
│   ├── financial_partner.py← Forensic financial analysis
│   ├── legal_partner.py    ← Litigation, IP, regulatory risk
│   ├── technical_partner.py← Tech stack, security, scalability
│   └── market_partner.py   ← Market size, competition, timing
│
├── core/                   ← Shared infrastructure (FUSION core)
│   ├── base_agent.py       ← LangGraph agent base + Band client
│   ├── band_client.py      ← Band SDK wrapper (real + mock bus)
│   ├── pitch_loader.py     ← Tool: loads pitch sections for agents
│   ├── llm_router.py       ← Multi-provider LLM with auto-fallback
│   ├── event_bus.py        ← FastAPI WebSocket event bridge
│   └── memory_graph.py     ← Shared deal memory (cross-session learning)
│
├── data/
│   └── novapay_pitch.json  ← Demo startup: 12 hidden problems
│
├── api/
│   ├── main.py             ← FastAPI app + /api/trigger-deal endpoint
│   └── v1.py               ← Chat, status, memory endpoints
│
└── frontend/               ← Next.js Boardroom Dashboard
    ├── pages/index.tsx
    └── components/
```

---

## API Endpoints

### Trigger a Deal Review
```bash
POST /api/trigger-deal?company=NovaPay%20Inc&raise_amount=%2410M
```

Kicks off the committee. Managing Partner is briefed and immediately sends `@mentions` to all 4 specialist rooms.

### Check System Status
```bash
GET /api/status
```
Returns registered Band rooms, agents online, active deal ID.

### Reset Between Runs
```bash
POST /api/reset
```
Clears state. Run this between demo runs.

### Chat with the Committee Chair
```bash
POST /api/v1/chat
{"user_message": "What did the Legal Partner find?"}
```

### WebSocket (dashboard live feed)
```
ws://localhost:8000/ws
```
Streams every agent event to the Next.js dashboard in real time.

---

## Running VERDICT

### 1. Environment Setup
```bash
cd ~/Desktop/fusion
cp .env.example .env
# Add your GOOGLE_API_KEY or GROQ_API_KEY
# Set BAND_MOCK=true for local demo
```

### 2. Install Dependencies
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start the Committee
```bash
python run.py
```

Expected output:
```
⚖️  Initializing VERDICT Investment Committee...
  ✓ Managing Partner  — managing-partner-room
  ✓ Financial Partner — finance-partner-room
  ✓ Legal Partner     — legal-partner-room
  ✓ Technical Partner — tech-partner-room
  ✓ Market Partner    — market-partner-room
INFO: Started server process
INFO: Application startup complete.
```

### 4. Run the Demo
```bash
# Trigger NovaPay analysis
curl -X POST "http://localhost:8000/api/trigger-deal"

# Watch the verdict arrive in real time on the dashboard
open http://localhost:3000
```

### 5. Environment Variables
| Variable | Value | Purpose |
|---|---|---|
| `BAND_MOCK` | `true` | Run offline (no Band API key needed) |
| `GOOGLE_API_KEY` | your key | Gemini 2.0 Flash (primary LLM) |
| `GROQ_API_KEY` | your key | Groq fallback LLM |
| `FEATHERLESS_API_KEY` | `BOA26` code | Featherless partner LLM |
| `PORT` | `8000` | FastAPI server port |

---

## Judging Criteria Alignment

### 1. Application of Technology ✅
Band is the **actual coordination layer** — not a wrapper.
- Managing Partner uses real `@mentions` to brief specialists
- Each agent lives in its own dedicated Band room
- No agent sees another agent's room unless explicitly mentioned
- The entire committee debate happens through Band message handoffs

### 2. Business Value ✅
M&A due diligence is a **$15B+ professional services market**.
- Current process: weeks, $100k–$500k, still fails
- VERDICT: 5 minutes, autonomous, no professional fees
- The problem is universally understood — every judge has encountered it

### 3. Presentation ✅
The demo arc is self-explanatory to any audience:
1. Upload pitch → committee convenes (15 seconds)
2. Watch 4 agents investigate in parallel (90 seconds)
3. See agent debate surface conflicts (60 seconds)
4. Final verdict delivered with confidence score (30 seconds)

Total: under 5 minutes. Fits the submission requirement exactly.

### 4. Originality ✅
- **Agent debate mechanic**: partners flag conflicts, chair resolves them
- **Weighted confidence scoring**: not binary — quantified uncertainty
- **Sector timing analysis**: agents challenge the pitch's own market claims
- **Undisclosed risk surfacing**: agents find things the founder didn't mention
- Nobody at this hackathon is building an AI VC committee

---

## Hackathon Submission Checklist

- [ ] All 5 agents running in Band real mode (`BAND_MOCK=false`)
- [ ] `scripts/setup_band_rooms.py` run → 5 rooms created in Band dashboard
- [ ] End-to-end NovaPay demo recorded (≤5 min video)
- [ ] GitHub repository public with working demo instructions
- [ ] Product description written for lablab.ai submission
- [ ] Presentation deck: problem → solution → demo → team

**Promo codes to activate before demo:**
- Band Pro: `BANDHACK26` (1 month free)
- Featherless AI: `BOA26` ($25 credits, 1000 open-source models)

**Submission deadline: June 19, 2026 via lablab.ai**

---

## Why VERDICT Beats an AI SOC

| Dimension | AI SOC (ARGUS) | AI VC Committee (VERDICT) |
|-----------|---------------|--------------------------|
| Judge relatability | Needs security background | Universal — everyone understands investing |
| Demo memorability | Security dashboard #17 | AI boardroom debates $10M investment |
| Agent debate visibility | Sequential pipeline | Explicit disagreement and resolution |
| Business stakes | Response time saved | $10M investment decision |
| Hackathon uniqueness | Common category | Rare — nobody builds this |
| Band fit | Strong | Perfect — partners = rooms = debate |

---

## The One-Line Pitch

> *"We uploaded a startup's pitch deck. Our AI investment committee found the Klarna lawsuit, the Amazon client concentration cliff, and the plaintext SSN storage — in 4 minutes. Human due diligence missed all three."*

---

*VERDICT — Five agents. One boardroom. No bad investments.*
