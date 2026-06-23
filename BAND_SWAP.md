# Band Swap Procedure — FUSION VC Committee Real Mode

This document outlines the procedure to swap the FUSION multi-agent system from local Mock Mode (`MockBandBus`) to production Real Mode (`RealBandBus` via the `thenvoi` SDK).

---

### Step 1: Create 5 Band External Agents (5 min)

1. Log in to your **band.ai** developer dashboard.
2. Create **5 External Agents** — one for each VC partner.
3. Name them exactly as follows to match the handles:
   - `managing-partner`
   - `financial-partner`
   - `legal-partner`
   - `technical-partner`
   - `market-partner`
4. Copy the `agent_id` and `api_key` for each agent and paste them into your local `agent_config.yaml` file:

```yaml
# agent_config.yaml
agents:
  managing_partner:
    agent_id: "your_managing_partner_agent_id"
    api_key: "your_managing_partner_api_key"
    room: "managing-partner-room"
  financial_partner:
    agent_id: "your_financial_partner_agent_id"
    api_key: "your_financial_partner_api_key"
    room: "finance-partner-room"
  ...
```

---

### Step 2: Set Up Band Rooms (10 min)

Run the automated setup script to register the 5 boardroom rooms on the Band platform:

```bash
python scripts/setup_band_rooms.py
```

This registers:
- `managing-partner-room` (monitored by Managing Partner)
- `finance-partner-room` (monitored by Financial Partner)
- `legal-partner-room` (monitored by Legal Partner)
- `tech-partner-room` (monitored by Technical Partner)
- `market-partner-room` (monitored by Market Partner)

---

### Step 3: Flip the Switch in `.env` (1 min)

Open your `.env` file and set the mode switches:

```bash
BAND_MOCK=false
BAND_API_KEY=your-developer-band-api-key
```

This disables `MockBandBus` and instructs the `BaseAgent` compiler in `core/base_agent.py` to instantiate the `thenvoi` `LangGraphAdapter` with your credentials.

---

### Step 4: Run & Test (15 min)

Start the FUSION server:

```bash
python run.py
```

In another terminal, trigger a new due diligence simulation:

```bash
curl -X POST "http://localhost:8000/api/trigger-deal?company=NovaPay%20Inc"
```

---

### Step 5: Verify the Band Swarm Event Flow (10 min)

Log in to the **band.ai** room explorer and verify the following flow of messages:

1. **Convene**: `@managing-partner` joins and posts the audit triggers in parallel:
   - `@baljotchohan23/financial-partner New deal in committee...` in the `finance-partner-room`.
   - `@baljotchohan23/legal-partner New deal in committee...` in the `legal-partner-room`.
   - ... and so on for tech and market partners.
2. **Auditing**: Each partner wakes up, reads its pitch section via the `load_deal_brief` tool, and posts its completed analysis back to `managing-partner-room` using a `@mention`:
   - `@managing-partner FINANCIAL ANALYSIS COMPLETE. Risk Score: 9.0/10...`
3. **Consensus & Verdict**: The Managing Partner collects all 4 completion reports, resolves any conflicts (e.g. high margins vs declining sector), and writes the final verdict card:
   - `DECISION: PASS` / `WEIGHTED SCORE: 9.3/10`.
4. **WebSocket Sync**: Ensure that every message sent on Band is successfully mirrored to the Next.js boardroom dashboard via the WebSocket event bridge.

---

*FUSION — Five agents. One boardroom. No bad investments.*
