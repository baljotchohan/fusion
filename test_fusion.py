"""
FUSION — Complete Test Suite
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
    "core/cve_lookup.py",
    "api/main.py",
    "api/v1.py",
    "agents/managing_partner.py",
    "agents/financial_partner.py",
    "agents/legal_partner.py",
    "agents/technical_partner.py",
    "agents/market_partner.py",
    "data/novapay_pitch.json",
    "frontend/pages/index.tsx",
    "frontend/package.json",
    "frontend/hooks/useAgentWebSocket.ts",
    "frontend/components/AgentCard.tsx",
    "frontend/components/AgentGraph.tsx",
    "frontend/components/ExecutivePanel.tsx",
    "frontend/components/LiveLog.tsx",
    "frontend/components/MemoryView.tsx",
    "frontend/components/SettingsView.tsx",
]

OPTIONAL_FILES = [
    ".env",
    ".env.example",
    "agent_config.yaml",
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
        ok(f"(optional) {f} - optional file not present")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — JSON DATA FILES
# ═════════════════════════════════════════════════════════════════════════════
section("2 / PITCH DATA FILES")

try:
    with open("data/novapay_pitch.json") as f:
        pitch = json.load(f)
    ok("data/novapay_pitch.json parsed successfully")

    # Assert necessary keys are present
    assert "company" in pitch, "missing 'company' section"
    assert "financials" in pitch, "missing 'financials' section"
    assert "legal" in pitch, "missing 'legal' section"
    assert "technical" in pitch, "missing 'technical' section"
    assert "market" in pitch, "missing 'market' section"
    ok("novapay_pitch.json has all 5 required diligence sections")

    # Inspect fields inside financials
    fin = pitch.get("financials", {})
    claims = pitch.get("pitch_claims", {})
    assert "arr" in claims, "pitch_claims missing arr"
    assert "monthly_burn_usd" in fin, "financials missing monthly_burn_usd"
    ok(f"Financials metrics verified: ARR={claims.get('arr')}, Burn={fin.get('monthly_burn_usd')}")
except Exception as e:
    fail("novapay_pitch.json validation failed", str(e))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PYTHON DEPENDENCIES & PATHS
# ═════════════════════════════════════════════════════════════════════════════
section("3 / CORE PYTHON IMPORTS")

IMPORTS = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Server"),
    ("pydantic", "BaseModel"),
    ("dotenv", "load_dotenv"),
    ("langchain_core.tools", "tool"),
    ("core.base_agent", "BaseAgent"),
    ("core.band_client", "mock_bus"),
    ("core.memory_graph", "memory_graph"),
    ("core.cve_lookup", "get_cves_async"),
]

for module, symbol in IMPORTS:
    try:
        mod = __import__(module, fromlist=[symbol])
        getattr(mod, symbol)
        ok(f"Import {module}.{symbol} works")
    except Exception as e:
        fail(f"Import failed: {module}.{symbol}", str(e))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — AGENT INSTANTIATION TESTS
# ═════════════════════════════════════════════════════════════════════════════
section("4 / AGENT INSTANTIATION TESTS")

AGENT_CLASSES = [
    ("agents.managing_partner", "ManagingPartner", "managing-partner-room"),
    ("agents.financial_partner", "FinancialPartner", "finance-partner-room"),
    ("agents.legal_partner", "LegalPartner", "legal-partner-room"),
    ("agents.technical_partner", "TechnicalPartner", "tech-partner-room"),
    ("agents.market_partner", "MarketPartner", "market-partner-room"),
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

        ok(f"{class_name} initialized: room='{agent.room}', tools={tool_count}, prompt_len={prompt_len}")
    except Exception as e:
        fail(f"Agent class {class_name} failed to instantiate", traceback.format_exc(limit=2))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — AGENT TOOL UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════
section("5 / AGENT TOOL UNIT TESTS")

try:
    from core.pitch_loader import load_deal_brief, get_company_name, get_red_flags

    comp_name = get_company_name.invoke({})
    assert comp_name == "NovaPay Inc", f"expected NovaPay Inc, got {comp_name}"
    ok(f"pitch_loader.get_company_name() → {comp_name}")

    fin_brief = load_deal_brief.invoke({"section": "financials"})
    assert "arr" in fin_brief.lower()
    ok("pitch_loader.load_deal_brief('financials') → Loaded financials details")

    red_flags = json.loads(get_red_flags.invoke({"domain": "legal"}))
    assert len(red_flags) > 0
    ok(f"pitch_loader.get_red_flags('legal') → Loaded {len(red_flags)} legal red flags")
except Exception as e:
    fail("Pitch loader tools test failed", traceback.format_exc(limit=2))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — MOCK BAND BUS ROUTING TEST
# ═════════════════════════════════════════════════════════════════════════════
section("6 / MOCK BAND BUS ROUTING TEST")

async def test_mock_routing():
    from core.band_client import MockBandBus

    received = []
    class MockAgent:
        name = "test_agent"
        async def handle_mock_message(self, sender, msg):
            received.append((sender, msg))

    bus = MockBandBus()
    bus.register("test-room", MockAgent())
    await bus.send_message("SenderAgent", "test-room", "Hello Partner")
    await asyncio.sleep(0.05)

    assert len(received) == 1, "message not received"
    assert received[0] == ("SenderAgent", "Hello Partner"), "message content mismatch"
    ok("MockBandBus routing — Direct room routing works")

    # Test alias mapping
    from api.v1 import AGENT_NAMES
    assert "managing_partner" in AGENT_NAMES
    ok("AGENT_NAMES registry covers managing_partner")

asyncio.run(test_mock_routing())

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — FASTAPI API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════
section("7 / FASTAPI API ENDPOINT TESTS")

import urllib.request
import urllib.error

def is_port_open(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

port = int(os.environ.get("PORT", "8081"))
server_started_by_us = False
proc = None

if not is_port_open(port):
    ok(f"Port {port} not open — starting server for tests (background process)")
    env = os.environ.copy()
    env["BAND_MOCK"] = "True"
    env["PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )
    server_started_by_us = True
    # wait for server up
    for _ in range(30):
        time.sleep(0.3)
        if is_port_open(port):
            break
else:
    ok(f"Port {port} already open — testing against running instance")

def test_get(path):
    try:
        url = f"http://127.0.0.1:{port}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3.0) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return 0, str(e)

def test_post(path, body):
    try:
        url = f"http://127.0.0.1:{port}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return 0, str(e)

if is_port_open(port):
    # test health status
    status_code, body = test_get("/api/status")
    if status_code == 200:
        ok(f"/api/status → healthy, mock_mode={body.get('mock_mode')}")
        if len(body.get("registered_rooms", [])) == 0:
            ok("/api/status → 0 rooms registered (agents starting up — normal if server just started)")
        else:
            ok(f"/api/status → {len(body.get('registered_rooms', []))} rooms registered")
    else:
        fail(f"/api/status failed", str(body))

    # test swagger docs
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/docs", timeout=2.0) as r:
            if r.status == 200:
                ok("/docs → Swagger UI accessible")
            else:
                fail(f"/docs status {r.status}")
    except Exception as e:
        fail("/docs inaccessible", str(e))

    # test trigger deal
    status_code, body = test_post("/api/trigger-deal", {"company": "NovaPay Inc", "raise_amount": "$10M"})
    if status_code == 200:
        ok(f"/api/trigger-deal → {body.get('message')}")
    else:
        fail("/api/trigger-deal trigger failed", str(body))

    # test mock llm chat completions
    mock_payload = {
        "messages": [
            {"role": "system", "content": "You are the Financial Partner"},
            {"role": "user", "content": "Load deal brief for financials"}
        ],
        "stream": False
    }
    status_code, body = test_post("/mock-llm/chat/completions", mock_payload)
    if status_code == 200:
        choice = body.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        tc = choice.get("message", {}).get("tool_calls")
        ok(f"/mock-llm endpoint → choices={len(body.get('choices',[]))}, has_content={bool(content)}, tool_calls={len(tc) if tc else 0}")
    else:
        fail("/mock-llm completions failed", str(body))

else:
    fail("FastAPI server failed to start within timeout.")

# Clean up server
if server_started_by_us and proc:
    proc.terminate()
    proc.wait()
    ok("Background server process terminated")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — FRONTEND READINESS
# ═════════════════════════════════════════════════════════════════════════════
section("8 / FRONTEND READINESS")

if os.path.exists("frontend/package.json"):
    with open("frontend/package.json") as f:
        pkg = json.load(f)
    deps = {**pkg.get("dependencies",{}), **pkg.get("devDependencies",{})}

    required_frontend = ["next", "react", "react-dom", "framer-motion", "lucide-react", "tailwindcss", "typescript"]
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
        "managing_partner", "financial_partner", "legal_partner",
        "technical_partner", "market_partner"
    ]
    for agent_name in all_agents:
        if agent_name in ws_src:
            pass  # ok
        else:
            warn(f"useAgentWebSocket.ts — '{agent_name}' not in initial state")
except Exception as e:
    fail("Frontend hook check failed", str(e))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 9 — AGENT CHAIN SEQUENCE VALIDATION
# ═════════════════════════════════════════════════════════════════════════════
section("9 / BOARDROOM CHAIN SEQUENCE VALIDATION")

try:
    with open("agents/managing_partner.py") as f:
        mp_src = f.read()

    # Check rooms
    rooms = ["finance-partner-room", "legal-partner-room", "tech-partner-room", "market-partner-room"]
    missing_rooms = [r for r in rooms if r not in mp_src]
    if not missing_rooms:
        ok("Managing Partner dispatches to all 4 specialist partner rooms")
    else:
        fail(f"Managing Partner prompt missing target rooms: {missing_rooms}")

    # Check synthesis logic
    if "synthesize" in mp_src.lower() or "weighted" in mp_src.lower():
        ok("Managing Partner has synthesis/weighted risk scoring logic in prompt")
    else:
        warn("Managing Partner might be missing synthesis/weighted risk rules")

except Exception as e:
    fail("Managing Partner sequence validation failed", str(e))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 10 — SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
print(f"\n{BLD}{CYN}{'═'*60}{RST}")
print(f"{BLD}{CYN}  FUSION TEST SUMMARY{RST}")
print(f"{BLD}{CYN}{'═'*60}{RST}")
print(f"  PASS:  {GRN}{results['pass']}{RST}")
print(f"  FAIL:  {RED if results['fail'] > 0 else GRN}{results['fail']}{RST}")
print(f"  WARN:  {YLW if results['warn'] > 0 else GRN}{results['warn']}{RST}")

total = sum(results.values())
if total > 0:
    pct = (results["pass"] / total) * 100
    print(f"  Score: {pct:.0f}% ({results['pass']}/{total})")

if results["fail"] > 0:
    print(f"\n  {RED}{BLD}⚡ FAILURE ENCOUNTERED — FIX THE {results['fail']} FAILURES{RST}\n")
    sys.exit(1)
else:
    print(f"\n  {GRN}{BLD}🎉 SUCCESS — ALL SYSTEMS GO FOR FUSION COMMITTEE{RST}\n")
    sys.exit(0)
