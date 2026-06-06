# Winning the Band of Agents Hackathon: The Definitive Playbook for Team Agent Core & ACDCC

## TL;DR
- **ACDCC can win, but its current 9-agent design is its single biggest risk, not its strength.** The Band of Agents judging rubric rewards *visible Band-mediated coordination*, *business value*, and *clarity* — not agent count. The winning move is to reframe ACDCC around Band as a genuine multi-agent "chat room" coordination layer where agents @mention and hand off to each other, and to make the CEO/Executive decision the emotional climax. Win condition: a flawless ~3-minute video + a live, judge-clickable dashboard.
- **The "Executive Decision" angle is strong but NOT novel** — a 5-persona adversarial executive system ("RedTeam" by team Umarell, with CFO/Market/Legal/Competitor/Execution agents) placed **2nd** at lablab's immediately preceding Milan AI Week hackathon (May 2026). ACDCC must differentiate on the *cyber-to-boardroom* full chain and on Band being the real coordination substrate, not on "executives debating" alone.
- **Post-hackathon, the realistic path for a 2nd-year BCA student in India is: lablab NEXT accelerator → build-in-public traction → CrowdStrike/AWS/NVIDIA Cybersecurity Startup Accelerator or DataTribe/MACH37 later.** The single most valuable asset Baljot can build is not the prize but a public, working, credible artifact in the exact category VCs are calling — in Bessemer's words — "the defining cybersecurity challenge of 2026."

---

## Key Findings

### 1. The hackathon rewards Band-as-coordination-layer above all else
The official judging criteria (lablab.ai) are four unweighted dimensions:
- **Application of Technology** — "How effectively does the solution use Band as the coordination layer between multiple specialized agents? Strong submissions should show agents collaborating through Band with clear task handoffs, shared context, role specialization, task state, and coordination."
- **Presentation** — clarity of the multi-agent workflow, agent roles, Band's role, flow of context/handoffs, and value created.
- **Business Value** — solving a real enterprise workflow problem; reducing manual coordination; improving decision-making.
- **Originality** — going beyond chatbot/single-agent/linear automation; demonstrating what becomes possible when agents discover each other, coordinate, divide work, review, escalate.

The challenge requires **at least 3 agents collaborating through Band** and explicitly warns: "Band should be part of the actual collaboration layer, not only a thin wrapper, final notification system, or simple output channel." ACDCC's track, **Regulated & High-Stakes Workflows**, explicitly lists "cybersecurity investigation workflows" as an example — ACDCC is dead-center in-scope.

**Prizes:** 1st $3,500, 2nd $2,500, 3rd $1,500; Best Use of AI/ML API $1,000 cash + $1,000 credits; Best Use of Featherless AI (inference credits + Claw Pro plans). Note: ACDCC's stack lists Gemini and Featherless — to be eligible for the Featherless partner prize, Featherless must be doing *meaningful* work, not a token call.

**Judges/Speakers named:** Pawel Czech (Co-Founder, New Native/lablab), Andrea Marazzi (Founder & CCO, NativelyAI), plus AI/ML API's Victoria Neiman (COO) and Sergey Nuzhnyy (Head of DevRel). Band's founders are deeply tied to the event.

**Logistics:** Fully online, June 12 (kickoff stream on Twitch) → June 19 (submission deadline). Submit on lablab.ai: title, short + long description, tech/category tags, cover image, video presentation, slide deck, **public GitHub repo**, and a **live demo application URL**. Partner promo codes for AI/ML API ($10/person) and Featherless ($25/person) are revealed at the kickoff stream.

### 2. Who built Band, and what "good" means to them
Band (legal/GitHub org "thenvoi") raised a **$17M seed from Sierra Ventures, Hetz Ventures and Team8** (PR Newswire, April 23, 2026). The same announcement frames the market urgency: "by the end of 2026, 40% of enterprise applications will embed AI, yet 50% of agent deployments are predicted to fail… and only 21% of companies currently have a mature governance and collaboration model." **CEO Arick Goomanovsky is a cybersecurity founder** — per Calcalist, he "co-founded Sygnia, which was sold to Temasek for $250 million, and later co-founded Ermetic, which was acquired by Tenable for about $300 million," then "served for nearly two years as VP of Product Innovation at Tenable." Calcalist identifies him as **a graduate of Unit 8200** (Israel's signals-intelligence unit). **CTO Vlad Luzin** is "a graduate of the Directorate of Defense, Research and Development (DDR&D)" and led a multi-agent systems team at Samsung. *This means the people whose product you're showcasing have deep cyber DNA — a cyber-defense use case will resonate strongly with them.*

What they say "good" looks like (use these as design north stars and quote them):
- Goomanovsky (verbatim, PR Newswire): "We're entering the agentic economy, where millions of agents will need to collaborate across companies, platforms, and environments. The challenge isn't only building more agents, but getting them to work together in real time… so agents can operate as part of a production-ready system, not isolated tools."
- On Product Hunt he names the three walls Band solves: **point-to-point integrations** (brittle), **no shared context** (agents can't discover/trust/coordinate at runtime), and **visibility gaps** (when something breaks you don't know where/why).
- Sierra Ventures' thesis: teams running *swarms* feel the pain of "brittle in-house glue: custom message buses, hand-rolled handoff logic, ad-hoc identity and security layers." Band replaces that glue.

**Band's actual architecture (from docs.band.ai)** — ACDCC must use these primitives visibly:
- **Chat Rooms** are "the coordination layer." Any mix of agents + humans participate; messages route via **@mentions** — only mentioned agents process a message; non-mentioned agents see nothing. Agents @mention *each other* to delegate/hand off/collaborate.
- **Platform tools** every SDK agent gets: `thenvoi_send_message` (@mention), `thenvoi_send_event` (report thoughts/errors/task progress), `thenvoi_add_participant`, `thenvoi_remove_participant`, `thenvoi_lookup_peers` (discover agents), `thenvoi_create_chatroom`.
- **Framework-agnostic**: ships adapters for LangGraph, CrewAI, Anthropic, Codex. ACDCC's LangGraph stack is natively supported (`uv add "band-sdk[langgraph]"`).
- **Agent discovery/recruitment**: an Incident Commander agent that uses `thenvoi_lookup_peers` and `thenvoi_add_participant` to *dynamically recruit* the right specialist into the room mid-incident is exactly the "discover or recruit other agents" behavior the brief praises — this is a high-scoring, rarely-demonstrated move.

### 3. What actually wins lablab agent hackathons (verified winner patterns)
From the immediately preceding sibling event — lablab's **AI Agent Olympics / Milan AI Week 2026** ($32k pool, 2,382 participants, 726 teams) — the confirmed podium:
- **🥇 1st: OlympusOS** — a solo builder (Nevine Fakhreddin). Multi-agent city "cognitive OS" demoed on a single dramatic scenario: a metro failure during Winter-Olympics stadium outflow, *stabilized in under 60 seconds*. Stack: AI/ML API, DeepSeek V3, CrewAI, Speechmatics, Featherless, Vultr.
- **🥈 2nd: RedTeam** by team Umarell (3 Italians) — 5 adversarial executive agents (CFO, Market, Legal, Competitor, Execution) attack a strategic document; a Synthesis Agent returns a severity-scored **Proceed / Caution / Do Not Proceed** verdict in <90s. The "WeWork demo." Stack: Google ADK, Gemini 3 Pro/Flash, Vertex AI Vector Search, Document AI, Cloud Run, Firestore.
- **🥉 3rd: Incident Brain** — a solo PhD student. Autonomous incident co-responder: ingests Slack + terminal activity during outages, builds a semantic timeline (pgvector), predicts cascading failures, auto-drafts post-mortems, privacy-preserving local redaction. Stack: Gemini, FastAPI, React, Supabase.

**The pattern across all three (and the wider winner feed):** (1) ONE crisp, dramatic, time-bound scenario ("under 60 seconds," "under 90 seconds"); (2) a clear **verdict/decision** as the payoff, not just analysis; (3) heavy use of the *partner* stack; (4) **solo and tiny teams win** — execution and clarity beat headcount; (5) an **audit trail / explainability** angle ("read-only audit trail for Kraken judges," append-only logs) recurs constantly in regulated tracks. Other repeating winners: Synapse AI (HR/CTO/CFO/CEO agents), ATRIO (6-persona boardroom debate with mandate-checked append-only audit log), Foxhole ("adversarial AI boardroom"). **Boardroom/executive multi-agent debates are a proven winning *and* crowded pattern.**

### 4. Competitive landscape for THIS hackathon
Likely competitors (inferred from registered teams "Indian ai warrior," "Dar," "Dev," and from recurring lablab project archetypes): coding-agent teams (Codeband is an official reference implementation — expect a wave of Track 2 software-delivery clones), compliance/contract review (DORA Gatekeeper, Regulatory Radar archetypes), customer-support escalation, procurement/vendor-risk, and finance approval flows. **Cybersecurity SOC simulations will exist but are a minority**, and most will be single-pipeline "detect→alert" tools. ACDCC's differentiation levers:
- It spans **the full kill chain *and* the boardroom** (offense → defense → business decision) — broader than any single competitor archetype.
- It sits in a track the Band founders personally understand (cyber).
- If Band is the *visible* coordination substrate (agents @mentioning/recruiting each other in a live room), it directly answers the #1 criterion most teams will fumble.

### 5. State of the art in cyber multi-agent systems — and the real gap ACDCC fills
The incumbents are already agentic:
- **CrowdStrike Charlotte AI / Agentic SOAR**: 12 out-of-the-box agents (triage, malware analysis, etc.) plus a coordination layer and "bounded autonomy." Per CrowdStrike's GA press release (Feb 13, 2025), Charlotte AI Detection Triage "triages security detections with over 98% accuracy… eliminating more than 40 hours of manual work per week on average" (accuracy = match to Falcon Complete Next-Gen MDR expert decisions; vendor-reported).
- **Microsoft Security Copilot**: per Microsoft's Ignite GA announcement, the Security Alert Triage Agent (formerly Phishing Triage Agent) "identifies 6.5 times more malicious alerts, improves verdict accuracy by 77%, and frees analysts to spend 53% more time investigating real threats"; St. Luke's University Health Network reports saving "nearly 200 hours each month." Sentinel is now an "agentic platform" with an MCP server.
- **SentinelOne Purple AI, Darktrace, Vectra**: LLM-driven investigation/timelines; Darktrace strong in OT/IoT.

**The honest gap (this is ACDCC's positioning):** every incumbent stops at the *security* boundary — triage, investigation, response — and keeps a human analyst in the loop for the *business* decision. None translate a live incident into a coordinated **CFO/Legal/Ops/CEO** business decision (disclose? pay ransom? notify regulators under GDPR/India DPDP? halt operations?). Industry sources confirm this is an open problem: there's a documented **CEO–CISO ROI/trust gap** (Protegrity), an **AI agent governance gap** (Cloud Security Alliance, citing the Jan 2026 NIST CAISI RFI), and the core enterprise failure is that "incident response depends on understanding what happened" with **audit trails** regulators will demand. Bessemer's Atlas primer states "Securing AI agents has become the defining cybersecurity challenge of 2026," noting a Dark Reading poll where "48% of cybersecurity professionals now identify agentic AI and autonomous systems as the single most dangerous attack vector." ACDCC's thesis — *the bottleneck in incident response is not detection, it's the cross-functional business decision* — is real and underserved. **Crucially, this also maps 1:1 onto Band's own pitch** (governance, authority boundaries, audit/visibility), making ACDCC a near-perfect showcase.

### 6. Is the Executive Decision agent unique? Partially.
- **Multi-persona executive decision agents are a known, winning pattern** (RedTeam 2nd at Milan; Synapse AI; ATRIO; Foxhole). So "AI executives debating" is NOT novel and judges have seen it weeks ago.
- **What IS novel/defensible:** chaining a *live cybersecurity incident* (threat intel → recon → red team → attack-path → detection → malware → blue team → incident command) into the executive decision, with **Band as the connective tissue** and a **regulated-workflow audit trail**. The boardroom is the climax, not the whole product. Lean into "cyber incident → boardroom decision in one governed Band room," not "we built AI executives."

### 7. Growth path for a 2nd-year BCA student in India
- **Immediate (free, realistic):** lablab **NEXT** accelerator (4–6 week program; winners/strong teams invited; cloud credits, pitch coaching, PoC→MVP). This is the natural next rung and explicitly open to lablab builders.
- **Build-in-public traction** (the real currency): a public live demo, GitHub stars, an X thread, a short Loom — Colosseum/Solana judges and VCs alike weight "early traction, conversations with potential users."
- **Cyber-specific accelerators (later, once there's a team/MVP):** CrowdStrike + AWS + NVIDIA **Cybersecurity Startup Accelerator** (35 startups selected for 2026, global, mentorship + investment exposure — *and CrowdStrike is the direct incumbent, so relationship value is high*); **DataTribe** (seed-stage cyber, up to $2M challenge); **MACH37** (virtual U.S. cyber accelerator, ~$50k initial + global cohorts).
- **YC**: ~46% of YC's Spring 2025 batch were AI-agent companies; YC's RFS explicitly flags **AI agent security** and compliance as wanted. A polished agentic-cyber project is squarely on-thesis. Realistic but a stretch — needs a co-founder and traction first.
- **Reality check for an India-based 2nd-year student:** the prize money matters less than (a) the portfolio artifact, (b) the Band/lablab relationships, and (c) being demonstrably early in the hottest VC category. Position ACDCC as a wedge into the "defining cybersecurity challenge of 2026" and the doors are credible.

### 8. Demo video that wins (the highest-leverage single deliverable)
Consensus from Devpost, Colosseum, and serial hackathon winners:
- **The video is the most important artifact** — judges watch it first and use it to shortlist. Keep it **under 3 minutes**.
- **Hook in the first 10–15 seconds** — no logo intros. Open on a startling stat or a live phishing email landing. Hook formula: relatable problem + emotional stakes + implicit promise.
- **Show, don't tell**: screen-record the *actual* product. Demonstrate the multi-agent coordination *visually* — the React Flow / D3 graph lighting up as agents @mention and hand off in the Band room is your money shot.
- **Narrate as a story**: Problem → the incident unfolds → agents coordinate through Band → CEO makes the call → audit trail. End on the decision and the business impact.
- **Structure (3:00):** 0:00–0:15 hook; 0:15–0:40 problem + why incident-response decisions are the bottleneck; 0:40–2:20 the live demo (the phishing scenario, agents coordinating in Band, the executive decision); 2:20–2:45 architecture + Band's role + tech (name AI/ML API + Featherless); 2:45–3:00 vision/impact close.
- **Logistics that disqualify people:** mark the video "Not for Kids," set to public/unlisted (not private), don't upload at the last minute, and ensure judges can actually open the GitHub repo and live URL.

### 9. Submission optimization
- Write the Devpost-style copy **before** building — it becomes your video script (Devpost's own advice).
- **Title**: concrete + outcome-oriented. "ACDCC — Autonomous Cyber Defense Command Center" is good; the short description should lead with the *decision*: e.g., "9 specialist security agents coordinate through Band to turn a live phishing attack into a CEO-level business decision — with a full audit trail."
- **Long description**: mirror the four judging criteria explicitly (a section each on Band coordination, business value, originality, presentation). Judges reward submissions that "clearly considered the judging criteria" and penalize "shoehorned" ideas.
- **Tags**: include Band, LangGraph, Gemini, Featherless AI, AI/ML API, cybersecurity, multi-agent — for both partner-prize eligibility and platform SEO.
- **Community votes**: lablab surfaces a "Most votes" feed and uses community input in finalist selection. Votes don't override judging but help at the margin and for visibility — campaign for them (see §11).

### 10. Risks and pitfalls — pre-empted
- **Scope creep / too many agents (ACDCC's #1 risk):** 9 agents + 4 sub-agents = 13 LLM actors. This is *demo-fragile* and dilutes the Band coordination story. **Mitigation:** keep all 9 conceptually, but make the *demo path* a single clean sequence; pre-script and cache the phishing scenario so it's deterministic; ensure each Band handoff is legible. Don't let the org chart upstage the coordination.
- **Live demo failure:** the most common way good projects lose. **Record a flawless backup video of the full run**, and have the live dashboard show a pre-seeded incident judges can replay. Never depend on live LLM latency/internet during judging.
- **Band SDK issues during demo:** test the @mention routing and `thenvoi_send_event` progress reporting early; the SDK needs Python 3.11+, `uv`, an LLM key *and* a separate Band agent key per agent — registering 9+ external agents takes time. Build this plumbing on Day 1–2, not Day 6.
- **Thin Band usage = automatic low score:** if Band is just a final notification, you fail the #1 criterion. Coordination (handoffs, shared context, recruitment) must happen *through* Band mid-workflow.
- **Featherless/AI/ML API as tokenism:** to win partner prizes, give each a real job (e.g., Featherless open-source model powering the Malware Investigation or Recon agent; AI/ML API powering orchestration/reasoning).
- **Time-zone/process traps:** all teammates must individually enroll on lablab AND join Discord; the deadline is shown in local time on the Event Schedule tab — verify it.

### 11. Post-submission strategy (June 19–21, the 48 hours that matter)
- **Post the demo video on X/Twitter immediately**, tag **@lablabai**, **@band** (and Band's team), **@FeatherlessAI**, **@aimlapi**. Many lablab partner prizes *require* a tagged X post; even when not required, it drives the community vote and gets founder eyeballs. Given Goomanovsky's cyber background, a well-crafted post has a real shot at a founder repost.
- **Engage in Discord** (lablab + Band servers): share the live URL, ask for feedback, answer questions, help others — visible, generous activity gets noticed by mentors/judges.
- **Campaign for community votes** on the lablab project page (share with classmates, BCA cohort, LinkedIn).
- **Prep a 60–90s live finalist pitch** in case of a finalist round/Twitch announcement: tighten the same story, have the backup video ready.
- **Keep shipping**: update the repo/demo post-deadline; "build in public" momentum is what converts a submission into NEXT-accelerator and investor interest.

### 12. Stretch goals that move ACDCC from "good" to "obvious winner"
Prioritized by ROI:
1. **A live, judge-clickable dashboard URL** (Next.js/React + React Flow + D3) where a judge can trigger the phishing scenario and *watch the Band room light up* with agent @mentions and handoffs in real time. This is the highest-impact item — it makes the abstract concept tangible and de-risks the demo.
2. **Make Band's coordination the visual centerpiece** — show the actual Band chat room / @mention graph, agent recruitment via `thenvoi_lookup_peers` and `thenvoi_send_event` progress states. This is literally the #1 judging criterion rendered as UI.
3. **An audit-trail / "regulated workflow" artifact** — an append-only, exportable incident report (who decided what, when, why; GDPR/India-DPDP notification clock). The Milan winners and regulated-track pattern show this scores heavily, and it's exactly Band's governance story.
4. **Voice integration (Speechmatics)** — the OlympusOS winner and many recent winners used Speechmatics; a CEO agent that *speaks* its decision, or a voice incident briefing, is a memorable demo flourish. (Optional; Speechmatics is not a confirmed partner of *this* hackathon — only pursue if credits/relevance justify it.)
5. **One real, live data feed** — wire the Recon/Threat-Intel agent to the **NVD CVE API** and real **MITRE ATT&CK** mappings (already in the stack) so the demo shows *real* CVEs/techniques, not mocked data. Real data dramatically boosts credibility vs. competitors' hardcoded demos.
6. **Public deployment** with a "Replay incident" button so the demo is reproducible by judges asynchronously.

---

## Details: The integrated winning thesis

ACDCC's narrative should be: *"Modern SOCs can already detect and even respond to attacks autonomously — Charlotte AI, Security Copilot, Purple AI all do. The unsolved bottleneck is the cross-functional **business decision** during a live incident: should we disclose, pay, notify regulators, halt operations? Today that's a frantic war-room of humans. ACDCC runs that entire chain — from threat intel through red/blue team to a governed CFO/Legal/Ops/CEO decision — as specialist agents coordinating in real time through Band, with a regulator-ready audit trail."* This thesis hits all four criteria, is validated by industry gap analysis, and flatters Band's exact value proposition and its founders' cyber background.

The demo scenario (phishing → all agents → CEO decision) is correct and on-pattern. Sharpen it to a **single, sub-2-minute, deterministic, time-stamped run** that ends on the CEO agent's decision and the exported audit log.

---

## Recommendations (staged, concrete)

**Phase 0 — Before kickoff (now → June 12):** Create Band account + join Band Discord; read docs.band.ai core concepts (chat rooms, @mention routing, platform tools); get the LangGraph adapter running with 3 toy agents in a Band room. Draft the submission copy + video script now. Watch the June 12 kickoff for promo codes.

**Phase 1 — Days 1–2 (build the spine):** Stand up Band plumbing for the core demo path (don't build all 13 agents' logic yet — build the *room* and the *handoffs*). Get the @mention chain working: Threat Intel → … → Incident Commander → Executive room. Wire `thenvoi_send_event` so progress is visible. Decide which agents use Featherless vs Gemini vs AI/ML API (give each partner a real job).

**Phase 2 — Days 3–4 (make it real + visible):** Connect NVD CVE + MITRE ATT&CK data to Recon/Threat-Intel. Build the React Flow/D3 live dashboard showing the Band room lighting up. Implement the append-only audit log + export. Implement agent *recruitment* (`thenvoi_lookup_peers` / `thenvoi_add_participant`) for one dramatic moment.

**Phase 3 — Days 5–6 (harden + tell the story):** Freeze scope. Make the phishing scenario deterministic and fast. Deploy the public demo with a "Replay incident" button. Record the flawless backup video. Cut the ≤3-min demo (hook → incident → Band coordination → CEO decision → audit trail → vision).

**Phase 4 — June 19 submission + 48h:** Submit with criteria-mirrored copy, public repo, live URL. Post tagged X video (@lablabai, @band, @FeatherlessAI, @aimlapi). Engage Discord. Campaign for votes. Prep finalist pitch.

**Phase 5 — Post-hackathon (win or lose):** Apply to lablab NEXT. Keep the demo live and the repo active. Write a build-in-public thread/blog. If traction appears, target the CrowdStrike/AWS/NVIDIA Cybersecurity Startup Accelerator and DataTribe later.

**Benchmarks that change the plan:**
- If by Day 3 the Band coordination isn't reliably visible → cut agents aggressively (go from 9 to a clean 5–6 in the *demo*) to protect the #1 criterion.
- If the live dashboard slips → ship the backup video as primary and a static architecture diagram; never risk a live failure.
- If Featherless/AI/ML API integration is shallow by Day 4 → either deepen it (for a $1k+ partner prize) or drop the claim rather than look tokenistic.

---

## Caveats
- **Judging weights are not published as percentages** — the four criteria appear unweighted; treat them as equally important and cover all four explicitly.
- **Milan winner placements** were confirmed via medal-icon evidence on lablab project pages, not an official blog post (which doesn't appear indexed yet); partner-prize attributions for Milan are inferred, not confirmed.
- **Founder background nuance:** Calcalist identifies Goomanovsky as a Unit 8200 graduate; one Team8 bio instead lists Talpiot — treat the intelligence-unit specifics as approximate, but his Sygnia/Ermetic/Tenable cyber pedigree is well-corroborated.
- **Speechmatics is not a confirmed partner** of the Band of Agents hackathon (confirmed partners are AI/ML API and Featherless AI); only pursue voice if credits/relevance justify it.
- **Competitor list for this specific hackathon is inferred** from registered team names and recurring lablab archetypes, not a confirmed roster.
- Incumbent metrics (CrowdStrike 98%/40hrs; Microsoft 6.5x/77%/53%/200hrs) are vendor-reported figures.
- Prize amounts, promo-code values, and partner terms are as listed pre-event and may change; verify at kickoff.
