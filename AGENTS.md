# FUSION — Agent Documentation

> Detailed specifications for all 5 partner agents in the FUSION Swarm Investment Committee boardroom.

---

## Agent Architecture

Every partner in FUSION follows a standardized multi-agent boardroom pattern:

```
External Trigger / upload-pitch or trigger-deal
         ↓
FastAPI backend receives command
         ↓
Managing Partner briefs partners in Band rooms
         ↓
LangGraph react agent activates for each partner
         ↓
Node 1: Load pitch data room section (load_deal_brief)
Node 2: Retrieve red flags (get_red_flags)
Node 3: Fetch deterministic calculations (get_calculated_scores)
Node 4: Audit for missing information (NEEDS_MORE_DILIGENCE check)
Node 5: Analyze and compile domain report
         ↓
thenvoi_send_message → @mention Managing Partner with domain report
         ↓
FastAPI event_bus → stream events to boardroom UI (WebSockets)
```

All partners extend `BaseAgent` and connect to the Band AI Platform (or `MockBandBus` in local dev mode).

---

## Agent 1 — Managing Partner (IC Chair) 💼

**Band Room:** `managing-partner-room`  
**LLM:** GPT-4o / Gemini 2.0 Flash (Primary)  
**Trigger:** Triggered when a new pitch is uploaded or a simulation is started via `@managing-partner` or `/api/trigger-deal`.

### What It Does
As the Investment Committee Chair, the Managing Partner orchestrates the entire swarm. It convenes the committee, briefs all 4 specialist partners simultaneously, collects their completed diligence reports, runs the boardroom debate round to resolve conflicts, and delivers the final `INVEST` / `PASS` / `CONDITIONAL` / `NEEDS_MORE_DILIGENCE` decision.

### Tools
- `load_deal_brief(section)` — Load company metadata or overview
- `get_company_name()` — Retrieve company name
- `get_red_flags()` — Fetch key issues
- `get_calculated_scores()` — Fetch deterministic weighted risk scores and verdict confidence from the engine

### LangGraph Nodes
```
convene_committee → brief_partners → await_findings → resolve_debates → synthesize_verdict → publish_decision
```

### Output Format
The Managing Partner's final message MUST contain the literal token `DECISION:` and a `WEIGHTED SCORE:` line:
```markdown
---
INVESTMENT COMMITTEE VERDICT — NovaPay Inc
Chair: Managing Partner

DECISION: PASS
WEIGHTED SCORE: 9.3/10
VERDICT CONFIDENCE: 91%

SUMMARY:
NovaPay presents unacceptable tail-risk due to a combination of severe customer concentration (78% ARR from Amazon expiring in 3 months) and an active patent infringement lawsuit seeking $8M in damages, which represents 80% of the current raise. 

BOARDROOM DEBATE RESOLUTION:
Financial Partner flags the high revenue growth, but Market Partner notes BNPL sector headwinds (-12% YoY). Legal Partner's highlight of the $8M Klarna lawsuit combined with Technical Partner's audit showing plaintext SSN storage and EOL Node 14 runtimes confirms that the risk outweighs the growth potential.

RECOMMENDED STEPS:
1. Issue formal PASS letter to founders.
2. Archive due diligence logs to memory graph.
---
```

### Band Coordination
- **Briefs:** `@baljotchohan23/financial-partner`, `@baljotchohan23/legal-partner`, `@baljotchohan23/technical-partner`, and `@baljotchohan23/market-partner` simultaneously.
- **Collects:** Awaits reports containing `"ANALYSIS COMPLETE"` in `managing-partner-room`.

---

## Agent 2 — Financial Partner 📊

**Band Room:** `finance-partner-room`  
**LLM:** GPT-4o-mini / Gemini 2.0 Flash  
**Trigger:** `@mention` from Managing Partner.

### What It Does
Acts as a forensic accountant and VC financial analyst. Investigates revenue model quality (e.g., customer concentration), burn rate sustainability, runway post-raise, unit economics (LTV:CAC, payback periods), and valuation multiples.

### Tools
- `load_deal_brief('financials')` — Load data room financials section
- `load_deal_brief('company')` — Load general company facts
- `get_calculated_scores()` — Retrieve mathematically calculated risk scores (e.g., `financial_risk_score`)

### Output Format
```markdown
---
FINANCIAL DUE DILIGENCE REPORT — NovaPay Inc
Partner: Financial Analysis
Confidence: HIGH

REVENUE QUALITY:
- 78% ARR concentration with a single customer (Amazon). Contract expires in 3 months.
- Stated 200% YoY growth is highly vulnerable to contract non-renewal.

BURN & RUNWAY:
- Stated runway is 8 months based on current monthly burn of $500k and cash reserves.
- Post-raise runway is projected to be 18 months, assuming head-count growth is capped.

UNIT ECONOMICS:
- LTV:CAC is 2.5x, which falls short of our Series A hurdle rate of 3.0x.
- Customer payback period is 14 months.

VALUATION:
- Valuation multiple stands at 16x ARR, which is highly expensive for a company with severe customer concentration cliff-risk.

🚨 CRITICAL RED FLAGS:
1. 78% customer concentration with Amazon expiring in 90 days.
2. LTV:CAC of 2.5x is sub-standard.
3. High valuation multiple relative to concentration risk.

FINANCIAL RISK SCORE: 9.0/10
RECOMMENDATION: PASS
---
```

### Band Coordination
Sends report to: **@managing-partner** in `managing-partner-room` via `@mention`.

---

## Agent 3 — Legal Partner ⚖️

**Band Room:** `legal-partner-room`  
**LLM:** GPT-4o-mini / Gemini 2.0 Flash  
**Trigger:** `@mention` from Managing Partner.

### What It Does
Acts as a corporate M&A attorney. Audits litigation exposure, regulatory compliance (CFPB, licensing, SEC), IP status (provisional vs granted patents), and founder backgrounds.

### Tools
- `load_deal_brief('legal')` — Load data room legal and compliance section
- `load_deal_brief('team')` — Load reference checks and team backgrounds
- `get_calculated_scores()` — Retrieve mathematically calculated risk scores (e.g., `legal_risk_score`)

### Output Format
```markdown
---
LEGAL DUE DILIGENCE REPORT — NovaPay Inc
Partner: Legal Analysis
Confidence: HIGH

LITIGATION EXPOSURE:
- Active patent infringement lawsuit from Klarna seeking $8M in damages. This represents 80% of the proposed $10M raise and poses an existential capital depletion risk.

REGULATORY COMPLIANCE:
- Lacks state lending licenses in 4 key operating jurisdictions.
- Non-compliant with latest CFPB BNPL disclosure guidelines.

IP STATUS:
- Core transaction routing algorithm is only covered by provisional patents; no utility patent granted.

FOUNDER BACKGROUND:
- Lead founder was subject to an SEC investigation in 2022 (no charges filed, but settled administrative inquiry).

🚨 CRITICAL LEGAL RED FLAGS:
1. Klarna patent dispute seeking $8M (80% of raise).
2. Operating unlicensed in 4 states.
3. Founder history of SEC inquiries.

LEGAL RISK SCORE: 9.5/10
RECOMMENDATION: PASS
BLOCKING ISSUES: Resolve Klarna litigation; acquire state lending licenses.
---
```

### Band Coordination
Sends report to: **@managing-partner** in `managing-partner-room` via `@mention`.

---

## Agent 4 — Technical Partner 🔧

**Band Room:** `tech-partner-room`  
**LLM:** GPT-4o-mini / Gemini 2.0 Flash  
**Trigger:** `@mention` from Managing Partner.

### What It Does
Audits the technical architecture and security posture. Evaluates tech stack EOL runtimes, security practices (PCI-DSS compliance, penetration testing, data storage), scalability bottlenecks, and code/IP leakage risks.

### Tools
- `load_deal_brief('technical')` — Load data room technical architecture details
- `get_calculated_scores()` — Retrieve mathematically calculated risk scores (e.g., `technical_risk_score`)

### Output Format
```markdown
---
TECHNICAL DUE DILIGENCE REPORT — NovaPay Inc
Partner: Technical Analysis
Confidence: HIGH

TECH STACK VIABILITY:
- Core routing engine runs on Node.js 14, which reached End-of-Life (EOL) in 2023. Represents significant security and technical debt.

SECURITY POSTURE:
- Plaintext storage of SSNs and credit card numbers detected in MongoDB databases.
- Lacks PCI-DSS compliance certification.
- No independent penetration testing conducted in the last 18 months.

SCALABILITY:
- Single-region database deployment with no hot failover. Significant availability risk.

🚨 CRITICAL TECHNICAL RED FLAGS:
1. Plaintext storage of sensitive PII (SSNs).
2. End-of-Life Node.js 14 runtime in production.
3. Lack of PCI-DSS compliance and failover infrastructure.

TECHNICAL RISK SCORE: 8.5/10
RECOMMENDATION: PASS
---
```

### Band Coordination
Sends report to: **@managing-partner** in `managing-partner-room` via `@mention`.

---

## Agent 5 — Market Partner 📈

**Band Room:** `market-partner-room`  
**LLM:** GPT-4o-mini / Gemini 2.0 Flash  
**Trigger:** `@mention` from Managing Partner.

### What It Does
Audits market claims, competitive positioning, and industry tailwinds. Validates TAM claims, assesses competitor strengths, and evaluates market-timing headwinds.

### Tools
- `load_deal_brief('market')` — Load market size and competitor sections
- `get_calculated_scores()` — Retrieve mathematically calculated risk scores (e.g., `market_risk_score`)

### Output Format
```markdown
---
MARKET DUE DILIGENCE REPORT — NovaPay Inc
Partner: Market Analysis
Confidence: HIGH

TAM VALIDATION:
- Stated TAM of $50B is overstated by including total global payments instead of regional BNPL consumer transactions (True TAM is closer to $6B).

COMPETITIVE LANDSCAPE:
- Faces severe headwinds from scale incumbents (Affirm, Klarna, Block/Afterpay) offering aggressive merchant discounts.

SECTOR TIMING:
- BNPL sector transaction volumes are declining 12% YoY. VC funding in the sector is down 67% YoY.

🚨 CRITICAL MARKET RED FLAGS:
1. Overstated TAM by 8.3x.
2. Strong incumbent market dominance leaving little space for Series A entrant.
3. Sector transaction volumes in a multi-year downward trend.

MARKET RISK SCORE: 8.0/10
RECOMMENDATION: PASS
---
```

### Band Coordination
Sends report to: **@managing-partner** in `managing-partner-room` via `@mention`.

---

*FUSION — Five agents. One boardroom. No bad investments.*
