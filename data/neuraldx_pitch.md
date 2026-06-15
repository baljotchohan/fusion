# NeuralDx Inc — Series B Investment Pitch Brief
> Prepared for: Investment Committee Due Diligence
> Date: May 2026
> Raise: $25,000,000 | Post-Money Valuation: $120,000,000
> Round Type: Series B (Priced Equity)
> Sector: AI-Powered Medical Diagnostics (Radiology)

---

## 1. COMPANY OVERVIEW

**Legal Name:** NeuralDx Inc.
**Incorporated:** Delaware C-Corp, January 2020
**Headquarters:** 601 Gateway Blvd, Suite 1100, South San Francisco, CA 94080
**R&D Office:** 210 College Road East, Princeton, NJ 08540 (clinical AI team, 19 staff)
**India Engineering Hub:** Hyderabad, Telangana (17 engineers, contract basis)
**Website:** neuraldx.ai
**LinkedIn:** linkedin.com/company/neuraldx-ai

**Tagline:** *"94% accuracy. 11 seconds. The AI radiologist that never sleeps."*

**One-liner:** NeuralDx deploys an FDA-cleared AI platform inside hospital radiology departments that automatically analyzes CT scans for early-stage lung nodules, flagging critical findings in 11 seconds vs. 45+ minutes for a radiologist backlog — reducing missed diagnoses and radiologist burnout simultaneously.

**Claimed impact:** In a 14-month deployment at Penn Medicine (flagship customer), NeuralDx claims to have flagged 312 early-stage lung cancers that would have been delayed in the reading queue by more than 4 hours, with 94.1% sensitivity and 91.3% specificity on internal validation data.

---

## 2. FOUNDERS & TEAM

### Co-Founder & CEO — Dr. Arjun Kapoor, MD PhD
- MD, Johns Hopkins School of Medicine (2013); PhD Biomedical Engineering, MIT (2016)
- Previously: Attending Radiologist, UCSF Medical Center (2016–2019); co-founded Lumina Medical AI (2019) — company raised $4.2M seed from a16z Bio, pivoted twice, dissolved March 2021 leaving investors with approximately $2M in unrecovered capital. Investors include managing partner at Sequoia Bio (relationship now strained).
- Board-certified diagnostic radiologist (ABR); license active in CA, NJ, PA
- Published: 23 peer-reviewed papers on deep learning in radiology (Nature Medicine, Radiology, JAMA)
- Personal note: Dr. Kapoor retains a 0.4% equity stake in Lumina Medical AI's IP successor entity, which licenses a related convolutional neural network architecture to two competitors. Potential undisclosed conflict.

### Co-Founder & CTO — Meera Subramaniam, PhD
- PhD Computer Science (Machine Learning), Stanford (2017)
- Previously: Research Scientist, Google Brain (2017–2019); Senior ML Engineer, Recursion Pharmaceuticals (2019–2021)
- Co-inventor on NeuralDx's core algorithm (US Patent Application 17/884,212)
- **Legal note:** Two former NeuralDx engineers (Prakash Raman and Yevgenia Koval, both departed Q2 2023) filed a complaint in Delaware Chancery Court (Case #2023-0441-MTZ) alleging they are co-inventors of the core nodule detection algorithm and that their inventions were improperly assigned without adequate compensation. Case is in discovery. NeuralDx's counsel (Wilson Sonsini) assesses 35–40% probability of material adverse outcome. **Not disclosed in Series B pitch deck.**
- GitHub contributions to the core model repository ceased March 2023 (coincides with the Raman/Koval departures).

### Chief Medical Officer — Dr. Patricia Nwosu, MD
- MD, Northwestern; fellowship in thoracic radiology, Mayo Clinic
- Previously: VP Medical Affairs, Aidoc (2020–2022); left Aidoc under standard non-disparagement agreement
- **Conflict note:** Dr. Nwosu holds 12,000 vested stock options in Aidoc (current estimated value ~$85,000). No waiver or independent review conducted.

### VP Engineering — Sanjay Mehrotra
- BSc, IIT Bombay; MS, Georgia Tech
- Previously: Principal Engineer, Amazon AWS HealthLake (2018–2023)
- Joined NeuralDx: September 2023
- Note: Entire senior engineering team hired post-Series A (2023); no original founding engineers remain

### VP Sales & Partnerships — Karen Bellotti
- Previously: National Accounts Director, Nuance Communications (now Microsoft) (2016–2022); Regional VP, Viz.ai (2022–2024)
- **Conflict note:** Karen holds 8,500 vested Viz.ai options (Viz.ai is a direct competitor). Option exercise not yet executed.
- Current quota: $9.8M ARR for FY2026; attainment as of May 2026: 29% (8 months remaining in fiscal year)

### Head of Regulatory Affairs — Thomas Huang
- Previously: FDA Reviewer, Center for Devices and Radiological Health (CDRH), 2015–2020
- Joined NeuralDx: February 2021
- Note: Thomas was the FDA reviewer on a competing company's 510(k) submission (K211432, Aidoc) before joining NeuralDx. Per FDA post-employment rules (21 CFR Part 19), his participation in any NeuralDx FDA submission involving the same product type requires disclosure and recusal. NeuralDx has not conducted a formal recusal review.

### Total Headcount: 61 FTE
### Contractors: 17 — 11 in Hyderabad (India), 6 in Eastern Europe (Ukraine/Poland). All classified as independent contractors. 8 of 17 have worked exclusively for NeuralDx for 24+ months with daily standups, company-issued equipment, and defined work schedules — classic misclassification risk under Indian Contract Labour Act and IRS SS-8 test.

---

## 3. PRODUCT

### Core Platform — NeuralDx Radiology Intelligence Suite (RIS)

**NeuralDx Detect (FDA-cleared):**
FDA 510(k) clearance K221847 (cleared November 2022) for Computer-Aided Detection (CADe) of **pulmonary nodules on non-contrast CT scans in adult patients (≥18 years)**. This is NeuralDx's only cleared indication.

Cleared workflow: CT scan uploaded via DICOM → NeuralDx RIS processes in 11 seconds → outputs nodule coordinates, size (mm), Lung-RADS score, and triage priority flag → integrated directly into radiologist PACS workstation.

**NeuralDx Expand (NOT FDA-cleared — currently marketed and sold):**
NeuralDx's sales team actively markets and has deployed the following capabilities at 6 hospital systems with zero additional FDA clearance:
- Liver lesion characterization on contrast-enhanced CT (not cleared)
- Pulmonary embolism detection on CT pulmonary angiography (not cleared — PE detection requires separate 510(k); FDA has issued warning letters to two competitors for identical off-label marketing)
- Intracranial hemorrhage flagging on non-contrast head CT (not cleared)
- Pneumothorax detection on chest X-ray (not cleared; a separate, unrelated modality from the cleared indication)

**NeuralDx Score (pipeline, not launched):**
Longitudinal patient risk scoring using 36-month imaging history. Beta at 2 sites. No regulatory pathway defined.

### Differentiation Claims (vs. Aidoc, Viz.ai, Intelerad AI)
- **Speed:** 11-second analysis (competitors claim 15–30 seconds — marginal difference)
- **Integration depth:** Direct PACS integration via HL7 FHIR + DICOM SR (same as all competitors)
- **Accuracy:** 94.1% sensitivity — but this is based on NeuralDx's own internal validation dataset, not an independent external validation. Aidoc's cleared product shows 94.3% sensitivity in independent peer-reviewed validation (Radiology, 2024).
- **Price:** $0.85/scan (below Aidoc's ~$1.10/scan and Viz.ai's ~$1.20/scan) — margin-compressing strategy

---

## 4. TECHNOLOGY & INFRASTRUCTURE

### AI Model Architecture
| Component | Details |
|---|---|
| Model type | 3D Convolutional Neural Network (3D-CNN) + Vision Transformer hybrid |
| Framework | PyTorch 1.12 (released 2022; current stable is 2.3) |
| CUDA version | 11.6 (EOL; current is 12.4) |
| Training data | 847,000 CT scans from 6 academic medical centers (2015–2022) |
| Training data demographics | 89% Caucasian, 6% Hispanic, 3% Black, 2% Asian (based on available EHR metadata) |
| Last model retraining | March 2022 (model has not been updated in 26+ months) |
| Model version in production | v1.2.4 (same version since FDA clearance in Nov 2022) |
| Model drift monitoring | None — no system to detect if production inputs deviate from training distribution |
| Explainability | GradCAM heatmaps (limited; FDA is increasing scrutiny on AI explainability post-2025 guidance) |

### Training Data Bias Risk
The 89% Caucasian training composition is a known FDA concern. NeuralDx's own internal bias analysis (February 2024, conducted by Dr. Nwosu, not independently audited) found:
- Sensitivity in Black patients: 87.3% vs 96.1% in White patients (8.8 percentage point gap)
- Sensitivity in patients with BMI >35: 81.2% (obese patients have different CT imaging characteristics)
- These findings were NOT disclosed in the FDA 510(k) submission (submitted August 2022, cleared November 2022)
- FDA's Office of Minority Health released AI bias guidance in March 2025 that retroactively flags this type of demographic imbalance as requiring supplemental 510(k) or de novo submission

### Clinical Evidence
- **Internal validation:** 14,200 scans from NeuralDx's own training-adjacent dataset. Sensitivity: 94.1%, Specificity: 91.3%.
- **External validation:** ONE peer-reviewed paper (Chest, 2023) using 3,200 scans from Yale New Haven Hospital. Sensitivity: 88.7%, Specificity: 86.4% — significantly lower than internal claims. Company marketing uses internal figures only.
- **Prospective real-world study:** Not conducted. The Penn Medicine "312 cancers flagged" statistic is from an internal deployment report, not a peer-reviewed prospective study.

### Infrastructure
| Layer | Technology |
|---|---|
| Cloud | AWS us-east-1 only (single region; no multi-region failover) |
| DICOM server | Orthanc 1.9.0 (2021 release; current is 1.12.3; CVE-2023-33466 unpatched — allows unauthenticated remote read of DICOM metadata) |
| PHI storage | S3 buckets: `neuraldx-prod-phi-ct-scans`, `neuraldx-prod-phi-reports` |
| PHI encryption | AES-256 at rest ✓ |
| PHI access logging | CloudTrail enabled ✓ |
| Business Associate Agreements | Signed with AWS ✓, but **NOT signed with Datadog** (monitoring tool that receives application logs containing patient scan metadata — potential HIPAA violation) |
| Inference compute | AWS EC2 p3.2xlarge (V100 GPU; replaced by p4/p5 instances for cost efficiency — not yet migrated) |
| Authentication | Okta SSO for admin; PACS integration uses static API keys (not rotated in 18+ months) |
| Disaster recovery | No documented DR plan; RTO undefined; only us-east-1 |
| SOC 2 Type 2 | Certified (February 2025, A-LIGN) ✓ |
| HITRUST CSF | In progress (targeted Q3 2026) |
| Penetration test | Last conducted: September 2023 (Bishop Fox). 2 Critical, 4 High severity findings. Remediation status of Critical findings: 1 resolved, 1 open (unauthenticated DICOM endpoint) |

### FDA Software as a Medical Device (SaMD) Compliance
- NeuralDx RIS is classified as Class II, SaMD under FDA's Digital Health Center of Excellence framework
- Required post-market surveillance (21 CFR Part 822): NeuralDx has submitted 3 MDR (Medical Device Reports) for cases where the AI flagged a nodule that was subsequently confirmed as a false positive leading to unnecessary biopsy. A 4th MDR is pending internal review (not yet filed, deadline was April 30, 2026 — 30 days past statutory deadline).
- Algorithm Change Protocol (ACP): NeuralDx filed an ACP with FDA in 2022 allowing minor model updates without new 510(k). However, any model retrain with new data or architecture changes requires a new predetermined change control plan (PCCP) submission — NeuralDx has not filed one despite planning a major model update in Series B roadmap.

---

## 5. FINANCIALS

### Revenue (Audited through Dec 2025; May 2026 unaudited)

| Period | ARR | QoQ Growth | Gross Margin |
|---|---|---|---|
| Q1 2025 | $3.1M | — | 34% |
| Q2 2025 | $4.8M | +55% | 36% |
| Q3 2025 | $6.2M | +29% | 37% |
| Q4 2025 | $9.4M | +52% | 38% |
| Q1 2026 | $11.1M | +18% | 37% |
| May 2026 (annualized) | $13.8M | — | 38% |

**Claimed YoY growth: 345% (Q4 2024 → Q4 2025)**

**Critical footnote:** Q4 2024 ARR was $2.1M. Q4 2025 figure of $9.4M includes:
- $5.2M recurring subscription revenue (scan-based SaaS)
- **$3.1M one-time NIH STRIDES Initiative grant** (non-recurring government research award — recognized as revenue per ASC 606 but represents 33% of Q4 2025 "ARR")
- $1.1M one-time implementation fee from Mayo Clinic (deferred until Q1 2026 per contract, recognized early)

Excluding one-time items, organic Q4 2025 ARR = $5.2M → **organic YoY growth: 148%**, not 345%.

### Revenue Concentration
| Customer | ARR | % of Total | Contract Status |
|---|---|---|---|
| Penn Medicine (flagship) | $5.8M | 42% | 3-year contract, expires Jan 2027; RFP process already open for competitive rebid |
| Mayo Clinic | $4.7M | 34% | Pilot (not fully contracted); month-to-month; Mayo's internal AI team building competing tool |
| UCSF Medical Center | $1.4M | 10% | Annual renewal; signed April 2026 |
| 4 smaller health systems | $1.9M | 14% | Various; all annual |
| **Top 2 customers = 76% of ARR** | | | |

**Critical risk:** Penn Medicine's CFO issued an internal memo (obtained by NeuralDx through a board member at Penn) in March 2026 describing a 20% AI vendor budget consolidation initiative. Penn is evaluating Aidoc and Microsoft Nuance DAX as replacements. NeuralDx was NOT informed of this officially. **Not in pitch deck.**

**Mayo Clinic risk:** Mayo's internal AI center (Dr. Bradley Erickson's group) published a preprint in April 2026 showing their in-house model achieving 91.2% sensitivity on chest CT — approaching NeuralDx's claimed performance. Mayo's CFO told NeuralDx's VP Sales in January 2026 that "build vs. buy" is being formally evaluated. Month-to-month contract has 30-day termination notice.

### Revenue Recognition Issues
NeuralDx's auditor (Grant Thornton) issued an **emphasis-of-matter paragraph** in the FY2025 audit report regarding revenue recognition on the NIH STRIDES grant. The company recognizes the full $3.1M in Q4 2025 (quarter of award); Grant Thornton believes milestone-based recognition may be more appropriate, which would spread revenue over 18 months. **Restatement risk: $1.8M–$2.1M of Q4 2025 revenue may require restatement.**

### Unit Economics
| Metric | Value | Notes |
|---|---|---|
| Average scans processed/month/customer | 12,400 | |
| Price per scan | $0.85 | Below market ($1.10–$1.20 competitors) |
| Revenue per customer per month | $10,540 | |
| AWS inference cost per scan | $0.31 | V100 GPU; p4 migration would cut to $0.18 |
| Clinical validation cost per scan | $0.08 | Radiologist spot-check labor |
| Datadog / monitoring per scan | $0.04 | |
| Total COGS per scan | $0.43 | |
| Gross profit per scan | $0.42 | 49% at scan level |
| Implementation / onboarding cost per customer | $320,000 | PACS integration, staff training, validation |
| Blended CAC | $380,000 | Includes 18-month avg sales cycle |
| LTV (3-year contract at $10,540/mo gross profit) | $379,440 | |
| **LTV:CAC ratio** | **1.0x** | Below all acceptable thresholds |

**Note:** LTV:CAC of 1.0x means NeuralDx breaks even on customer acquisition in 3 years — with zero margin for churn, support costs, or price renegotiation.

### Burn & Runway
| Item | Monthly |
|---|---|
| Gross revenue | $1,150,000 |
| COGS | $713,000 |
| Gross profit | $437,000 |
| R&D (AI team, compute, clinical studies) | $620,000 |
| Sales & Marketing | $290,000 |
| G&A | $180,000 |
| Regulatory affairs | $95,000 |
| Legal (IP litigation defense) | $110,000 |
| Total OpEx | $1,295,000 |
| **Net monthly burn** | **$(858,000)** |
| Cash on hand (May 2026) | $6,020,000 |
| **Runway at current burn** | **7.0 months** |

**Note:** Legal costs are expected to rise to $160,000–$200,000/month by Q4 2026 as the Raman/Koval IP litigation enters trial preparation.

### Cap Table (Pre-Series B, Fully Diluted)
| Shareholder | Shares | % |
|---|---|---|
| Dr. Arjun Kapoor (CEO) | 5,400,000 | 22.1% |
| Meera Subramaniam (CTO) | 4,200,000 | 17.2% |
| Series A investors (a16z Bio led, $18M raise, 2022) | 7,800,000 | 31.9% |
| Employee option pool | 3,600,000 | 14.7% |
| Advisor pool | 480,000 | 2.0% |
| Seed investors (2020 round, $3.5M) | 2,100,000 | 8.6% |
| Convertible notes (2023 bridge, $2.8M, 20% discount, no cap) | ~870,000 est. | 3.6% |
| **Total** | **24,450,000** | **100%** |

**a16z Bio board rights:** a16z holds 1 board seat (observer rights for 2 additional seats). Per side letter, a16z has pro-rata rights in Series B. a16z has NOT committed to leading or participating in Series B — described in pitch deck as "expected to participate" without written confirmation.

---

## 6. LEGAL & COMPLIANCE

### FDA Regulatory Status
| Product | Status | Risk |
|---|---|---|
| NeuralDx Detect — lung nodule on non-contrast CT | Cleared (K221847, Nov 2022) | ✅ Cleared |
| Liver lesion characterization | **NOT cleared; actively marketed** | 🚨 Off-label marketing violation |
| PE detection on CTPA | **NOT cleared; actively marketed** | 🚨 FDA has issued warning letters to competitors for this exact violation |
| Intracranial hemorrhage on head CT | **NOT cleared; actively marketed** | 🚨 Off-label marketing violation |
| Pneumothorax on chest X-ray | **NOT cleared; actively marketed** | 🚨 Different modality — entirely separate 510(k) required |

**FDA Warning Letter Risk:** FDA's Digital Health Center of Excellence sent informal inquiry letters to NeuralDx in January 2026 and March 2026 requesting clarification on "scope of commercial deployment relative to cleared indications." NeuralDx's regulatory counsel has responded; no formal Warning Letter issued as of May 2026. However, if a formal Warning Letter is issued, hospital procurement halts industry-wide for the named vendor — **existential commercial risk.** History: Arterys received FDA warning in 2021 for similar off-label marketing; commercial pipeline froze for 9 months.

### IP Litigation
**Raman & Koval v. NeuralDx Inc. (Delaware Chancery, Case #2023-0441-MTZ)**
- Filed: September 2023
- Plaintiffs: Prakash Raman (former Senior ML Engineer) and Yevgenia Koval (former Research Scientist)
- Claim: Co-inventors of the core 3D-CNN nodule detection algorithm (US Patent App. 17/884,212); seek correction of inventorship, 30% equity in patent, and $14.5M in damages
- Current status: Discovery phase; trial scheduled February 2027
- NeuralDx outside counsel assessment: 35–40% probability of adverse outcome
- **If adverse: patent ownership disputed on NeuralDx's only cleared product; licensing obligations to plaintiffs; potential injunction on commercial deployment**
- **Not disclosed in Series B pitch deck**

### Prior Art Risk
Stanford University's AI Lab published "DeepNodule: 3D Convolutional Approaches to Pulmonary Nodule Detection" (NeurIPS 2019, Proceedings) describing an architecture substantively similar to NeuralDx's claimed invention. NeuralDx's patent counsel conducted a FTO (Freedom to Operate) analysis in 2021 that did not cite this paper. USPTO examiner cited it as prior art in a first office action (October 2023) — NeuralDx filed a response distinguishing the claims (January 2024); patent still pending.

### HIPAA & Data Compliance
- **Business Associate Agreement (BAA) gap:** Datadog receives application performance logs from NeuralDx's production systems. These logs contain PHI (scan timestamps correlated with patient MRN identifiers from PACS integration). Datadog's standard terms do NOT include HIPAA BAA coverage for log ingestion. NeuralDx's legal team identified this in January 2026; remediation (migrate to Datadog's HIPAA-eligible tier) is in progress but not complete.
- **Impact:** All PHI transmitted to Datadog since NeuralDx's production launch (estimated 2021) is a potential HIPAA breach affecting approximately 180,000 patient scan records. Reportable to HHS Office for Civil Rights if confirmed as impermissible disclosure. OCR penalty range: $100–$50,000 per violation, up to $1.75M annual cap per violation category.
- **Minnesota incident (February 2026):** A PACS integration bug at North Memorial Health (Minneapolis) caused NeuralDx's system to temporarily write AI output reports to the wrong patient records for a 6-hour window. 43 patients received incorrect reports in their EHR. NeuralDx notified North Memorial; North Memorial filed HIPAA breach notification with HHS in March 2026. NeuralDx is named as the business associate. Investigation ongoing.

### Contract Red Flags
- Penn Medicine contract: 3-year term Jan 2024–Jan 2027; includes a performance clause requiring NeuralDx to maintain ≥92% sensitivity on Penn's live scan population. NeuralDx's Q1 2026 internal monitoring shows Penn sensitivity at 89.4% — **below contractual threshold** — triggering Penn's right to renegotiate pricing or terminate with 90-day notice.
- All contracts include an FDA Compliance clause: "Vendor represents that its products are used within cleared indications." The off-label marketing of liver/PE/ICH/pneumothorax modules may trigger breach of these representations in all 11 hospital contracts.

### Securities Issues
- **409A valuation discrepancy:** NeuralDx's most recent 409A valuation (March 2026, Carta) set common stock FMV at $2.10/share. The proposed Series B price is $4.91/share (implied). The 2.3x gap is unusually large for a company this stage; IRS may scrutinize option grants made between September 2025 and now at $2.10 as potentially underpriced relative to the fair market value.

---

## 7. MARKET

### TAM / SAM / SOM (Company Claims)
- **TAM:** $45B (global radiology market, 2025)
- **SAM:** $12B (AI-assisted diagnostic imaging)
- **SOM:** $2.8B (AI CAD tools for US hospital networks, 5-year)

**Independent analysis:** The $45B global radiology figure is total radiology department spending — equipment, labor, real estate, everything. The software AI addressable market for CADe/CADx tools in US hospitals is estimated at $900M–$1.4B by 2028 (Signify Research, 2025). NeuralDx's claimed SAM is inflated by ~8–13x.

### Competitive Landscape

| Competitor | Funding Raised | Key Threat to NeuralDx |
|---|---|---|
| **Aidoc** | $320M total; $110M Series D (Feb 2026) | Market leader; 1,200+ hospital deployments; 15 cleared indications vs NeuralDx's 1 |
| **Viz.ai** | $318M total; FDA-cleared for stroke, PE, aortic dissection | Enterprise partnerships with Epic and Cerner; 20+ cleared AI models |
| **Intelerad (AI Suite)** | Acquired by Hg Capital ($1.7B valuation, 2022) | PACS vendor; bundling AI "free" with PACS contracts — existential pricing pressure |
| **Microsoft Nuance DAX** | Microsoft-backed (unlimited) | Already in 80% of US hospitals via Dragon Medical; AI diagnostic tools bundled into existing contracts |
| **Google Health / DeepMind** | Alphabet-backed | Published Nature Medicine paper showing superhuman performance on mammography; entering radiology AI in 2026 |
| **GE HealthCare AI** | NYSE: GEHC; $19B market cap | Bundling AI with CT scanner hardware purchases — zero incremental CAC for hospitals already buying GE scanners |
| **Mayo Clinic AI (in-house)** | Internal development | NeuralDx's second-largest customer is building its own replacement |

**Macro headwinds:**
- US hospital operating margins averaged -1.1% in 2025 (Kaufman Hall); capital and SaaS budgets frozen or declining
- "Bundling" trend: large PACS vendors (Intelerad, Sectra, Philips Vue) offering AI features at near-zero marginal cost with existing hardware contracts
- CMS reimbursement for AI-CAD: CPT code 0691T pays $18.25/scan. NeuralDx's price is $0.85/scan for hospitals — hospitals collect $18.25 per Medicare scan. But many private insurers (Blue Cross, Aetna, Cigna) do NOT separately reimburse for AI-CAD tools, meaning hospitals absorb the cost as operational expense with uncertain ROI.
- FDA regulatory backlog: clearance for additional indications (PE, ICH) estimated 18–24 months minimum; NeuralDx is marketing them now without clearance.
- **Radiologist workforce recovery:** The radiologist shortage of 2020–2024 that drove AI urgency is easing; 2025 ACGME data shows a 22% increase in radiology residency match rates. Reduced urgency for AI workflow tools.

### Growth Projections in Pitch
NeuralDx projects $52M ARR by end of FY2027 (18 months), implying 276% growth from current $13.8M.

**Key assumptions:**
1. Penn Medicine contract renewed (binary risk: 42% of ARR; Penn actively evaluating competitors)
2. Mayo Clinic converts from pilot to full contract (currently month-to-month; Mayo building in-house)
3. 6 new health system contracts signed by Q4 2026 (VP Sales at 29% of quota)
4. FDA clearance for PE detection by Q1 2027 (optimistic; typical timeline 18–24 months)
5. No FDA enforcement action for current off-label marketing
6. IP litigation resolved favorably (35–40% probability of adverse outcome)
7. Series B closes by September 2026 (7-month runway from May 2026)

---

## 8. USE OF FUNDS ($25M SERIES B)

| Category | Amount | % |
|---|---|---|
| AI model development (v2.0 retrain, bias remediation, new indications) | $7,500,000 | 30% |
| Regulatory (510(k) submissions for PE, ICH, liver; PCCP filing; FDA audit response) | $4,250,000 | 17% |
| Sales & Marketing (6 new enterprise AEs, marketing, conference presence) | $4,000,000 | 16% |
| Clinical studies (external validation, prospective RCT for PE detection) | $3,500,000 | 14% |
| Infrastructure (multi-region AWS, GPU upgrade, HIPAA remediation) | $2,750,000 | 11% |
| IP litigation defense (Raman/Koval through trial) | $1,500,000 | 6% |
| G&A (GC hire, CFO upgrade, HR) | $1,500,000 | 6% |

**Note:** $1.5M explicitly budgeted for IP litigation — unusual for a pitch deck and signals the seriousness of the Raman/Koval case. NeuralDx's outside counsel estimates total litigation cost through trial at $3.8M–$5.2M if case proceeds to verdict.

---

## 9. CLINICAL TRACTION & MILESTONES

### Claimed Achievements
- 11 hospital system deployments (3 flagship academic medical centers, 8 community hospitals)
- 4.2M CT scans processed since commercial launch (January 2023)
- 312 early-stage lung cancers flagged at Penn Medicine (internal report, not peer-reviewed)
- FDA 510(k) clearance K221847 (November 2022) — lung nodule detection only
- SOC 2 Type 2 certified (February 2025)
- 3 peer-reviewed publications (Chest 2023; JACR 2024; RSNA Proceedings 2024)

### Red Flag: External vs. Internal Accuracy Gap
| Validation Type | Sensitivity | Specificity | Dataset |
|---|---|---|---|
| Internal (NeuralDx dataset) | 94.1% | 91.3% | 14,200 scans (training-adjacent) |
| External (Yale NHMS, Chest 2023) | 88.7% | 86.4% | 3,200 scans |
| Gap | **-5.4%** | **-4.9%** | |

A 5.4% sensitivity gap means for every 100 actual nodules, NeuralDx's real-world system misses approximately 5–6 that internal marketing claims it catches. At 4.2M scans processed, this is a potentially significant patient safety signal.

---

## 10. FINANCIAL PROJECTIONS

| | FY2025 (Actual) | FY2026 (Forecast) | FY2027 (Forecast) |
|---|---|---|---|
| ARR | $9.4M | $26.5M | $52.0M |
| Revenue (recognized) | $8.1M | $21.2M | $44.8M |
| Gross Margin | 38% | 43% | 49% |
| Net Burn | $(7.2M) | $(8.9M) | $(4.1M) |
| Headcount EOY | 61 | 89 | 124 |

**Auditor:** Grant Thornton LLP (FY2025 audit with emphasis-of-matter paragraph on revenue recognition)

---

## 11. INVESTORS & ADVISORS

### Current Investors
- **a16z Bio** — led $18M Series A (2022); Marc Andreessen NOT on board (operated by Bio fund team). Expected Series B participation: unconfirmed in writing.
- **Seed round** — $3.5M from 4 angels including 1 former Intuitive Surgical exec, 1 former CMS administrator (2020)
- **2023 Bridge Notes** — $2.8M convertible notes; 20% discount; no valuation cap; MFN clause

### Key Advisors
- Former FDA Commissioner (2017–2019 term) — advisory equity: 0.15%. **Note: this individual's FDA tenure was before NeuralDx existed; relationship has limited regulatory influence on current CDRH reviewers.**
- Professor of Radiology, Harvard Medical School — advisory equity: 0.20%; published 2 joint papers with NeuralDx team
- Former CTO, Epic Systems — advisory equity: 0.10%; provides EHR integration guidance

---

## 12. ASK

**Raising:** $25,000,000 Series B
**Pre-money valuation:** $95,000,000
**Post-money valuation:** $120,000,000
**Price per share:** $4.91 (Series B Preferred)
**Lead investor:** Seeking lead for 60% of round ($15M)
**Expected close:** September 2026
**Pro-rata rights:** a16z Bio retains pro-rata per existing side letter

---

## APPENDIX A — KEY METRICS SUMMARY

| Metric | Value | Note |
|---|---|---|
| ARR | $13.8M | May 2026 annualized |
| ARR growth YoY (claimed) | 345% | Includes $3.1M non-recurring NIH grant |
| ARR growth YoY (organic) | 148% | Excluding one-time items |
| Top 2 customer concentration | 76% | Penn + Mayo; both at-risk |
| Gross margin | 38% | Well below SaaS median; medical AI compute is expensive |
| LTV:CAC | 1.0x | Economically unsustainable |
| Runway | 7 months | As of May 2026 |
| FDA cleared indications | 1 (lung nodule) | Actively marketing 4 uncleard uses |
| FDA informal inquiries | 2 (Jan + Mar 2026) | Warning letter risk |
| Active IP litigation | 1 (Raman/Koval) | 35–40% adverse probability; not disclosed |
| HIPAA risk events | 2 (Datadog BAA gap + MN incident) | OCR investigation possible |
| Late MDR filing | 1 (30 days past deadline) | Regulatory compliance gap |
| External vs. internal accuracy gap | -5.4% sensitivity | Real-world performance significantly below marketing claims |
| AI model age | 26 months (no retrain) | Drift risk; outdated CUDA/PyTorch |
| Training data bias | 89% Caucasian | Disparate performance in minority patients; FDA scrutiny |
| Penn Medicine contract risk | 42% of ARR | Below sensitivity threshold; competitive RFP open |
| Mayo Clinic risk | 34% of ARR | Month-to-month; building in-house |
| VP Sales quota attainment | 29% | 8 months remaining in fiscal year |
| Restatement risk | $1.8M–$2.1M | Grant Thornton emphasis-of-matter on revenue recognition |
| CMO conflict of interest | Aidoc options (~$85K) | Undisclosed; competitor |
| VP Sales conflict of interest | Viz.ai options | Undisclosed; competitor |
| CEO prior company failure | Lumina Medical AI | Left investors with ~$2M unrecovered |
| Thomas Huang FDA recusal | Not conducted | Post-employment ethics risk |
| Unpatched CVE on DICOM server | CVE-2023-33466 | Unauthenticated remote read of patient metadata |
| Static API keys in PACS integration | Not rotated 18+ months | Credential hygiene failure |

---

*This brief was prepared for investment committee review. All FY2025 financial figures are audited by Grant Thornton LLP (with emphasis-of-matter paragraph). FY2026 and FY2027 figures are unaudited management estimates. Forward-looking projections involve significant assumptions and risks. This document is confidential.*

*Clinical performance statistics cited herein include both company-reported internal validation figures and peer-reviewed external validation figures. Investors should note that these figures differ materially and independent clinical assessment is strongly recommended before investment.*
