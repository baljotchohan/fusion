# FUSION — Complete Project Reference (All-in-One)

> **PURPOSE:** Feed this ENTIRE document to any AI (ChatGPT, Gemini, etc.) and ask it to create a presentation. This file contains EVERYTHING about FUSION — no other context needed.

---

## INSTRUCTION TO THE AI CREATING THE PRESENTATION

Create a professional presentation (12-15 slides) for FUSION, an AI-Powered Venture Capital Investment Committee. Use the content below as the single source of truth. The presentation is for the **Band of Agents Hackathon** (lablab.ai, June 12-19, 2026, Track: Regulated and High-Stakes Workflows, Team: Agent Core). Make it visually compelling with a dark boardroom aesthetic, FUSION brand green (#4fae47), and clean data visualizations.

---

## SLIDE STRUCTURE SUGGESTION

1. Title Slide - FUSION AI-Powered Venture Capital Investment Committee
2. The Problem - Why VC due diligence is broken
3. The Solution - What FUSION does (30-second pitch)
4. How It Works - The 5-agent workflow diagram
5. The 5 Partners - Agent roles + Band rooms
6. The Demo - NovaPay Inc pitch + what agents find
7. The Verdict - Committee decision + risk scorecard
8. Agent Debate - How agents disagree and resolve conflicts
9. Architecture - Tech stack + system diagram
10. Key Features - MCP Server, PDF Generator, Real-time Dashboard, Memory Graph
11. Band AI Integration - How Band is the coordination layer
12. Hackathon Criteria Alignment - Why this wins
13. Business Vision - Post-hackathon SaaS potential
14. Team - Agent Core
15. Thank You / Demo Link

---

# 1. WHAT IS FUSION?

FUSION is an AI-powered Investment Committee consisting of a swarm of 5 specialized AI partner agents that autonomously audit startup pitch decks, conduct real-time inter-agent debates, and deliver a final INVEST / PASS / CONDITIONAL verdict with a weighted risk scorecard, all in under 5 minutes.

Tagline: "Five agents. One boardroom. No bad investments."

Each agent acts as a domain-expert VC partner (Financial, Legal, Technical, Market) coordinated by a Managing Partner (the committee chair). All agents communicate through the Band AI multi-agent coordination platform using @mentions in dedicated Band rooms.

---

# 2. THE PROBLEM

## VC Due Diligence Is Fundamentally Broken

Every year, billions of dollars are lost on bad startup investments.

The root cause is not a lack of smart people. It is a coordination failure.

When a VC firm evaluates a startup, they need:
- A financial analyst to stress-test the revenue model
- A corporate lawyer to check for lawsuits, IP risk, and regulatory violations
- A technical expert to audit the product and security posture
- A market researcher to validate the market size and competitive landscape
- A committee chair to synthesize all findings into a final decision

### The Pain Points

| Problem | Reality |
|---|---|
| Time | Due diligence takes weeks to months |
| Cost | Professional fees range from $100,000 to $500,000 per deal |
| Failure Rate | WeWork, Theranos, and FTX all passed human due diligence before catastrophic collapse |
| Silo Problem | The lawyer does not talk to the engineer. The financial analyst does not know about the pending lawsuit. Nobody reconciles conflicts until it is too late |
| Market Size | M&A due diligence is a $15B+ professional services market |

---

# 3. THE SOLUTION

FUSION deploys 5 specialist AI partner agents that:

1. Investigate independently - Each partner conducts a deep-dive audit in their own domain (financials, legal, technical, market)
2. Coordinate in real-time - Partners communicate via Band AI platform using @mentions, sharing findings and flagging conflicts
3. Debate findings - When partners disagree (e.g., Revenue looks great vs The sector is declining), the Managing Partner resolves the conflict through structured debate
4. Deliver a unified verdict - A single, weighted risk scorecard with an INVEST/PASS/CONDITIONAL decision and confidence percentage

### The Flow

```
Startup Pitch Uploaded (JSON/PDF)
        |
Managing Partner convenes committee
        |
4 Partners investigate in PARALLEL
  Financial  Legal  Technical  Market
        |
Partners report findings -> Conflicts surface
        |
Managing Partner runs Committee Debate
        |
  DECISION:    PASS
  CONFIDENCE:  91%
  RISK SCORE:  9.3 / 10
        |
Publication-grade PDF Report generated
```

---

# 4. THE 5 INVESTMENT PARTNER AGENTS

## Agent 1: Managing Partner (Chair / Orchestrator)
- Band Room: managing-partner-room
- @mention: @managing-partner
- Role: Committee Chair. Does NOT perform analysis. Orchestrates the committee, convenes all 4 partners, collects findings, runs the debate round, resolves conflicts, calculates the weighted risk score, and delivers the final INVEST / PASS / CONDITIONAL decision.
- Persona: 20 years as a GP at top-tier VC funds, led investments in 3 unicorns, returned 8x DPI to LPs.
- Weight: Chair (no score, aggregates others)
- Tools: load_deal_brief, get_company_name, get_red_flags, get_calculated_scores
- LLM: Gemini 2.0 Flash

### Verdict Format It Produces:
```
FUSION INVESTMENT COMMITTEE DECISION
Company:      NovaPay Inc
Deal:         $10M Series A at $40M post-money
DECISION:    PASS
CONFIDENCE:  91%

RISK SCORECARD:
  Financial Risk:  9/10  (weight: 30%) = 2.70
  Legal Risk:     10/10  (weight: 25%) = 2.50
  Technical Risk: 10/10  (weight: 25%) = 2.50
  Market Risk:     8/10  (weight: 20%) = 1.60
  WEIGHTED SCORE:  9.3/10
```

---

## Agent 2: Financial Partner
- Band Room: finance-partner-room
- @mention: @financial-partner
- Role: Forensic accountant. Stress-tests every financial claim in the pitch.
- Persona: 15 years of experience in forensic accounting, killed 40+ deals by uncovering financial red flags.
- Weight: 30%
- What It Investigates:
  - Revenue concentration (any single customer >40% ARR is a red flag)
  - Contract expiry dates vs fundraise timeline
  - Burn rate vs runway (must extend 18+ months post-raise)
  - Unit economics (LTV:CAC must be >3x for Series A)
  - Valuation multiple fairness (ARR multiple vs sector)
  - Gross margin health (<50% is concerning for SaaS/fintech)
- Tools: load_deal_brief, get_red_flags
- LLM: Gemini 2.0 Flash

---

## Agent 3: Legal Partner
- Band Room: legal-partner-room
- @mention: @legal-partner
- Role: Corporate M&A attorney. Finds legal landmines before money moves.
- Persona: Former M&A attorney at Sullivan and Cromwell, 18 years experience, blocked investments that later faced DOJ/SEC enforcement.
- Weight: 25%
- What It Investigates:
  - Active litigation: damages exposure vs raise amount
  - IP portfolio: provisional vs granted patents
  - Regulatory compliance: CFPB, state money transmitter licenses
  - Data privacy: SOC2, CCPA, GDPR
  - Cap table cleanliness
  - Founder background: prior SEC/DOJ scrutiny
- Tools: load_deal_brief, get_red_flags
- LLM: Gemini 2.0 Flash

---

## Agent 4: Technical Partner
- Band Room: tech-partner-room
- @mention: @technical-partner
- Role: CTO-level auditor. Assesses whether the product can scale and will not blow up post-investment.
- Persona: Ex-CTO of two fintech unicorns, deep expertise in payment infrastructure and security.
- Weight: 25%
- What It Investigates:
  - Tech stack currency (EOL runtimes = unpatched CVEs)
  - PCI-DSS compliance (mandatory for payment processors)
  - Security posture: pentest history, PII encryption, MFA
  - Architecture scalability
  - Tech debt and bus factor risk
  - Remediation cost estimates
- Tools: load_deal_brief, get_red_flags
- LLM: Gemini 2.0 Flash

---

## Agent 5: Market Partner
- Band Room: market-partner-room
- @mention: @market-partner
- Role: Market research director. Validates or disproves market claims.
- Persona: Former head of research at a16z, encyclopedic knowledge of market sizing and competitive dynamics.
- Weight: 20%
- What It Investigates:
  - TAM claim credibility (bottom-up vs top-down)
  - Actual sector growth vs company growth claims
  - Competitive landscape: can this survive against funded incumbents?
  - Sector timing: is VC conviction growing or dying?
  - Regulatory tailwinds vs headwinds
  - Defensibility scoring (data moat, network effects, switching costs, brand, technology, each scored 1-5, total /25)
- Tools: load_deal_brief, get_red_flags
- LLM: Gemini 2.0 Flash

---

# 5. WEIGHTED RISK SCORING SYSTEM

Each specialist partner produces a risk score from 1-10 (1=no risk, 10=dealbreaker). The Managing Partner aggregates these using fixed weights:

| Domain | Weight | Score Range |
|--------|--------|-------------|
| Financial | 30% | 1-10 |
| Legal | 25% | 1-10 |
| Technical | 25% | 1-10 |
| Market | 20% | 1-10 |

Verdict Thresholds:
- Score 1-4: INVEST
- Score 5-6: CONDITIONAL (invest with conditions)
- Score 7-10: PASS (do not invest)

Confidence Calibration:
- 90-100%: Near-certain. Hard evidence, no ambiguity.
- 70-89%: High. Strong evidence, one unknown.
- 50-69%: Moderate. Mixed signals.
- Below 50%: PASS regardless, uncertainty itself is the risk.

---

# 6. THE DEMO: NovaPay Inc

## What NovaPay Pitches (Surface Level, Looks Great)

| Metric | Value |
|--------|-------|
| Industry | Fintech / Buy Now Pay Later (BNPL) |
| Stage | Series A |
| Raise | $10,000,000 |
| Post-Money Valuation | $40,000,000 |
| ARR | $5,000,000 |
| YoY Growth | 200% |
| Users | 50,000 |
| NPS | 72 |
| CEO | Marcus Chen, Stanford MBA |
| CTO | Sarah Okafor, MIT CS, ex-Stripe |
| Employees | 23 |
| USP | AI-powered credit scoring, 40% lower default rate |

On paper: looks like a solid Series A deal.

---

## What the Agents Actually Find: 12+ Hidden Problems

### Financial Red Flags (4 problems)
| Finding | Severity |
|---------|----------|
| 78% of ARR from single Amazon client, extreme dependency | CRITICAL |
| Amazon contract expires Sept 30, 2026, only 3 months post-close | CRITICAL |
| Only 8 months runway at $380k/month burn | HIGH |
| LTV:CAC of 2.5x, below 3x Series A benchmark | MEDIUM |

### Legal Red Flags (4 problems)
| Finding | Severity |
|---------|----------|
| Klarna patent lawsuit: $8M potential damages = 80% of entire raise | CRITICAL |
| CFPB non-compliance since January 2026 | CRITICAL |
| Operating without money transmitter licenses in 4 states | CRITICAL |
| CEO prior startup under SEC investigation (case closed, caution letter issued) | HIGH |

### Technical Red Flags (5 problems)
| Finding | Severity |
|---------|----------|
| Node.js 14 (EOL Oct 2023), unpatched in a payment processor | CRITICAL |
| PII and SSNs stored in plaintext MongoDB | CRITICAL |
| No PCI-DSS, cannot legally process payments at scale | CRITICAL |
| Never had a penetration test, unknown attack surface | CRITICAL |
| Undisclosed 2024 data breach (3,200 records), not reported to regulators | CRITICAL |

### Market Red Flags (3 problems)
| Finding | Severity |
|---------|----------|
| US BNPL sector declining 12% YoY, contradicts 200% growth claim | CRITICAL |
| VC funding into BNPL down 67% YoY, terrible sector timing | CRITICAL |
| Competing vs Klarna ($6.7B), Affirm ($8B), Block ($29B) | CRITICAL |

### Team Gaps (2 problems)
- No General Counsel (active lawsuit with no legal lead)
- First-time CFO with no scale experience

---

## The Final Verdict

```
FUSION INVESTMENT COMMITTEE DECISION
Company:    NovaPay Inc
Deal:       $10,000,000 Series A at $40,000,000 post-money
DECISION:    PASS
CONFIDENCE:  91%

RISK SCORECARD:
  Financial Risk:   9/10  (weight: 30%) = 2.70
  Legal Risk:      10/10  (weight: 25%) = 2.50
  Technical Risk:  10/10  (weight: 25%) = 2.50
  Market Risk:      8/10  (weight: 20%) = 1.60
  WEIGHTED SCORE:  9.3/10

PRIMARY REASONS FOR PASS:
1. Klarna patent lawsuit ($8M potential damages = 80% of raise)
   is an existential risk that must be resolved before capital is deployed.
2. Amazon client concentration (78% ARR) with contract expiry 3 months
   post-close creates a cliff-edge revenue scenario.
3. Security posture (no PCI-DSS, plaintext PII, no pentest, undisclosed
   breach) is pre-catastrophe for a payments processor.
```

---

# 7. THE AGENT DEBATE (Key Differentiator)

Most multi-agent projects collect outputs and concatenate them. FUSION shows agents disagreeing and the chair resolving:

Financial Partner: "Revenue growth is excellent, 200% YoY. Gross margin at 62% is healthy."

Market Partner: "BNPL sector is declining 12% YoY in the US. That 200% growth contradicts sector reality. And VC funding into BNPL is down 67%."

Managing Partner: "Market Partner's concern outweighs the revenue headline. We are buying a growing company in a shrinking market. The 200% growth is concentrated in a single Amazon contract that expires 3 months after close. This is not organic growth, it is a dependency masquerading as traction."

This visible reasoning and conflict resolution is what separates FUSION from everything else at the hackathon.

---

# 8. TECHNOLOGY STACK

| Layer | Technology |
|-------|-----------|
| Agent Coordination | Band SDK (thenvoi), real WebSocket rooms with @mention routing |
| Agent Framework | LangGraph (ReAct agents with tool-calling) |
| Primary LLM | Google Gemini 2.0 Flash |
| Fallback LLMs | Groq (llama-3.3-70b) then Featherless AI (Mistral-Small-24B) then AI/ML API |
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Frontend | Next.js 14 + React + Tailwind CSS |
| Real-time | WebSockets (FastAPI to Next.js dashboard) |
| Memory | Graphify-backed shared deal memory (JSON graph) |
| PDF Generator | ReportLab (institutional-grade reports) |
| MCP Server | Model Context Protocol (stdio + streamable-HTTP) |
| Connectors | GitHub Repository Security Scanner |
| File Parsing | pypdf (PDF), UTF-8 (TXT/MD), json.loads (JSON) |
| Deploy Backend | Hugging Face Spaces (Docker) |
| Deploy Frontend | Vercel |

---

# 9. ARCHITECTURE DIAGRAM

```
FUSION Platform
 _________________________________________________________________
|                                                                 |
|  Web UI (Next.js)  <---->  REST API (FastAPI :8000)             |
|  - Boardroom log           /api/v1/*                            |
|  - Risk Gauge              WebSockets                           |
|  - PDF Download                                                 |
|                        Event Bus (async)                        |
|                             |                                   |
|   Band SDK    <---  5 Partner Swarm (LangGraph)                 |
|   WebSocket         Managing / Financial / Legal                |
|   @mentions         Technical / Market Partner                  |
|                        |         |          |                   |
|               Shared Memory   LLM Router   Connectors           |
|               Graph           Gemini /     GitHub               |
|               (Graphify)      Groq /       ReportLab            |
|                               Featherless  (PDF)                |
|                                                                 |
|  MCP Server: external AI apps use the partner swarm             |
|  chat_with_managing_partner / get_deal_record / etc.            |
|_________________________________________________________________|
```

### Band Room Architecture (How Messages Flow)

```
                    managing-partner-room
                    Managing Partner Agent
                           |
          @mentions all 4 partners simultaneously
              |                |               |
   finance-partner    legal-partner     tech-partner
        -room              -room             -room
   Financial Partner  Legal Partner    Technical Partner
              |                |               |
              +---------+------+-------+-------+
                        |  all report back via @mention
              +---------+------+-------+-------+
              |                                |
   market-partner               managing-partner-room
        -room         -------> Synthesis + Verdict
   Market Partner
```

### Message Flow (Step by Step)
1. POST /api/trigger-deal -> Event Bus -> Managing Partner Room
2. Managing Partner wakes up, calls load_deal_brief('company')
3. Managing Partner sends @mentions to all 4 partner rooms simultaneously
4. Each partner wakes up, loads their pitch section, produces independent report
5. Each partner sends findings to managing-partner-room via @managing-partner
6. Managing Partner receives all 4 reports
7. Managing Partner identifies conflicts, runs debate
8. Managing Partner calculates weighted risk score, delivers verdict
9. Event Bus broadcasts each step to Next.js dashboard via WebSocket

---

# 10. KEY FEATURES

## 10.1 Real-time Boardroom Dashboard
Dynamic war-room UI built in Next.js showing:
- WebSocket-streamed live logs of every agent action
- Audit timeline with timestamps
- Live agent status cards (idle/working/done)
- Risk gauge visualization
- Agent node graph (React Flow)

Frontend Components:
- AgentCard.tsx: Status cards for each partner
- AgentGraph.tsx: React Flow node visualization of the swarm
- AgentDetailPanel.tsx: Detailed agent findings view
- LiveLog.tsx: Real-time WebSocket log stream
- ExecutivePanel.tsx: Verdict display
- DemoDeals.tsx: Pre-loaded demo companies
- MemoryView.tsx: Deal history and learned patterns
- SettingsView.tsx: Configuration panel
- PartnersView.tsx: Partner overview
- DocsView.tsx: Documentation panel
- IntegrationsView.tsx: MCP and integrations panel

## 10.2 Weighted Risk Engine
- Aggregates partner risk scores (1-10) into a single weighted score
- Automatic diligence overrides for fatal flaws
- Evidence quality scoring
- Coverage assessment (which domains were fully investigated)
- Deal readiness metrics

## 10.3 Publication-Grade PDF Reports
The ReportLab engine produces institutional-grade diligence reports:
- Cover Page: Company metadata + color-coded Verdict Badge (Emerald Green for INVEST, Orange for CONDITIONAL, Crimson Red for PASS)
- Structured Scorecards: Risk score grids with weighted distribution
- Debate Timeline: Partner findings compiled into clean timestamped cards
- Brand colors: FUSION Green (#4fae47)

## 10.4 Model Context Protocol (MCP) Server
Exposes the entire investment committee as 5 tools for external AI clients:
- chat_with_managing_partner(message): Triggers the full committee
- get_deal_record(incident_id): Retrieve a past deal from shared memory
- get_boardroom_verdict(incident_id): Get the committee verdict
- query_deal_vault(keyword): Search similar past deals
- learn_risk_pattern(keyword, checklist): Teach the committee a new pattern

Two transport modes:
- Remote URL: http://localhost:8000/mcp (streamable-HTTP, no install needed)
- Local stdio: python mcp_server.py (for Claude Desktop / Claude Code)

## 10.5 GitHub Repository Security Scanner
Real connector that clones startup codebases and audits:
- Exposed secrets (via GitHub Secret Scanning API)
- Dependabot vulnerability alerts (severity, CVEs)
- Dependency manifests (package.json, requirements.txt, Gemfile, go.mod)
- EOL runtime detection

## 10.6 Shared Memory Graph (Cross-Session Learning)
Graphify-backed persistent memory (fusion_memory/ directory):
- incidents.json: All past deals with per-partner finding timelines
- attack_patterns.json: Learned checklists per risk category
- agent_profiles.json: Per-partner learning stats
- chat_history.json: Full conversation log

Agents query past deals before acting, so the team gets measurably faster on repeat evaluations.

## 10.7 Multi-Provider LLM Router with Auto-Fallback
If the primary LLM (Gemini) fails due to rate limits or outage, automatically falls back:
Gemini 2.0 Flash -> Groq (llama-3.3-70b) -> Featherless AI (Mistral-Small-24B) -> AI/ML API
The pipeline never crashes, resilient by design.

## 10.8 Pitch Upload and Processing
- Supports JSON, PDF (via pypdf), and Markdown/TXT uploads
- Automatic section extraction: financials, legal, technical, market, team
- Uploaded pitches stored as pitch_DEAL-{timestamp}.json
- Pitch cache with invalidation on re-upload

## 10.9 Interactive @mention Chat System
Users can chat directly with any partner:
Example: @financial-partner what is the biggest red flag you found?
Backend parses the @mention, routes to the correct partner agent with its persona, memory, and pitch data. Partners respond in-character, creating visible chain reactions in the UI.

---

# 11. PROJECT FILE STRUCTURE

```
fusion/
  run.py                        Entry point: starts FastAPI + 5 agents
  .env                          API keys + BAND_MOCK setting
  requirements.txt              Python dependencies
  Dockerfile                    Docker configuration (Hugging Face Spaces)
  agent_config.yaml             5 agent IDs + API keys + room names
  mcp_server.py                 MCP stdio transport
  mcp_tools.py                  MCP tool definitions (shared)

  agents/                       The 5 FUSION partner agents
    managing_partner.py          Chair: orchestrates + verdict
    financial_partner.py         Forensic financial analysis
    legal_partner.py             Litigation, IP, regulatory
    technical_partner.py         Tech stack, security
    market_partner.py            Market size, competition

  core/                         Shared engine and utilities
    base_agent.py                LangGraph agent base + Band client
    band_client.py               Band SDK wrapper (real + mock bus)
    pitch_loader.py              Loads pitch sections for agents
    llm_router.py                Multi-provider LLM with fallback
    event_bus.py                 WebSocket event bridge to frontend
    memory_graph.py              Shared deal memory (Graphify)
    diligence_engine.py          Mathematical risk scoring engine
    pdf_generator.py             ReportLab PDF report builder
    demo_registry.py             Demo company registry

  connectors/
    github_scanner.py            Real GitHub API security scanner

  api/                          FastAPI backend
    main.py                      FastAPI app, trigger, WebSocket, MCP
    v1.py                        All REST endpoints (chat, upload, report)
    state.py                     Simulation state management

  data/                         Pitch data files
    novapay_pitch.json           Primary demo company (12 problems)
    cadence_pitch.json           Additional demo company
    gridflow_pitch.json          Additional demo company
    helios_pitch.json            Additional demo company
    medivault_pitch.json         Additional demo company
    clearlend_pitch.md           Additional demo company
    pitch_DEAL-*.json            User-uploaded pitch files

  fusion_memory/                Persistent shared memory
    incidents.json
    attack_patterns.json
    agent_profiles.json
    chat_history.json

  scripts/
    setup_band_rooms.py          Creates 5 Band rooms

  frontend/                     Next.js Boardroom Dashboard
    pages/index.tsx              Main boardroom UI
    components/
      AgentCard.tsx
      AgentDetailPanel.tsx
      AgentGraph.tsx
      DemoDeals.tsx
      DocsView.tsx
      ExecutivePanel.tsx
      IntegrationsView.tsx
      LiveLog.tsx
      Logo.tsx
      MemoryView.tsx
      PartnersView.tsx
      SettingsView.tsx
      Wordmark.tsx
```

---

# 12. API ENDPOINTS

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/trigger-deal | Trigger a full committee review |
| GET | /api/status | System status (agents, rooms, active deal) |
| POST | /api/reset | Clear state between demo runs |
| POST | /api/v1/chat | Chat with the Managing Partner |
| POST | /api/v1/upload-pitch | Upload a pitch (JSON/PDF/MD/TXT) |
| POST | /api/v1/generate-report | Generate PDF diligence report |
| GET | /api/v1/system/mcp | Discover MCP tools |
| WS | /ws | WebSocket real-time dashboard feed |
| ALL | /mcp | MCP streamable-HTTP endpoint |

---

# 13. BAND AI INTEGRATION (Why This Is Core, Not A Wrapper)

Band is the actual coordination substrate, not a thin wrapper:

- Each agent has its own dedicated Band room
- Agents cannot see each other's rooms, findings are truly independent
- The Managing Partner uses real @mentions to brief specialists and collect reports
- Conflicts between partners are explicitly debated before the final decision
- Agent-to-agent handoffs are visible in the Band dashboard
- thenvoi_send_message and thenvoi_send_event used throughout

Band Platform Tools Used:
- thenvoi_send_message: @mention routing between rooms
- thenvoi_send_event: Progress reporting to dashboard
- thenvoi_add_participant: Dynamic agent recruitment
- thenvoi_lookup_peers: Agent discovery
- thenvoi_create_chatroom: Room management

---

# 14. HACKATHON CONTEXT

| Detail | Value |
|--------|-------|
| Hackathon | Band of Agents Hackathon |
| Platform | lablab.ai |
| Dates | June 12-19, 2026 |
| Track | Regulated and High-Stakes Workflows |
| Team Name | Agent Core |
| Prize Pool | $10,000+ (1st: $3,500 / 2nd: $2,500 / 3rd: $1,500) |
| Partner Prizes | Best Use of AI/ML API ($1k cash + $1k credits), Best Use of Featherless AI |
| Band SDK Sponsor | Band (thenvoi), $17M seed from Sierra Ventures, Hetz Ventures, Team8 |

### Judging Criteria Alignment:

| Criterion | How FUSION Delivers |
|-----------|-------------------|
| Application of Technology | Band is the ACTUAL coordination layer, not a wrapper. Each agent has its own room, real @mentions, visible handoffs. |
| Business Value | M&A due diligence is a $15B+ market. FUSION does in 5 minutes what costs $100K to $500K today. |
| Presentation | Self-explanatory demo: upload pitch, agents investigate, debate, verdict. Under 5 minutes. |
| Originality | Agent debate mechanic (partners disagree and chair resolves), weighted confidence scoring, undisclosed risk surfacing. |

---

# 15. WHY FUSION WINS

### Competitive Edge Over Other Hackathon Projects

| Dimension | Most Projects | FUSION |
|-----------|--------------|--------|
| Agent count | 1-2 agents | 5 specialized partners |
| Coordination | Sequential pipeline | Parallel investigation + debate |
| Band usage | Final notification | Core coordination layer |
| Output | Text analysis | Weighted verdict + PDF report |
| Memorability | Security dashboard #17 | AI boardroom debates $10M investment |
| Business stakes | Time saved | $10M investment decision |
| Audience relatability | Needs domain knowledge | Everyone understands investing |

The Debate Is The Product:
When judges have reviewed 30 projects (mostly security dashboards, HR bots, code review agents), FUSION shows them an AI boardroom arguing about a $10M investment decision. That is memorable. Every judge at a tech hackathon has personally experienced VC due diligence. They feel this problem.

---

# 16. BUSINESS VISION (Post-Hackathon)

Product: FUSION SaaS, AI investment committee in a box.

### Target Customers:
- Seed/Series A VC firms: $50-200k/yr for autonomous first-pass screening
- Corporate M&A teams: replaces $300k due diligence engagements
- Angel syndicates: institutional-grade DD for individuals
- Investment banks: augment analyst workflow

### Pricing:
- Free: NovaPay demo only
- Pro: Custom uploads, 10 deals/month
- Enterprise: Unlimited + MCP server + API access

### Growth Path:
lablab NEXT accelerator, then build-in-public (GitHub stars, X threads), then VC/M&A accelerators, then YC (AI agents in regulated finance = on-thesis)

---

# 17. TEAM: AGENT CORE

Baljot Singh Chohan - Lead Developer
- 2nd year BCA student, Punjab, India
- AI builder + AI journalist
- Built: Python backend, FastAPI, Band SDK integration, LangGraph agents, memory system, MCP server, Hugging Face Spaces deployment
- Other projects: Lirox (local Python AI research agent), Antigravity (lifestyle brand)

Teammate - Frontend Developer
- Next.js, React, Tailwind CSS boardroom UI, Vercel deployment

---

# 18. KEY METRICS SUMMARY

| Metric | Value |
|--------|-------|
| Agents | 5 specialist partners |
| Time to Verdict | Under 5 minutes |
| Traditional Cost | $100K to $500K |
| FUSION Cost | Near zero (API costs) |
| Market Size | $15B+ due diligence market |
| Risk Dimensions | 4 weighted domains |
| Demo Red Flags Found | 12+ hidden problems |
| Demo Verdict | PASS at 91% confidence |
| LLM Providers | 4 with auto-fallback |
| Frontend Components | 13 React components |
| API Endpoints | 8+ REST + WebSocket + MCP |
| Demo Companies | 5+ pre-loaded |
| Memory Persistence | Cross-session learning |

---

# 19. THE ONE-LINE PITCH

"We uploaded a startup's pitch deck. Our AI investment committee found the Klarna lawsuit, the Amazon client concentration cliff, and the plaintext SSN storage, in 4 minutes. Human due diligence missed all three."

---

# 20. DEPLOYMENT

### Backend (Hugging Face Spaces)
Deploy FUSION as a Docker Space on Hugging Face:
1. Create a Space on Hugging Face with **Docker** SDK (Dockerfile is automatically detected).
2. Set environment variables (`GOOGLE_API_KEY`, `AIMLAPI_KEY`, etc.) in the Space Settings tab.
3. Push to Hugging Face Space remote:
```bash
git remote add hf https://huggingface.co/spaces/baljot07/fusion
git push hf main
```
URL: `https://baljot07-fusion.hf.space`

### Frontend (Vercel)
```bash
cd frontend
vercel --prod
# In Vercel dashboard:
# Set NEXT_PUBLIC_API_URL=https://baljot07-fusion.hf.space
# Set NEXT_PUBLIC_WS_URL=wss://baljot07-fusion.hf.space/ws
```

---

FUSION: Five agents. One boardroom. No bad investments.

Built for the Band of Agents Hackathon, June 2026, Team Agent Core
