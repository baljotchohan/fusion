# Submission Checklist — ARGUS (Band of Agents Hackathon)

**Deadline:** Jun 19, 2026 3:00 PM UTC (8:30 PM IST)

## Pre-Submission (Jun 18–19)

- [ ] Video recorded (3 min, shows agent handoffs on Band)
- [ ] Slides done (8–10 slides, exported as PDF)
- [ ] GitHub repo cleaned:
  - [ ] No API keys in `.env.example`
  - [ ] `.gitignore` blocks `node_modules/`, `venv/`, `argus_memory/`, `agent_config.yaml`
  - [ ] README updated with live demo URL
  - [ ] Tag release: `v1.0.0-hackathon`
- [ ] Backend deployed on Hugging Face Spaces
  - [ ] Live URL: `https://baljot07-fusion.hf.space`
  - [ ] Test `/api/v1/chat` endpoint
  - [ ] Environment vars set in Hugging Face Space settings:
        `GOOGLE_API_KEY`, `FEATHERLESS_API_KEY`, `GROQ_API_KEY`, `AIMLAPI_KEY`,
        `BAND_API_KEY`, `BAND_MOCK=false`, `GITHUB_TOKEN`, `ALLOWED_ORIGINS`
- [ ] Frontend deployed on Vercel
  - [ ] Live URL: `https://argus-frontend.vercel.app`
  - [ ] `NEXT_PUBLIC_API_URL` + `NEXT_PUBLIC_WS_URL` point at Hugging Face Spaces
  - [ ] Chat works end-to-end
  - [ ] Dev mode toggle works
- [ ] Band setup complete
  - [ ] 9 rooms created via `python scripts/setup_band_rooms.py`
  - [ ] Incident Commander can @mention all 8 agents
  - [ ] Live incident shows agent handoffs in band.ai dashboard
- [ ] Memory graph verified
  - [ ] `argus_memory/` in `.gitignore`
  - [ ] Shared incident graph logs findings (run two incidents, check `/api/v1/memory/stats`)
  - [ ] Agents query memory before acting (learned defense recipes populate)
- [ ] MCP server verified (`python mcp_server.py` + Claude Desktop config)

## Submission Form (lablab.ai)

**Title (≤50 chars):**

```
ARGUS: 9 Agents. All Seeing. Never Sleeps.
```

**Short description (≤255 chars):**

```
Open-source AI SOC team orchestration using Band coordination and shared
memory. 9 specialized agents hand off tasks via Band @mentions for
autonomous 24/7 cybersecurity operations — with REST API, MCP server,
and real GitHub scanning.
```

**Long description (≥100 words):**

```
ARGUS is an embeddable cybersecurity agent orchestration system where 9
specialized AI agents coordinate through Band to automate threat detection,
response, and executive decision-making.

Key innovation: a shared memory graph (Graphify) across all agents. Every
incident is logged; every defense learned. Run #2 of the same attack? Agents
recognize the pattern and respond faster.

Band is the real coordination layer. Agents hand off via @mentions with full
context. Judges verify by checking the band.ai dashboard directly — real
multi-agent workflow, not a thin wrapper.

Real connectors (GitHub secret scanning, Dependabot, NVD CVE, MITRE ATT&CK)
prove this is a production-grade security tool, not a simulator. BYO LLM keys
(Gemini, Featherless, Groq, AI/ML API). MIT open-source. Deployable in
minutes. An MCP server lets any AI app recruit the team as tools.

Use case: SMBs can't afford a $500k/year SOC team. ARGUS plugs into their
infrastructure and runs 24/7. Enterprise security at startup cost.
```

**Tags:**

```
cybersecurity, multi-agent, band-coordination, security-operations,
open-source, incident-response, llm-agents, shared-memory
```

**Other fields:**

- Cover image: War Room dashboard screenshot (agent cards + threat gauge)
- Video: 3-min demo (YouTube link)
- Slides: PDF (8–10 slides)
- GitHub: https://github.com/baljotchohan/argus (public, MIT)
- Demo: https://argus-frontend.vercel.app (live "SIMULATE ATTACK" button)
- Track: Regulated & High-Stakes Workflows

## Video Script (3 min)

```
[0s]  Dashboard loading. "ARGUS: 9 agents. All seeing. Never sleeps."
[5s]  User types in Commander chat: "We got a phishing email."
[10s] Split screen: War Room left, band.ai rooms with @mentions right.
      "All 9 agents activate in parallel..."
[20s] Agents firing: Threat Intel CVEs -> Red Team kill chain ->
      Detection IoCs -> Blue Team containment -> Commander escalates.
[30s] Executive boardroom: CFO / Legal / Ops / CEO verdict.
[50s] War Room shows final decision + threat gauge.
[55s] Toggle DEV MODE — raw JSON event streams. "Devs see everything."
[60s] Run the SAME attack again — memory kicks in, faster response.
      "Agents that learn together."
[70s] MCP demo: Claude recruits ARGUS to scan a GitHub repo.
[80s] "Open source. Embeddable. Real connectors. Join the AI SOC revolution."
```

## Post-Submission (Jun 19)

- [ ] Tweet @lablabai @band_hq @FeatherlessAI with live demo URL
- [ ] Share on Reddit r/cybersecurity, r/OpenSourceProjects
- [ ] Discord: lablab.ai, Band, Anthropic communities
- [ ] Start build-in-public thread on X
