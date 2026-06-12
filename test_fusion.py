"""
Fusion — Complete Test Suite
Run from repo root: python test_fusion.py
Tests every angle: env, data, imports, agents, API, chain, WebSocket, Band readiness.
"""

import os, sys, json, asyncio, time, traceback, subprocess, threading
from datetime import datetime

# ── Colour output ─────────────────────────────────────────────────────────────
GRN = "\033[92m"; RED = "\033[91m"; YLW = "\033[93m"
BLU = "\033[94m"; CYN = "\033[96m"; RST = "\033[0m"; BLD = "\033[1m"

PASS = f"{GRN}✅ PASS{RST}"
FAIL = f"{RED}❌ FAIL{RST}"
WARN = f"{YLW}⚠️  WARN{RST}"
INFO = f"{BLU}ℹ️  INFO{RST}"

results = {"pass": 0, "fail": 0, "warn": 0}

def ok(msg):
    results["pass"] += 1
    print(f"  {PASS}  {msg}")

def fail(msg, detail=""):
    results["fail"] += 1
    print(f"  {FAIL}  {msg}")
    if detail:
        print(f"         {RED}{detail}{RST}")

def warn(msg):
    results["warn"] += 1
    print(f"  {WARN}  {msg}")

def section(title):
    print(f"\n{BLD}{CYN}{'─'*60}{RST}")
    print(f"{BLD}{CYN}  {title}{RST}")
    print(f"{BLD}{CYN}{'─'*60}{RST}")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — FILE STRUCTURE
# ═════════════════════════════════════════════════════════════════════════════
section("1 / FILE STRUCTURE")

REQUIRED_FILES = [
    "run.py",
    "requirements.txt",
    "agent_config.example.yaml",
    "core/band_client.py",
    "core/base_agent.py",
    "core/event_bus.py",
    "core/mitre_lookup.py",
    "core/cve_lookup.py",
    "api/main.py",
    "agents/threat_intel.py",
    "agents/recon.py",
    "agents/red_team.py",
    "agents/attack_path.py",
    "agents/detection.py",
    "agents/malware.py",
    "agents/blue_team.py",
    "agents/incident_commander.py",
    "agents/executive_decision.py",
    "data/company.json",
    "data/phishing_email.json",
    "data/email_logs.json",
    "data/network_map.json",
    "frontend/pages/index.tsx",
    "frontend/package.json",
    "frontend/hooks/useAgentWebSocket.ts",
    "frontend/components/AgentCard.tsx",
    "frontend/components/AgentGraph.tsx",
    "frontend/components/ExecutivePanel.tsx",
    "frontend/components/LiveLog.tsx",
]

OPTIONAL_FILES = [
    ".env",
    ".env.example",
    "agent_config.yaml",
    "data/enterprise-attack.json",
    "BAND_SWAP.md",
    "README.md",
]

for f in REQUIRED_FILES:
    if os.path.exists(f):
        ok(f)
    else:
        fail(f"MISSING: {f}")

for f in OPTIONAL_FILES:
    if os.path.exists(f):
        ok(f"(optional) {f}")
    else:
        warn(f"Missing optional: {f}")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — JSON DATA FILES
# ═════════════════════════════════════════════════════════════════════════════
section("2 / DATA FILE INTEGRITY")

def check_json(path, required_keys=None):
    try:
        with open(path) as f:
            data = json.load(f)
        if required_keys:
            for k in required_keys:
                if k not in data:
                    fail(f"{path} — missing key: '{k}'")
                    return None
        ok(f"{path} — valid JSON")
        return data
    except FileNotFoundError:
        fail(f"{path} — file not found")
    except json.JSONDecodeError as e:
        fail(f"{path} — invalid JSON", str(e))
    return None

company = check_json("data/company.json",
    required_keys=["company_name", "domain", "systems", "employees"])
if company:
    systems = company.get("systems", [])
    if len(systems) >= 4:
        ok(f"company.json — {len(systems)} systems defined")
    else:
        warn(f"company.json — only {len(systems)} systems (expected ≥4)")

    # Check each system has required fields
    for s in systems:
        missing = [k for k in ["id","ip","os","vulnerabilities"] if k not in s]
        if missing:
            warn(f"system '{s.get('id','?')}' missing fields: {missing}")

phishing = check_json("data/phishing_email.json",
    required_keys=["event_type","threat_sender","threat_target","attachment"])
if phishing:
    sender = phishing.get("threat_sender","")
    if "@" in sender and "." in sender:
        ok(f"phishing trigger — sender: {sender}")
    else:
        fail("phishing_email.json — invalid sender format")

logs = check_json("data/email_logs.json")
if isinstance(logs, list):
    malicious = [l for l in logs if phishing and phishing.get("threat_sender","") in l.get("sender","")]
    ok(f"email_logs.json — {len(logs)} entries, {len(malicious)} malicious match")
else:
    fail("email_logs.json — expected a JSON array")

check_json("data/network_map.json")

# MITRE ATT&CK check
if os.path.exists("data/enterprise-attack.json"):
    size_mb = os.path.getsize("data/enterprise-attack.json") / (1024*1024)
    if size_mb > 5:
        ok(f"enterprise-attack.json — {size_mb:.1f} MB (looks like full dataset)")
    else:
        warn(f"enterprise-attack.json — only {size_mb:.1f} MB (may be truncated)")
else:
    warn("enterprise-attack.json missing — run scripts/download_mitre.py")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PYTHON IMPORTS
# ═════════════════════════════════════════════════════════════════════════════
section("3 / PYTHON IMPORTS & DEPENDENCIES")

IMPORTS = [
    ("fastapi",              "FastAPI"),
    ("uvicorn",              "Uvicorn"),
    ("langchain_core",       "LangChain Core"),
    ("langchain_google_genai","LangChain Gemini"),
    ("langchain_openai",     "LangChain OpenAI"),
    ("langgraph",            "LangGraph"),
    ("dotenv",               "python-dotenv"),
    ("yaml",                 "PyYAML"),
    ("pydantic",             "Pydantic"),
    ("aiohttp",              "aiohttp"),
    ("websockets",           "websockets"),
]

OPTIONAL_IMPORTS = [
    ("thenvoi",              "Band SDK (thenvoi)"),
    ("langchain_groq",       "LangChain Groq"),
]

for module, name in IMPORTS:
    try:
        __import__(module)
        ok(f"{name}")
    except ImportError as e:
        fail(f"{name} — pip install failed", str(e))

for module, name in OPTIONAL_IMPORTS:
    try:
        __import__(module)
        ok(f"{name} (optional)")
    except ImportError:
        warn(f"{name} not installed — needed for real Band mode")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — CORE MODULE UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════
section("4 / CORE MODULE UNIT TESTS")

# 4a — band_client
try:
    sys.path.insert(0, ".")
    from core.band_client import MockBandBus, is_mock_mode, mock_bus
    ok("band_client imports clean")

    mode = is_mock_mode()
    ok(f"is_mock_mode() = {mode} (BAND_MOCK env var)")

    # Test room resolution
    class FakeAgent:
        name = "test"
        async def handle_mock_message(self, s, m): pass

    bus = MockBandBus()
    fa = FakeAgent()
    bus.register("threat-intel-room", fa)

    if "threat-intel-room" in bus.rooms:
        ok("MockBandBus.register() works")
    else:
        fail("MockBandBus.register() failed")
except Exception as e:
    fail("band_client import/test failed", traceback.format_exc(limit=2))

# 4b — event_bus
try:
    from core.event_bus import EventBus, event_bus
    ok("event_bus imports clean")

    # Test it's a singleton
    from core.event_bus import event_bus as eb2
    assert event_bus is eb2
    ok("event_bus is singleton")

    # Test timestamp is NOT hardcoded
    import inspect
    src = inspect.getsource(event_bus.broadcast)
    if "2026-06-19T08:45:00Z" in src:
        fail("event_bus — HARDCODED TIMESTAMP BUG still present!",
             "Fix: use datetime.now(timezone.utc).isoformat()")
    else:
        ok("event_bus — timestamp is dynamic (not hardcoded)")
except Exception as e:
    fail("event_bus import/test failed", traceback.format_exc(limit=2))

# 4c — mitre_lookup
try:
    from core.mitre_lookup import _db, search_ttp, get_technique
    ok("mitre_lookup imports clean")

    if os.path.exists("data/enterprise-attack.json"):
        _db.load_db()
        if len(_db.techniques) > 100:
            ok(f"MITRE DB loaded — {len(_db.techniques)} techniques")
        else:
            warn(f"MITRE DB loaded but only {len(_db.techniques)} techniques")

        result = json.loads(search_ttp.invoke({"keyword": "phishing"}))
        if result and len(result) > 0:
            ok(f"search_ttp('phishing') → {len(result)} results, first: {result[0].get('id')}")
        else:
            warn("search_ttp('phishing') returned 0 results")
    else:
        warn("Skipping MITRE search test — enterprise-attack.json not present")
except Exception as e:
    fail("mitre_lookup test failed", traceback.format_exc(limit=2))

# 4d — cve_lookup (offline check only — real API needs network)
try:
    from core.cve_lookup import get_cves, get_cves_async
    ok("cve_lookup imports clean")
    ok("NVD CVE API integration ready (skipping live call in unit test)")
except Exception as e:
    fail("cve_lookup import failed", traceback.format_exc(limit=2))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — AGENT UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════
section("5 / AGENT INSTANTIATION TESTS")

AGENT_CLASSES = [
    ("agents.threat_intel",     "ThreatIntelAgent",     "threat-intel-room"),
    ("agents.recon",            "ReconAgent",            "recon-room"),
    ("agents.red_team",         "RedTeamAgent",          "redteam-room"),
    ("agents.attack_path",      "AttackPathAgent",       "attack-path-room"),
    ("agents.detection",        "DetectionAgent",        "detection-room"),
    ("agents.malware",          "MalwareAgent",          "malware-room"),
    ("agents.blue_team",        "BlueTeamAgent",         "blueteam-room"),
    ("agents.incident_commander","IncidentCommander",    "incident-command-room"),
    ("agents.executive_decision","ExecutiveDecisionAgent","executive-room"),
]

for module_path, class_name, expected_room in AGENT_CLASSES:
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        agent = cls()

        # Check required attributes
        assert hasattr(agent, "name"), "missing .name"
        assert hasattr(agent, "room"), "missing .room"
        assert hasattr(agent, "system_prompt"), "missing .system_prompt"
        assert hasattr(agent, "custom_tools"), "missing .custom_tools"
        assert agent.room == expected_room, f"room mismatch: got '{agent.room}', expected '{expected_room}'"

        tool_count = len(agent.custom_tools)
        prompt_len = len(agent.system_prompt)

        if prompt_len < 200:
            warn(f"{class_name} — system_prompt only {prompt_len} chars (needs expert upgrade)")
        elif prompt_len < 500:
            warn(f"{class_name} — system_prompt {prompt_len} chars (could be more detailed)")
        else:
            ok(f"{class_name} — room={agent.room}, tools={tool_count}, prompt={prompt_len}c")

    except AssertionError as e:
        fail(f"{class_name} — assertion failed: {e}")
    except Exception as e:
        fail(f"{class_name} — instantiation error", traceback.format_exc(limit=3))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — AGENT TOOL TESTS
# ═════════════════════════════════════════════════════════════════════════════
section("6 / AGENT TOOL UNIT TESTS")

# Test each agent's domain tools return valid data
try:
    from agents.recon import scan_network, find_vulnerable_systems, check_exposed_services

    result = json.loads(scan_network.invoke({}))
    if "systems" in result and len(result["systems"]) > 0:
        ok(f"recon.scan_network() → {len(result['systems'])} systems")
    else:
        fail("recon.scan_network() returned no systems")

    vulns = json.loads(find_vulnerable_systems.invoke({}))
    ok(f"recon.find_vulnerable_systems() → {len(vulns)} vulnerable systems")

except Exception as e:
    fail("Recon tool test failed", traceback.format_exc(limit=2))

try:
    from agents.malware import analyze_file_metadata, classify_malware, extract_iocs, recommend_containment

    meta = json.loads(analyze_file_metadata.invoke({"file_name": "Invoice_2026_0891.exe"}))
    assert "file_entropy" in meta, "missing file_entropy"
    ok(f"malware.analyze_file_metadata() → entropy={meta.get('file_entropy')}")

    malware_class = classify_malware.invoke({"entropy": 7.85, "packed": "Yes"})
    if "Trojan" in malware_class or "Dropper" in malware_class or "Emotet" in malware_class:
        ok(f"malware.classify_malware() → {malware_class[:60]}")
    else:
        warn(f"malware.classify_malware() unexpected: {malware_class[:60]}")

    iocs = json.loads(extract_iocs.invoke({"file_name": "Invoice_2026_0891.exe"}))
    assert "c2_domains" in iocs, "missing c2_domains"
    ok(f"malware.extract_iocs() → {len(iocs.get('c2_domains',[]))} C2 domains")

except Exception as e:
    fail("Malware tool test failed", traceback.format_exc(limit=2))

try:
    from agents.detection import scan_email_logs, scan_server_logs

    email_matches = json.loads(scan_email_logs.invoke({"sender_domain": "corp-billing.xyz"}))
    if len(email_matches) > 0:
        ok(f"detection.scan_email_logs() → {len(email_matches)} malicious emails found")
    else:
        warn("detection.scan_email_logs() found 0 matches (check email_logs.json)")

    logs = json.loads(scan_server_logs.invoke({"server_id": "CEO-WORKSTATION-01"}))
    ok(f"detection.scan_server_logs() → {len(logs)} events")

except Exception as e:
    fail("Detection tool test failed", traceback.format_exc(limit=2))

try:
    from agents.attack_path import calculate_risk_score, predict_next_moves, identify_critical_assets

    score_raw = calculate_risk_score.invoke({"attack_stages": json.dumps([1,2,3,4,5,6]), "target_system": "SRV-03-DB"})
    score = int(score_raw) if str(score_raw).isdigit() else 0
    if score >= 70:
        ok(f"attack_path.calculate_risk_score() → {score}/100 (correctly CRITICAL)")
    else:
        warn(f"attack_path.calculate_risk_score() → {score}/100 (expected ≥70 for full chain)")

    preds = json.loads(predict_next_moves.invoke({}))
    ok(f"attack_path.predict_next_moves() → {len(preds)} predictions")

    assets = json.loads(identify_critical_assets.invoke({}))
    ok(f"attack_path.identify_critical_assets() → {len(assets)} crown jewels")

except Exception as e:
    fail("Attack path tool test failed", traceback.format_exc(limit=2))

try:
    from agents.executive_decision import cfo_financial_assessment, legal_regulatory_assessment, ops_continuity_assessment, ceo_final_decision

    cfo = json.loads(cfo_financial_assessment.invoke({"risk_score": 87.0}))
    assert "breach_cost_estimate" in cfo
    assert "containment_cost" in cfo
    ok(f"exec.cfo_financial_assessment() → breach={cfo['breach_cost_estimate']}")

    legal = json.loads(legal_regulatory_assessment.invoke({"has_pii": True}))
    assert "regulations_triggered" in legal
    regs = legal.get("regulations_triggered", [])
    has_gdpr = any("GDPR" in r for r in regs)
    if has_gdpr:
        ok(f"exec.legal_regulatory_assessment() → GDPR present ✓")
    else:
        warn("exec.legal_regulatory_assessment() — GDPR not found in regulations")

    ops = json.loads(ops_continuity_assessment.invoke({"downtime_summary": "2h mail server"}))
    assert "maintenance_window" in ops
    ok(f"exec.ops_continuity_assessment() → window={ops['maintenance_window'][:40]}")

    decision_raw = ceo_final_decision.invoke({
        "cfo_json": json.dumps(cfo),
        "legal_json": json.dumps(legal),
        "ops_json": json.dumps(ops)
    })
    decision = json.loads(decision_raw)
    verdict = decision.get("final_verdict","")
    if verdict in ("CONTAIN","ISOLATE","SHUTDOWN","ESCALATE"):
        ok(f"exec.ceo_final_decision() → VERDICT: {verdict} ✓")
    else:
        fail(f"exec.ceo_final_decision() — unexpected verdict: '{verdict}'")

except Exception as e:
    fail("Executive Decision tool test failed", traceback.format_exc(limit=2))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MOCK BUS ROUTING TEST
# ═════════════════════════════════════════════════════════════════════════════
section("7 / MOCK BAND BUS ROUTING TEST")

async def test_mock_routing():
    from core.band_client import MockBandBus

    received = []
    class MockAgent:
        name = "test_agent"
        async def handle_mock_message(self, sender, msg):
            received.append({"sender": sender, "msg": msg})

    bus = MockBandBus()
    agent = MockAgent()
    bus.register("threat-intel-room", agent)

    # Test direct room name
    await bus.send_message("SOC-Sensor", "threat-intel-room", "phishing alert test")
    await asyncio.sleep(0.1)

    if len(received) == 1 and received[0]["sender"] == "SOC-Sensor":
        return True, "Direct room routing works"
    return False, f"Expected 1 message, got {len(received)}"

try:
    success, detail = asyncio.run(test_mock_routing())
    if success:
        ok(f"MockBandBus routing — {detail}")
    else:
        fail(f"MockBandBus routing — {detail}")
except Exception as e:
    fail("MockBandBus routing test failed", traceback.format_exc(limit=2))

# Test handle resolution (aliases → canonical room names)
async def test_alias_routing():
    from core.band_client import MockBandBus

    received = []
    class MockAgent:
        name = "alias_test"
        async def handle_mock_message(self, sender, msg):
            received.append(msg)

    bus = MockBandBus()
    agent = MockAgent()
    bus.register("incident-command-room", agent)

    # Test that alias resolves to canonical room
    await bus.send_message("ThreatIntel", "@Incident-Commander", "report from threat intel")
    await asyncio.sleep(0.1)

    if len(received) == 1:
        return True, "@Incident-Commander alias resolves to incident-command-room"
    return False, f"Alias routing failed — got {len(received)} deliveries"

try:
    success, detail = asyncio.run(test_alias_routing())
    if success:
        ok(f"Room alias resolution — {detail}")
    else:
        warn(f"Room alias resolution — {detail}")
except Exception as e:
    fail("Room alias test failed", traceback.format_exc(limit=2))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — FASTAPI ENDPOINT TEST (starts server, tests all endpoints)
# ═════════════════════════════════════════════════════════════════════════════
section("8 / FASTAPI API ENDPOINT TESTS")

import socket, time

def port_is_open(port):
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except:
        return False

if port_is_open(8000):
    ok("Port 8000 already open — using existing server")
    server_started_here = False
else:
    warn("Port 8000 not open — starting server for tests (background process)")
    server_proc = subprocess.Popen(
        ["python", "-c",
         "import uvicorn; uvicorn.run('api.main:app', host='127.0.0.1', port=8000, log_level='error')"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2.5)
    server_started_here = True

if port_is_open(8000):
    try:
        import urllib.request, urllib.error

        # Test /api/status
        with urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=5) as r:
            data = json.loads(r.read())
        assert data.get("status") == "healthy"
        ok(f"/api/status → healthy, mock_mode={data.get('mock_mode')}")
        registered = data.get("registered_rooms", [])
        if len(registered) == 9:
            ok(f"/api/status → 9 rooms registered: {registered}")
        elif len(registered) > 0:
            warn(f"/api/status → only {len(registered)} rooms registered (expected 9 — are agents running?)")
        else:
            warn("/api/status → 0 rooms registered (agents not running yet — normal if server just started)")

        # Test /docs (OpenAPI)
        with urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=5) as r:
            html = r.read().decode()
        if "swagger" in html.lower() or "openapi" in html.lower():
            ok("/docs → Swagger UI accessible")
        else:
            warn("/docs → unexpected response")

        # Test /api/trigger-attack (POST)
        import urllib.parse
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/trigger-attack",
            data=b"",
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            tdata = json.loads(r.read())
        if tdata.get("status") == "success":
            ok(f"/api/trigger-attack → {tdata.get('message','')[:60]}")
        else:
            fail(f"/api/trigger-attack → {tdata}")

        # Test mock LLM endpoint
        mock_body = json.dumps({
            "model": "mock-model",
            "messages": [
                {"role": "system", "content": "You are a Threat Intelligence Analyst"},
                {"role": "user", "content": "Analyze phishing alert"}
            ],
            "tools": []
        }).encode()
        req2 = urllib.request.Request(
            "http://127.0.0.1:8000/mock-llm/chat/completions",
            data=mock_body,
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req2, timeout=5) as r:
            mdata = json.loads(r.read())
        choices = mdata.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            tool_calls = msg.get("tool_calls") or []
            ok(f"/mock-llm endpoint → role={msg.get('role')}, tool_calls={len(tool_calls)}")
        else:
            fail("/mock-llm endpoint → no choices in response", str(mdata)[:100])

    except Exception as e:
        fail("FastAPI endpoint test failed", traceback.format_exc(limit=2))
else:
    fail("Could not start/reach FastAPI on port 8000")
    server_started_here = False

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 9 — WEBSOCKET TEST
# ═════════════════════════════════════════════════════════════════════════════
section("9 / WEBSOCKET TEST")

async def test_websocket():
    try:
        import websockets as ws_lib
        received_events = []

        async def run():
            async with ws_lib.connect("ws://127.0.0.1:8000/ws", open_timeout=3) as ws:
                # Trigger attack to generate events
                import urllib.request
                req = urllib.request.Request(
                    "http://127.0.0.1:8000/api/trigger-attack",
                    data=b"", method="POST",
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=3)

                # Wait up to 3s for events
                try:
                    async with asyncio.timeout(3.0):
                        while True:
                            msg = await ws.recv()
                            event = json.loads(msg)
                            received_events.append(event)
                except asyncio.TimeoutError:
                    pass

        await run()
        return received_events
    except Exception as e:
        return str(e)

if port_is_open(8000):
    try:
        result = asyncio.run(test_websocket())
        if isinstance(result, list):
            if len(result) > 0:
                types = set(e.get("type") for e in result)
                agents_seen = set(e.get("agent") for e in result)
                ok(f"WebSocket received {len(result)} events — agents: {agents_seen}")
                for e in result[:2]:
                    ok(f"  Event sample: agent={e.get('agent')}, status={e.get('status')}")
            else:
                warn("WebSocket connected but received 0 events (agents may need API key to fire)")
        else:
            warn(f"WebSocket test skipped: {result}")
    except Exception as e:
        warn(f"WebSocket test error: {e}")
else:
    warn("Skipping WebSocket test — server not running")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 10 — ENVIRONMENT & BAND READINESS
# ═════════════════════════════════════════════════════════════════════════════
section("10 / ENVIRONMENT & BAND READINESS")

from dotenv import load_dotenv
load_dotenv()

# Check API keys
keys = {
    "GOOGLE_API_KEY":       ("Gemini LLM",       True),
    "FEATHERLESS_API_KEY":  ("Featherless AI",    False),
    "GROQ_API_KEY":         ("Groq (fallback)",   False),
    "BAND_API_KEY":         ("Band AI (Jun 12!)", False),
    "BAND_MOCK":            ("Band mock toggle",  True),
}

has_any_llm = False
for env_var, (desc, required) in keys.items():
    val = os.getenv(env_var, "")
    placeholder_phrases = ["your-", "get-from", "here"]
    is_real = bool(val) and not any(p in val.lower() for p in placeholder_phrases)

    if is_real:
        has_any_llm = True if env_var in ("GOOGLE_API_KEY","FEATHERLESS_API_KEY","GROQ_API_KEY") else has_any_llm
        masked = val[:6] + "..." + val[-3:] if len(val) > 9 else "***"
        ok(f"{env_var} = {masked} ({desc})")
    elif required:
        warn(f"{env_var} — not set ({desc}) — mock LLM will be used")
    else:
        warn(f"{env_var} — not set ({desc})")

if not has_any_llm:
    warn("No LLM API keys found — will use mock LLM endpoint (demo still works!)")
    warn("For real agents: add GOOGLE_API_KEY to .env")

# Band SDK check
try:
    import thenvoi
    ok(f"Band SDK (thenvoi) installed — version: {getattr(thenvoi, '__version__', 'unknown')}")

    # Check expected attributes
    has_agent = hasattr(thenvoi, "Agent")
    if has_agent:
        ok("thenvoi.Agent class available")
    else:
        fail("thenvoi.Agent not found — check SDK version at docs.thenvoi.com")

    try:
        from thenvoi.adapters import LangGraphAdapter
        ok("thenvoi.adapters.LangGraphAdapter importable")
    except ImportError:
        try:
            from thenvoi.adapters.langgraph import LangGraphAdapter
            ok("thenvoi.adapters.langgraph.LangGraphAdapter importable")
        except ImportError:
            fail("LangGraphAdapter not found — verify import path at docs.thenvoi.com")

except ImportError:
    warn("Band SDK (thenvoi) not installed — install: pip install 'band-sdk[langgraph]'")
    warn("Needed for real Band mode on Jun 12")

# agent_config check
if os.path.exists("agent_config.yaml"):
    with open("agent_config.yaml") as f:
        config = yaml_module_check = None
        try:
            import yaml
            config = yaml.safe_load(f)
        except:
            pass
    if config:
        agents_configured = list(config.keys())
        has_real = any(
            config.get(a,{}).get("api_key","get-from") != "get-from-band-dashboard"
            for a in agents_configured
        )
        if has_real:
            ok(f"agent_config.yaml — REAL credentials found for: {agents_configured}")
        else:
            warn(f"agent_config.yaml — still has placeholder credentials (fill in on Jun 12)")
    else:
        warn("agent_config.yaml — could not parse")
else:
    warn("agent_config.yaml — not created yet (copy from agent_config.example.yaml on Jun 12)")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 11 — FRONTEND READINESS
# ═════════════════════════════════════════════════════════════════════════════
section("11 / FRONTEND READINESS")

if os.path.exists("frontend/package.json"):
    with open("frontend/package.json") as f:
        pkg = json.load(f)
    deps = {**pkg.get("dependencies",{}), **pkg.get("devDependencies",{})}

    required_frontend = ["next", "react", "react-dom", "reactflow", "tailwindcss", "typescript"]
    for dep in required_frontend:
        if dep in deps:
            ok(f"frontend dep: {dep}@{deps[dep]}")
        else:
            fail(f"frontend dep missing: {dep}")

    # Check node_modules installed
    if os.path.exists("frontend/node_modules"):
        ok("frontend/node_modules exists (npm install done)")
    else:
        fail("frontend/node_modules MISSING — run: cd frontend && npm install")

# Check WS URL in hook
try:
    with open("frontend/hooks/useAgentWebSocket.ts") as f:
        ws_src = f.read()
    if "ws://localhost:8000/ws" in ws_src:
        ok("useAgentWebSocket.ts — WS URL = ws://localhost:8000/ws ✓")
    else:
        warn("useAgentWebSocket.ts — WebSocket URL may be incorrect")

    all_agents = [
        "threat_intel_agent","recon_agent","red_team_agent","attack_path_agent",
        "detection_agent","malware_agent","blue_team_agent",
        "incident_commander","executive_decision"
    ]
    for agent_name in all_agents:
        if agent_name in ws_src:
            pass  # ok
        else:
            warn(f"useAgentWebSocket.ts — '{agent_name}' not in initial state")
except Exception as e:
    fail("Frontend hook check failed", str(e))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 12 — CHAIN SEQUENCE VALIDATION (mock simulation)
# ═════════════════════════════════════════════════════════════════════════════
section("12 / AGENT CHAIN SEQUENCE VALIDATION")

EXPECTED_CHAIN = [
    ("SOC-Alert-Sensor",      "threat-intel-room"),    # trigger → threat intel
    ("Threat Intelligence",   "incident-command-room"),# TI → commander
    ("Incident Commander",    "recon-room"),           # commander → recon (parallel)
    ("Incident Commander",    "detection-room"),       # commander → detection (parallel)
    ("Recon",                 "incident-command-room"),# recon → commander
    ("Detection",             "incident-command-room"),# detection → commander
    ("Incident Commander",    "redteam-room"),         # commander → red team
    ("Incident Commander",    "malware-room"),         # commander → malware (parallel)
    ("Red Team",              "incident-command-room"),# red team → commander
    ("Malware Investigation", "incident-command-room"),# malware → commander
    ("Incident Commander",    "attack-path-room"),     # commander → attack path
    ("Attack Path",           "incident-command-room"),# attack path → commander
    ("Incident Commander",    "blueteam-room"),        # commander → blue team (parallel)
    ("Incident Commander",    "executive-room"),       # commander → exec (parallel)
    ("Blue Team",             "incident-command-room"),# blue team → commander
    ("Executive Decision",    "incident-command-room"),# exec → commander
]

# Validate Incident Commander system prompt covers all phases
try:
    from agents.incident_commander import SYSTEM_PROMPT as IC_PROMPT

    required_mentions = [
        "threat-intel-room",
        "recon-room",
        "detection-room",
        "redteam-room",
        "malware-room",
        "attack-path-room",
        "blueteam-room",
        "executive-room",
    ]

    missing_rooms = [r for r in required_mentions if r not in IC_PROMPT]
    if not missing_rooms:
        ok("Incident Commander prompt — all 8 target rooms mentioned")
    else:
        fail(f"Incident Commander prompt missing rooms: {missing_rooms}")

    required_phases = ["PHASE 1", "PHASE 2", "PHASE 3", "PHASE 4", "PHASE 5"]
    missing_phases = [p for p in required_phases if p not in IC_PROMPT]
    if not missing_phases:
        ok("Incident Commander prompt — all 5 phases defined")
    else:
        warn(f"Incident Commander prompt missing phases: {missing_phases} (run prompt upgrade)")

    if "risk score" in IC_PROMPT.lower() and "70" in IC_PROMPT:
        ok("Incident Commander — escalation threshold (score ≥70) present")
    else:
        warn("Incident Commander — escalation threshold missing in prompt")

    if "@" in IC_PROMPT and "thenvoi_send_message" in IC_PROMPT:
        ok("Incident Commander — uses @mentions + thenvoi_send_message ✓")
    else:
        warn("Incident Commander — @mentions or thenvoi_send_message not in prompt")

except Exception as e:
    fail("Incident Commander prompt validation failed", str(e))

# Validate room name consistency: agent.room == routing targets
try:
    import importlib
    MODULE_ROOM_MAP = {
        "agents.threat_intel":       ("ThreatIntelAgent",      "threat-intel-room"),
        "agents.recon":              ("ReconAgent",            "recon-room"),
        "agents.red_team":           ("RedTeamAgent",          "redteam-room"),
        "agents.attack_path":        ("AttackPathAgent",       "attack-path-room"),
        "agents.detection":          ("DetectionAgent",        "detection-room"),
        "agents.malware":            ("MalwareAgent",          "malware-room"),
        "agents.blue_team":          ("BlueTeamAgent",         "blueteam-room"),
        "agents.incident_commander": ("IncidentCommander",     "incident-command-room"),
        "agents.executive_decision": ("ExecutiveDecisionAgent","executive-room"),
    }
    all_consistent = True
    for mod_path, (cls_name, expected_room) in MODULE_ROOM_MAP.items():
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        agent = cls()
        if agent.room != expected_room:
            fail(f"Room mismatch: {cls_name}.room='{agent.room}' != '{expected_room}'")
            all_consistent = False

    if all_consistent:
        ok("All 9 agent room names consistent with routing targets ✓")

except Exception as e:
    fail("Room consistency check failed", traceback.format_exc(limit=2))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 13 — SUBMISSION READINESS
# ═════════════════════════════════════════════════════════════════════════════
section("13 / SUBMISSION READINESS CHECKLIST")

submission_checks = [
    ("README.md exists",            os.path.exists("README.md")),
    (".env.example exists",          os.path.exists(".env.example")),
    ("LICENSE exists",              os.path.exists("LICENSE")),
    ("BAND_SWAP.md exists",         os.path.exists("BAND_SWAP.md")),
    ("requirements.txt exists",     os.path.exists("requirements.txt")),
    ("agent_config.example.yaml",   os.path.exists("agent_config.example.yaml")),
    (".gitignore has .env",         ".env" in open(".gitignore").read() if os.path.exists(".gitignore") else False),
    (".gitignore has enterprise-attack.json", "enterprise-attack.json" in open(".gitignore").read() if os.path.exists(".gitignore") else False),
    ("MIT license",                 "MIT" in open("LICENSE").read() if os.path.exists("LICENSE") else False),
]

for check_name, passed in submission_checks:
    if passed:
        ok(check_name)
    else:
        warn(f"TODO: {check_name}")

# README quality check
if os.path.exists("README.md"):
    readme = open("README.md").read()
    readme_checks = [
        ("Quick Start section",       "Quick Start" in readme or "quick start" in readme.lower()),
        ("Band mentioned",            "Band" in readme),
        ("9 agents mentioned",        "9" in readme and "agent" in readme.lower()),
        ("MITRE mentioned",           "MITRE" in readme),
        ("Architecture diagram",      "```" in readme or "diagram" in readme.lower()),
    ]
    for name, passed in readme_checks:
        if passed:
            ok(f"README — {name}")
        else:
            warn(f"README — missing: {name}")

# ═════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
print(f"\n{BLD}{'═'*60}{RST}")
print(f"{BLD}  Fusion TEST SUMMARY{RST}")
print(f"{BLD}{'═'*60}{RST}")
total = results["pass"] + results["fail"] + results["warn"]
pct = int(results["pass"] / total * 100) if total > 0 else 0
print(f"  {GRN}PASS:  {results['pass']}{RST}")
print(f"  {RED}FAIL:  {results['fail']}{RST}")
print(f"  {YLW}WARN:  {results['warn']}{RST}")
print(f"  Score: {pct}% ({results['pass']}/{total})")
print()

if results["fail"] == 0 and results["warn"] <= 5:
    print(f"  {GRN}{BLD}🏆 Fusion IS READY TO WIN{RST}")
elif results["fail"] == 0:
    print(f"  {YLW}{BLD}⚠️  FIX WARNINGS THEN YOU'RE GOOD{RST}")
elif results["fail"] <= 3:
    print(f"  {YLW}{BLD}⚡ CLOSE — FIX THE {results['fail']} FAILURES{RST}")
else:
    print(f"  {RED}{BLD}🛠  {results['fail']} FAILURES TO FIX{RST}")

print()

# Cleanup
if 'server_started_here' in dir() and server_started_here:
    try:
        server_proc.terminate()
    except:
        pass
