# SolarGrid AI (SolarGrid Technologies Inc.)
## Series A Investment Proposal

### Executive Summary
SolarGrid Technologies Inc. develops an AI-powered smart grid optimization platform that helps municipal utility providers balance decentralized energy grids (solar, wind, batteries) in real-time. Our software decreases municipal grid instability events by 45% and improves energy utilization by 30%.

---

### Company Profile
* **Company Name:** SolarGrid Technologies Inc. (DBA SolarGrid AI)
* **Industry:** CleanTech / Smart Grid Utilities / Infrastructure SaaS
* **Stage:** Series A
* **Founded:** 2023
* **Headquarters:** Boulder, CO
* **Employees:** 18
* **Funding Goal:** $8,000,000 Series A at $32,000,000 post-money valuation

---

### 1. Financial Diligence
* **Annual Recurring Revenue (ARR):** $3,200,000
* **Year-over-Year Growth:** 180%
* **Gross Margin:** 58% (depressed due to custom hardware integrations and on-site calibration services)
* **Monthly Burn Rate:** $290,000
* **Runway:** 9 months of runway based on current cash on hand ($2.6M remaining from Seed round)
* **LTV to CAC Ratio:** 2.8x (CAC is high at $85,000 due to enterprise sales cycles to utility executives; LTV is $238,000)
* **Revenue Concentration:** 
  * **Boulder Municipal Utility (single client):** 72% of total ARR ($2.3M). 
  * **Remaining clients (3 smaller cooperatives):** 28% of ARR ($900k).
  * **Critical Risk:** The Boulder Municipal Utility contract is up for public renewal in November 2026. A change in city council leadership could trigger a rebidding process.

---

### 2. Legal & Regulatory Diligence
* **Patent Portfolio:** 
  * 1 Utility Patent granted (US12,345,678B1) covering "Decentralized Grid Balancing Node Control."
  * 3 Provisional Patents filed covering "AI-Driven Predictive Load Shifting Algorithms."
* **Active Litigation:**
  * **GridDynamics Corp v. SolarGrid Technologies Inc (Case No. 1:26-cv-00432):** Patent infringement lawsuit filed by competitor GridDynamics Corp in March 2026. They allege SolarGrid’s core algorithm infringes their patent #US10,987,654.
  * **Potential Damages Exposure:** Legal counsel estimates potential damages of $4,500,000 if GridDynamics prevails, representing over 55% of the requested Series A raise.
* **Regulatory Compliance:**
  * **FERC Order 2222:** Requires grids to allow distributed energy resource aggregators. SolarGrid claims compliance, but has not completed formal certification in the PJM and ERCOT regions.
  * **NERC CIP (Critical Infrastructure Protection):** Compliance is currently **incomplete**. SolarGrid is running pilot projects on critical municipal infrastructure without meeting NERC CIP Version 6 cybersecurity standards.
* **Data Security & Privacy:**
  * **SOC 2 Type II:** Not certified (process started, but halted due to engineering resource constraints).
  * **HIPAA/GDPR:** Not applicable (US utility infrastructure focus).

---

### 3. Technical & Product Diligence
* **Architecture:** Python/Django backend with a React web interface, communicating with edge sensors deployed at utility substations.
* **Tech Stack Currency:**
  * Django 3.2 (Reached End-of-Life April 2024 — currently running unsupported without security patches).
  * Python 3.8 (Reached End-of-Life October 2024).
* **Cybersecurity Posture:**
  * **Exposed Secrets:** System logs show database connection strings and an AWS root API key committed to the private git repository (discovered during a routine tech audit).
  * **Encryption:** API traffic uses HTTPS, but telemetry data from edge sensors to the central database is sent over unencrypted HTTP (port 80).
  * **Bus Factor:** The entire machine learning codebase is maintained and understood exclusively by the single Lead AI scientist (Co-founder), presenting high key-person risk.

---

### 4. Market & Defensibility Diligence
* **Total Addressable Market (TAM) Claim:** $120B global smart grid optimization market by 2032. (Source: bottom-up calculation based on $15,000 annual license per substation across 8,000 global utilities).
* **Competitive Landscape:**
  * **Funded Incumbents:** GridDynamics Corp (Series C, $45M raised), Enersolve Inc (acquired by Siemens).
  * **SolarGrid Defensibility Rating (Scale 1-5):**
    * *Data Moat:* 4/5 (Proprietary telemetry datasets collected from Boulder pilots)
    * *Network Effects:* 1/5 (No native network effects; utility deployments are isolated)
    * *Switching Costs:* 4/5 (High integration complexity makes replacing SolarGrid difficult once installed)
    * *Technology Advantage:* 3/5 (Standard deep reinforcement learning applied to grid physics)
    * *Defensibility Score:* 12 / 20
