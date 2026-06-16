# ClearLend Technologies — Series A Investment Pitch Brief
> Prepared for: Investor Due Diligence
> Date: May 2026
> Raise: $12,000,000 | Post-Money Valuation: $48,000,000
> Round Type: Series A (Priced Equity)

---

## 1. COMPANY OVERVIEW

**Legal Name:** ClearLend Technologies, Inc.
**Incorporated:** Delaware C-Corp, March 2021
**Headquarters:** 400 Market Street, Suite 900, San Francisco, CA 94105
**Satellite Office:** Bengaluru, India (engineering team, 14 staff)
**Website:** clearlend.io
**LinkedIn:** linkedin.com/company/clearlend-technologies

**Tagline:** *"Credit decisions in 11 seconds. Default rates that make banks jealous."*

**One-liner:** ClearLend is an AI-powered alternative lending API platform that enables mid-market SaaS companies and e-commerce platforms to embed instant credit decisioning for their SMB customers, replacing traditional 10–14 day bank loan processes with sub-15-second underwriting decisions using 2,400+ alternative data signals.

---

## 2. FOUNDERS & TEAM

### Co-Founder & CEO — Rohan Mehta
- MBA, Stanford GSB (2018)
- Previously: VP Product at LoanDepot (2018–2020), Product Manager at Stripe (2016–2018)
- Personal background note: civil judgment in 2019 (Santa Clara County, Case #19CV352117) — settled, $47,000 paid to former business partner; described by company as "a commercial dispute, fully resolved"
- Angel investor in 3 companies (Finpilot, Allocate, Pave)

### Co-Founder & CTO — Priya Shenoy
- MS Computer Science, Carnegie Mellon (2015)
- Previously: Principal Engineer at Kabbage (2015–2020), Staff Engineer at Plaid (2020–2022)
- Note: Left Plaid under terms of a standard IP invention assignment agreement; Plaid's general counsel sent a letter in March 2022 questioning ownership of ClearLend's "alternative signal graph" architecture — matter described by ClearLend as "resolved informally" with no written settlement
- GitHub: github.com/priyashenoy (public commits on core risk engine repo stopped March 2022)

### VP Engineering — Daniel Osei
- BSc, University of Ghana; MSc, Georgia Tech
- Previously: Engineering Manager at Blend Labs (2019–2023)
- Joined ClearLend: February 2024

### VP Sales — Sarah Kim
- Previously: Director of Partnerships at Brex (2020–2023)
- Joined ClearLend: August 2023
- Quota: $4.2M ARR for FY2026; current attainment (May 2026): 38% with 7 months remaining

### Head of Compliance — Marcus Webb
- Paralegal background (not a licensed attorney)
- Previously: Compliance Analyst at LendingClub (2018–2022)
- Manages all state lending license applications; no outside counsel on retainer
- Departed compliance attorney (Jennifer Cho, formerly of Orrick) left ClearLend in January 2026; replacement not yet hired

### Total Headcount: 47 FTE (28 engineers, 8 sales/CS, 5 ops, 4 exec, 2 compliance)
### Contractors: 11 — all classified as 1099 independent contractors in India; 4 have been working full-time for 18+ months

---

## 3. PRODUCT

### What It Does
ClearLend embeds via a single REST API call into a host platform (SaaS tool, e-commerce stack, payroll app). When a host platform's SMB customer needs working capital, they click "Get Funding" inside the platform UI. ClearLend's engine:
1. Pulls bank transaction data (Plaid integration), accounting data (QuickBooks/Xero), and 2,400 alternative signals (web traffic rank, review velocity, social sentiment, supplier payment timing)
2. Returns a credit decision in 11 seconds with an offer (loan amount, rate, term)
3. Disburses via ACH within 4 hours if accepted
4. Services the loan and splits revenue with the host platform (20% of net interest income)

### Differentiators (as claimed by company)
- **Speed:** 11-second decision vs 10–14 days (bank) or 2–3 days (competitors)
- **Default rate:** 3.2% vs sector average 7.1% (company-reported; no third-party audit)
- **Approval rate:** 61% vs bank average 27%
- **Embedded model:** zero direct-to-consumer CAC; revenue sharing creates platform lock-in

### Product Tiers
- **ClearLend Embed:** Core API, $0 upfront, revenue share
- **ClearLend Intelligence:** Risk scoring API only, $0.08/decision, for banks/fintechs that want only the score
- **ClearLend Enterprise:** White-label, custom models, SLA guarantees, $180K/yr base + rev share

---

## 4. TECHNOLOGY & INFRASTRUCTURE

### Tech Stack
| Layer | Technology |
|---|---|
| Core loan origination engine | Python 2.7 (migrated from legacy Kabbage codebase) |
| ML models / signal processing | Python 3.10, scikit-learn, XGBoost, PyTorch |
| API layer | Node.js 16 (EOL October 2023) |
| Database — loan records | MySQL 5.7 (EOL October 2023) |
| Database — ML feature store | PostgreSQL 15 |
| Cloud | AWS us-east-1 only (single region) |
| Authentication | Custom JWT implementation (in-house, not using Auth0/Cognito) |
| Data storage — customer PII | S3 bucket `clearlend-prod-customer-data` (public-read ACL was misconfigured for 9 months; patched September 2023; not disclosed to affected customers) |
| Bank connectivity | Plaid (OAuth), Finicity (fallback) |
| Infrastructure | EC2 + RDS; no Kubernetes; manual deployments |
| Monitoring | Datadog (basic metrics only; no SIEM) |

### Security Posture
- **SOC 2 Type 1:** Completed February 2025 (auditor: A-LIGN)
- **SOC 2 Type 2:** In progress (started April 2026; expected completion Q4 2026)
- **PCI-DSS:** Not applicable (no card processing); however, ClearLend stores ACH routing + account numbers in MySQL 5.7 with AES-128 encryption (not AES-256)
- **Penetration test:** Last external pentest was July 2023 (vendor: Rapid7). No pentest since. Pentest report identified 3 High severity and 7 Medium severity findings; status of remediation: unverified
- **Bug bounty:** None
- **SIEM / threat monitoring:** None

### Incident History
- **September 2023:** S3 misconfiguration patched internally. Estimated 12,000–18,000 customer records (name, SSN, bank account number, loan amount) were in a publicly readable S3 path for ~9 months. No breach notification sent to customers or state AGs. Not disclosed in this pitch document — discovered through ClearLend's own internal security audit. (Note: this section was added by the due diligence preparer, not provided by ClearLend.)
- **March 2025:** API rate limiter failure caused 4.3 hours of downtime for primary enterprise customer (Shopify plugin); $34,000 SLA credit paid.

### Technical Debt
- Python 2.7 loan origination engine: migration to Python 3 scoped but not funded; estimated 6-month engineering effort
- Node.js 16 API layer: upgrade backlog item, no timeline assigned
- MySQL 5.7 EOL: data migration to Aurora PostgreSQL estimated at 3 months, $180K in engineering time
- No disaster recovery plan formally documented; RTO/RPO undefined

---

## 5. FINANCIALS

### Revenue (Audited through Dec 2025; May 2026 unaudited)

| Period | ARR | QoQ Growth | Gross Margin |
|---|---|---|---|
| Q1 2025 | $1.8M | — | 39% |
| Q2 2025 | $2.4M | +33% | 41% |
| Q3 2025 | $3.1M | +29% | 42% |
| Q4 2025 | $4.6M | +48% | 41% |
| Q1 2026 | $5.9M | +28% | 40% |
| May 2026 (annualized) | $7.1M | — | 41% |

**Claimed YoY growth: 194% (Q4 2024 → Q4 2025)**
**Note:** Q4 2024 ARR was $1.56M; a $2M one-time revenue recognition event (Shopify enterprise contract, 2-year prepay) was included in Q4 2025 figures. Excluding this, organic Q4 2025 ARR was $2.6M, representing 67% YoY growth.

### Revenue Concentration
- **Shopify Integration (via Shopify App Store):** $3.9M ARR (55% of total revenue) — 3-year contract signed January 2025; contract includes termination-for-convenience clause at 12 months (exercisable from January 2026 onward)
- **QuickBooks Embed (Intuit partnership):** $1.9M ARR (27% of total revenue) — month-to-month since primary contract expired March 2026; Intuit has not formally renewed; currently under "commercial review"
- **Top 2 customers = 82% of ARR**
- All other customers combined: $1.3M ARR (18%)

### Unit Economics
| Metric | Value |
|---|---|
| Average loan size | $42,000 |
| Net interest income per loan | $1,890 |
| Platform revenue share paid | $378 (20%) |
| Servicing cost per loan | $210 |
| Net revenue per loan | $1,302 |
| Default loss per loan (3.2% rate) | $1,344 |
| Gross profit per loan | -$42 |
| LTV (36-month cohort, company model) | $2,800 |
| CAC (blended) | $1,320 |
| LTV:CAC | 2.1x |

**Note on default rate:** The 3.2% default figure is based on loans originated Jan–Dec 2024 (vintage analysis). Loans originated in 2025 (larger loan sizes, looser underwriting after Shopify deal) have a 30-day delinquency rate of 8.1% as of May 2026 — not yet in default but a leading indicator not disclosed in primary pitch materials.

### Burn & Runway
| Item | Monthly |
|---|---|
| Gross revenue | $591,000 |
| COGS (servicing, data, cloud) | $350,000 |
| Gross profit | $241,000 |
| Headcount (47 FTE + 11 contractors) | $510,000 |
| Infrastructure + tooling | $67,000 |
| G&A | $44,000 |
| Sales & Marketing | $89,000 |
| Total OpEx | $710,000 |
| **Net monthly burn** | **$(469,000)** |
| Cash on hand (May 2026) | $2,820,000 |
| **Runway at current burn** | **6.0 months** |

### Cap Table (Pre-Series A)
| Shareholder | Shares | % Ownership |
|---|---|---|
| Rohan Mehta (CEO) | 4,200,000 | 28.0% |
| Priya Shenoy (CTO) | 3,800,000 | 25.3% |
| Seed investors (Hustle Fund, angel round) | 3,600,000 | 24.0% |
| Employee option pool (ESOP) | 2,100,000 | 14.0% |
| Advisor pool | 450,000 | 3.0% |
| Convertible notes (2 SAFEs, 2023) | ~870,000 (estimated) | 5.7% |
| **Total (fully diluted)** | **15,020,000** | **100%** |

**Note:** Two SAFE notes (total $1.8M, MFN clause, uncapped) from 2023 will convert at Series A. Conversion math not included in cap table above — dilution to existing holders estimated at additional 5–7% depending on final valuation.

---

## 6. LEGAL & COMPLIANCE

### Corporate Structure
- Parent: ClearLend Technologies, Inc. (Delaware C-Corp)
- Subsidiary: ClearLend India Pvt Ltd (Bengaluru; incorporated February 2023; wholly owned)

### Lending Licenses
ClearLend originates loans in 34 U.S. states through a bank partnership model (partner bank: Meridian Community Bank, FDIC-insured, chartered in Utah). ClearLend acts as a Credit Services Organization (CSO) / loan servicer.

| State | Status |
|---|---|
| California | Licensed (CFL #60DBO-90123) |
| New York | **Unlicensed — operating under the bank partner model; NY DFS has issued informal guidance that this structure requires a NY licensed lender** |
| Texas | Licensed (SML #12345) |
| Florida | Licensed |
| Illinois | **Unlicensed — operating under bank partner model; IL DFPR opened inquiry in November 2025** |
| Georgia | **Unlicensed** |
| Virginia | Licensed |
| All other states (28) | Licensed or bank-partner model with no known state inquiry |

### Regulatory Actions
- **FTC Investigation (Case 2026-CID-01183):** In February 2026, ClearLend received a Civil Investigative Demand (CID) from the FTC under the FTC Act Section 20. The CID requests all internal documents related to credit decisioning model training data, adverse action notices, and AI model explainability for the period 2022–2025. ClearLend has retained outside counsel (Goodwin Procter) for this matter. The investigation is ongoing. **Not disclosed in primary pitch deck.** ClearLend's position: "We believe we are fully compliant and the CID is routine."
- **CFPB ECOA Compliance:** ClearLend's adverse action notices do not currently meet CFPB's model-specific explanation requirements under ECOA/Reg B for AI-driven credit decisions (per the March 2025 CFPB guidance bulletin). Remediation in development; no timeline committed.
- **EEOC / Fair Lending:** No active complaints. Last fair lending analysis: internal, Q3 2024 (vendor analysis not conducted).

### Intellectual Property
- **Patents:** 3 patent applications filed (USPTO); none granted as of May 2026
  - Application #17/823,445: "System and method for real-time credit underwriting using multi-source alternative data signals" (filed Aug 2022)
  - Application #17/923,112: "Graph-based SMB credit risk model" (filed Jan 2023) — **this is the application subject to the Plaid IP dispute referenced above**
  - Application #18/045,890: "Embedded lending API with revenue-share orchestration layer" (filed June 2023)
- **Trademarks:** "ClearLend" registered (USPTO Reg. #7,123,456). "ClearScore" brand name — **conflict: ClearScore UK (Experian subsidiary) has sent two C&D letters (2024, 2025) regarding naming; ClearLend does not use "ClearScore" in US marketing but the brand name appears in 3 internal product roadmap docs and 1 investor deck.**

### Contracts — Key Terms
- Shopify contract: 3-year term, Jan 2025–Jan 2028; termination for convenience by Shopify at 12 months (exercisable from Jan 2026); $4.2M revenue guarantee over term; exclusivity clause prevents ClearLend from partnering with Shopify competitors (Squarespace, Wix, BigCommerce) for 18 months
- Meridian Bank partnership: 5-year term; bank retains right to suspend originations with 30-day notice; bank's own exam by OCC is scheduled for Q3 2026; if bank receives adverse CRA rating, partnership may be at risk
- Plaid data agreement: Standard Plaid terms; Plaid can terminate data access with 90 days notice; replacement connectivity (Finicity) untested at production scale

### Contractor Classification Risk
11 contractors in India, all on 1099/equivalent. Four individuals have worked exclusively for ClearLend for 18–24 months, receive company-issued equipment, attend daily standups, and work defined hours. This pattern is consistent with employee misclassification under both Indian labor law and potential U.S. tax / benefits liability.

---

## 7. MARKET

### TAM / SAM / SOM (Company Claims)
- **TAM:** $2.3 trillion (U.S. SMB credit market, total outstanding)
- **SAM:** $180 billion (embedded finance / non-bank SMB lending)
- **SOM:** $4.8 billion (AI-native underwriting APIs, 5-year target)

**Independent Analysis Note:** The $2.3T TAM figure is total outstanding SMB debt — not addressable by ClearLend's model. The actual addressable segment (SMBs embedded within SaaS platforms seeking sub-$250K working capital) is estimated at $40–55B outstanding, with new origination volume of ~$18B/year. ClearLend's top-down TAM is inflated by ~50x.

### Competitive Landscape

| Competitor | Funding | Key Differentiator vs ClearLend |
|---|---|---|
| **Pipe Technologies** | $316M raised | Revenue-based financing; direct-to-business; larger deals |
| **Capchase** | $700M raised | SaaS-specific; ARR financing; deeper integrations |
| **Arc** | $200M raised | Series-stage SaaS; higher ACV; no revenue share model |
| **Shopify Capital** | Shopify internal | Native to platform; zero integration friction; $5B originated |
| **Square Capital (Block)** | Block internal | Seller ecosystem; $15B originated since 2014 |
| **Clearco** | $700M raised; restructured 2023 | Revenue advance model; recent layoffs, retreating from market |
| **Stripe Capital** | Stripe internal | ~$4B originated; native platform advantage |
| **Kabbage (AmEx)** | Acquired by AmEx $850M | Enterprise distribution; legacy tech but AmEx balance sheet |

**Critical risk:** Shopify Capital (ClearLend's 55% revenue customer's direct competitor product) has originated >$5B in loans natively. If Shopify exercises its termination-for-convenience clause and expands Shopify Capital instead, ClearLend loses 55% of ARR with 30 days notice.

### Market Conditions (2025–2026)
- U.S. VC funding into fintech lending: down **71% YoY** (PitchBook Q1 2026) from $8.2B (2023) to $2.4B (2025)
- CFPB rule-making (Small Business Data Collection Rule under Dodd-Frank 1071): requires detailed loan-level reporting from lenders like ClearLend starting Q3 2026 — significant compliance build required, estimated $400K engineering/legal cost not budgeted
- Federal Reserve base rate: 4.25% (May 2026); elevated rates compress net interest margins; ClearLend's average loan APR is 24.5% — blended cost of capital through Meridian Bank is 9.8%, leaving 14.7% gross NIM before losses; if default rates rise toward 2025 cohort delinquency signal (8.1%), NIM collapses
- BNPL / embedded credit sector VC narrative: "peak enthusiasm passed" — Klarna IPO (2024) underperformed, Affirm stock -67% from peak, sector sentiment cautious
- Regulation: FTC AI model explainability pressure (direct risk to ClearLend), CFPB Reg B AI adverse action (direct risk), UDAAP enforcement increasing

### Growth Assumptions in Pitch
ClearLend projects $28M ARR by end of FY2027 (18 months), implying ~295% growth from current $7.1M.

**Key assumptions:**
1. Shopify contract renewed and not terminated (binary risk: 55% of ARR)
2. Intuit QuickBooks contract formally renewed by Q3 2026 (currently month-to-month)
3. 4 new enterprise platform partners signed by Q4 2026 (VP Sales at 38% of quota)
4. Default rates remain at 3.2% (2025 cohort showing 8.1% delinquency)
5. Series A closes by August 2026 (6-month runway from May 2026)

---

## 8. USE OF FUNDS ($12M SERIES A)

| Category | Amount | % |
|---|---|---|
| Engineering (Python 3 migration, API modernization, ML models) | $3,600,000 | 30% |
| Sales & Marketing (5 new AEs, demand gen) | $2,400,000 | 20% |
| Compliance & Legal (SOC 2 Type 2, state licensing, FTC) | $1,800,000 | 15% |
| Product (mobile SDK, webhooks, new verticals) | $1,440,000 | 12% |
| Working capital / loan book expansion | $1,200,000 | 10% |
| G&A / hiring (CFO, Head of Legal) | $960,000 | 8% |
| Reserve | $600,000 | 5% |

**Projected runway post-Series A:** 26 months (assumes burn increases to $625K/month as headcount grows)

---

## 9. TRACTION & MILESTONES

### Achieved
- $7.1M ARR (May 2026)
- 1,847 SMB loans originated since inception (cumulative principal: $77.6M)
- 61% approval rate vs 27% industry average (self-reported)
- 3.2% default rate vs 7.1% sector average (2024 vintage; 2025 vintage not yet mature)
- Shopify App Store: 4.6/5 stars, 312 reviews
- Patent applications: 3 filed
- SOC 2 Type 1 certified (February 2025)

### Upcoming (as claimed in pitch deck)
- SOC 2 Type 2 completion: Q4 2026
- Python 3 migration: Q2 2027
- 5 new platform partner integrations: Q4 2026
- Series A close target: August 2026

---

## 10. FINANCIAL PROJECTIONS

| | FY2025 (Actual) | FY2026 (Forecast) | FY2027 (Forecast) |
|---|---|---|---|
| ARR | $4.6M | $14.2M | $28.0M |
| Revenue | $3.8M | $11.1M | $24.4M |
| Gross Margin | 41% | 44% | 47% |
| Net Burn | $(4.2M) | $(5.9M) | $(3.1M) |
| Headcount EOY | 47 | 68 | 94 |

**Auditor:** Marcum LLP (FY2025 audit complete)
**Revenue recognition:** ASC 606; net interest income recognized ratably over loan term; platform fees recognized on disbursement.

---

## 11. INVESTORS & ADVISORS

### Current Investors
- **Hustle Fund** — led $2.5M seed (2022)
- **Angel round** — $1.8M from 6 angels including 1 former LendingClub exec, 2 Stanford GSB alums (2023)
- **SAFE notes** — $1.8M total, uncapped with MFN clause (2023)

### Advisors
- Former VP Risk, Capital One (equity: 0.15%)
- Ex-CFO, OnDeck Capital (equity: 0.25%) — **Note: OnDeck was acquired after near-insolvency in 2020; advisor's track record in the sector includes this outcome**
- Partner, Goodwin Procter FinTech practice (relationship only; no equity)

---

## 12. ASK

**Raising:** $12,000,000 Series A
**Pre-money valuation:** $36,000,000
**Post-money valuation:** $48,000,000
**Instrument:** Priced equity (Series A Preferred)
**Lead investor sought:** Yes — 60% of round reserved for lead
**Expected close:** August 2026
**Use:** See Section 8

---

## APPENDIX A — KEY METRICS SUMMARY

| Metric | Value | Note |
|---|---|---|
| ARR | $7.1M | May 2026 annualized |
| ARR growth YoY | 194% (claimed) / 67% (organic) | See footnote Section 5 |
| Top 2 customer concentration | 82% | Shopify + Intuit |
| Gross margin | 41% | Below SaaS median of 70%+ |
| LTV:CAC | 2.1x | Below healthy 3x+ threshold |
| Runway | 6 months | As of May 2026 |
| Default rate (2024 vintage) | 3.2% | Self-reported, unaudited |
| Delinquency rate (2025 vintage) | 8.1% (30-day) | Not in primary pitch |
| Open regulatory actions | 2 (FTC CID + IL DFPR inquiry) | Not in primary pitch deck |
| State licensing gaps | NY, IL, GA unlicensed | Lending in these states |
| Security incidents | 1 undisclosed S3 breach (2023) | ~18,000 records affected |
| Pending IP dispute | Plaid (CTO's prior employer) | Patent #17/923,112 at risk |
| Tech debt — EOL software | Python 2.7, Node.js 16, MySQL 5.7 | Core production systems |
| SOC 2 Type 2 | Not complete | In progress Q4 2026 |
| Pentest last conducted | July 2023 | 3 High severity unresolved |

---

*This brief was prepared for investment committee review. All financial figures for FY2025 are audited by Marcum LLP. FY2026 figures are unaudited management estimates. Forward-looking projections involve significant assumptions and risks. This document is confidential and intended solely for the recipient.*
