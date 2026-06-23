# FUSION — Hackathon Strategy & Retrospective Playbook

## TL;DR
- **The Pivot from ARGUS/ACDCC to FUSION (VERDICT) was our winning strategic move.** Originally, the project was designed as a 9-agent autonomous security operations center (ACDCC). However, a 9-agent setup presented severe scope risk, high API latency, and reduced presentation clarity. By pivoting to a 5-partner VC Investment Committee swarm (FUSION), we streamlined the codebase, highlighted the inter-agent boardroom debate, and delivered an easily understandable business outcome in under 5 minutes.
- **Why this pivot won**:
  - **High Business Stakes**: Evaluating a $10M Series A startup investment is universally understood and carries clear financial and legal trade-offs.
  - **Legible Boardroom Debates**: Instead of a linear cybersecurity alert pipeline, FUSION showcases multi-agent coordination via Band where partners actively disagree (e.g. high revenue growth vs declining sector) and the Managing Partner resolves the dispute.
  - **Resilience**: A simplified 5-agent graph backed by deterministic calculations in `diligence_engine.py` runs with high speed, low cost, and clear audit logging.

---

## 1. Key Hackathon Criteria Met

The Band of Agents Hackathon (lablab.ai, June 2026) evaluated four core dimensions:

### 📡 Application of Technology (Band Coordination)
- Band is not a thin wrapper or notification logger; it is the **runtime coordination substrate**.
- The Managing Partner briefs 4 partners simultaneously in their respective rooms via `@mentions`.
- Partners perform audits in parallel and post structured completion cards back to the `managing-partner-room` to trigger the boardroom debate.

### 💼 Business Value
- Human due diligence on Series A startup investments is historically slow (weeks to months) and costly ($100k–$500k in fees).
- FUSION automates the retrieval, verification, and cross-checking of data rooms, producing a publication-ready PDF audit memo in under 5 minutes.

### 🎭 Originality
- Most multi-agent systems are linear pipelines or simple chat routing.
- FUSION implements an **adversarial boardroom debate round** where agents argue trade-offs and resolve contradictions before outputting the final verdict.

---

## 2. Competitive Landscape & Positioning

In hackathons, the most common submissions in the high-stakes track are:
- Basic coding assistants (e.g., Codeband copies).
- Contract reviewers / regulatory compliance compliance checkers.
- Standard threat detectors (like the original ARGUS concept).

FUSION stands out because it brings **financial, legal, technical, and market perspectives together in one visual dashboard**. While other teams focus solely on technical metrics, FUSION bridges the gap between raw data analysis and high-level executive decision-making.

---

## 3. Retrospective: Pivoting from Cyber SOC to VC Swarm

During development, we compared the two project paradigms to optimize our submission:

| Dimension | AI SOC (ARGUS / ACDCC) | AI VC Boardroom (FUSION / VERDICT) |
| :--- | :--- | :--- |
| **Complexity** | 9-agent pipeline + sub-agents (High failure risk) | 5-partner boardroom graph (Highly stable) |
| **Presentation** | Complex terminal inputs & firewall logs | Relatable pitch decks, risk gauges, and PDF downloads |
| **Band Integration** | Sequential notifications | Real-time boardroom debate over shared room channels |
| **Business Impact** | Time saved on triage alerts | $10M capital allocation decision |

By choosing FUSION, we ensured a flawless 3-minute video presentation and a judge-clickable live URL.

---

## 4. Key Architectural Trade-offs Made

1. **Deterministic Scoring vs. LLM Hallucinations**: We chose to compute the core risk score, coverage, and verdict confidence inside a deterministic python engine (`diligence_engine.py`) rather than letting the LLM compute it. The partner LLMs handle the persona-based narration and debate, but the numbers remain mathematically sound and grounded in the data room.
2. **Resilient Local Mock-LLM**: We built an OpenAI-compatible mock completion server inside `api/main.py`. If cloud APIs fail or encounter rate limits, the swarm degrades to mock mode seamlessly, ensuring judges can run the demo end-to-end without disruption.

---

*FUSION — Five agents. One boardroom. No bad investments.*
