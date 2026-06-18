# Band Swap Procedure — Jun 12, 2026 Kickoff

## Time budget: 90 minutes from API key receipt

### Step 1: Get credentials (5 min)
1. Login to band.ai
2. Create 9 Band agents — one per ARGUS agent
3. Name them exactly: Threat-Intel, Recon, Red-Team, Attack-Path,
   Detection, Malware-Investigation, Blue-Team, Incident-Commander, Executive-Decision
4. Copy agent_id and api_key for each into agent_config.yaml

### Step 2: Create 9 Band rooms (10 min)
Create rooms with these exact names:
- threat-intel-room
- recon-room
- redteam-room
- attack-path-room
- detection-room
- malware-room
- blueteam-room
- incident-command-room
- executive-room

### Step 3: Flip the switch (1 min)
In .env:
```
BAND_MOCK=false
BAND_API_KEY=<your-key>
```

### Step 4: Test (30 min)
```bash
python run.py
# In another terminal:
curl -X POST http://localhost:8000/api/trigger-attack
# Watch Band dashboard — should see 9 agents lighting up
```

### Step 5: Verify chain fires (15 min)
Watch Band rooms for:
- Threat Intel → incident-command-room (report)
- Incident Commander → recon-room + detection-room (parallel)
- Recon + Detection → incident-command-room (reports)
- Incident Commander → redteam-room + malware-room (parallel)
- Red Team + Malware → incident-command-room (reports)
- Incident Commander → attack-path-room
- Attack Path → incident-command-room (risk score 87)
- Incident Commander → blueteam-room + executive-room (PARALLEL)
- Blue Team + Executive → incident-command-room (final reports)

## Implementation note (real-mode wiring)
`core/base_agent.py::compile_agent()` already contains the real-mode branch that
builds a `thenvoi` `LangGraphAdapter` + `Agent` when `is_mock_mode()` is False. Before
flipping the switch, run a quick `python -c "import thenvoi"` to confirm the SDK is
installed and the import path (`from thenvoi.adapters import LangGraphAdapter`) matches
the version you `pip install`ed. If the SDK signature differs, adjust only the
`else:` block in `compile_agent()` — the mock path and all 9 agent prompts stay unchanged.
