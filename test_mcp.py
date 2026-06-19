#!/usr/bin/env python3
"""
Live FUSION MCP client test — can be run as a standalone script or via pytest.
Exercises all 5 committee tools end-to-end against a running/spawned FUSION backend.

To run with pytest:  .venv/bin/pytest test_mcp.py
To run standalone:   python test_mcp.py
"""
import asyncio
import json
import os
import sys
import socket
import subprocess
import time

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

API = os.getenv("FUSION_API_URL", "http://localhost:8000")
PASS, FAIL = 0, 0


def _ok(label, cond, detail=""):
    global PASS, FAIL
    mark = "PASS" if cond else "FAIL"
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    return cond


def _payload(result) -> dict:
    """Extract the JSON dict a FUSION MCP tool returned."""
    if getattr(result, "structuredContent", None):
        sc = result.structuredContent
        if isinstance(sc, dict) and set(sc.keys()) == {"result"}:
            return sc["result"]
        return sc
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"_raw": text}
    return {}


def port_is_open(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False


async def test_mcp_all_tools():
    """Integration test checking all FUSION MCP tools."""
    global PASS, FAIL
    PASS, FAIL = 0, 0

    server_started_here = False
    server_proc = None

    # Check if FUSION API is running. If not, start it in mock mode.
    if not port_is_open(8000):
        print("Port 8000 not open — starting FUSION API server for tests (background)...")
        # Ensure we pass BAND_MOCK=true
        env = {**os.environ, "BAND_MOCK": "true", "PORT": "8000"}
        server_proc = subprocess.Popen(
            [sys.executable, "run.py"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        server_started_here = True

        # Wait for port 8000 to open
        for _ in range(15):
            if port_is_open(8000):
                break
            await asyncio.sleep(1)

        if not port_is_open(8000):
            if server_proc:
                server_proc.terminate()
            raise RuntimeError("FUSION API failed to start on port 8000.")
        else:
            print("FUSION API started successfully in the background. Waiting 18s for agents to register...")
            await asyncio.sleep(18)
    else:
        print("FUSION API is already running on port 8000.")

    try:
        params = StdioServerParameters(
            command=sys.executable,
            args=["mcp_server.py"],
            env={**os.environ, "FUSION_API_URL": API},
        )

        print(f"== FUSION MCP live test (API={API}) ==\n")
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1) tool discovery
                print("1) Tool discovery")
                tools = await session.list_tools()
                names = sorted(t.name for t in tools.tools)
                expected = sorted([
                    "chat_with_managing_partner",
                    "get_deal_record",
                    "get_boardroom_verdict",
                    "query_deal_vault",
                    "learn_risk_pattern",
                ])
                _ok("all 5 tools exposed", names == expected, ", ".join(names))

                # 2) trigger the committee
                print("\n2) chat_with_managing_partner → trigger committee")
                res = await session.call_tool(
                    "chat_with_managing_partner",
                    {"message": "Evaluate NovaPay Inc for a Series A investment."},
                )
                chat = _payload(res)
                incident_id = chat.get("incident_id")
                _ok(
                    "Managing Partner responded",
                    bool(chat.get("commander_response")),
                    (chat.get("commander_response") or "")[:70]
                    .replace("\n", " ")
                    .strip(),
                )
                _ok("incident opened", bool(incident_id), incident_id or "—")

                # 3) poll for the boardroom verdict
                print("\n3) get_boardroom_verdict → poll for final decision")
                decision, verdict_seen = "", False
                if incident_id:
                    for _ in range(45):  # ~90s max
                        vr = _payload(
                            await session.call_tool(
                                "get_boardroom_verdict",
                                {"incident_id": incident_id},
                            )
                        )
                        decision = vr.get("final_decision", "") or ""
                        if decision and "decision pending" not in decision.lower():
                            verdict_seen = True
                            break
                        await asyncio.sleep(2)
                import re as _re

                m = _re.search(
                    r"DECISION:\s*(INVEST|CONDITIONAL|PASS|REJECT)", decision.upper()
                )
                verdict_word = (
                    m.group(1)
                    if m
                    else next(
                        (
                            w
                            for w in ("CONDITIONAL", "PASS", "INVEST", "REJECT")
                            if _re.search(rf"\b{w}\b", decision.upper())
                        ),
                        "—",
                    )
                )
                _ok(
                    "committee reached a verdict",
                    verdict_seen,
                    f"verdict={verdict_word}",
                )

                # 4) deal record
                print("\n4) get_deal_record")
                if incident_id:
                    rec = _payload(
                        await session.call_tool(
                            "get_deal_record", {"incident_id": incident_id}
                        )
                    )
                    _ok(
                        "deal record returned",
                        rec.get("incident_id") == incident_id
                        or bool(rec.get("timeline") or rec.get("final_decision")),
                        f"keys={list(rec)[:5]}",
                    )
                else:
                    _ok("deal record returned", False, "no incident id")

                # 5) deal vault search
                print("\n5) query_deal_vault('fintech')")
                vault = _payload(
                    await session.call_tool(
                        "query_deal_vault", {"keyword": "fintech", "limit": 5}
                    )
                )
                _ok(
                    "vault query returned results array",
                    "similar_deals" in vault,
                    f"{len(vault.get('similar_deals', []))} match(es)",
                )

                # 6) teach a pattern
                print("\n6) learn_risk_pattern")
                learned = _payload(
                    await session.call_tool(
                        "learn_risk_pattern",
                        {
                            "keyword": "money-transmitter",
                            "checklist": "Verify state MTLs are in place before close.",
                            "success_rate": 0.9,
                        },
                    )
                )
                _ok(
                    "pattern learned",
                    learned.get("status") == "learned",
                    learned.get("keyword", ""),
                )
    finally:
        if server_started_here and server_proc:
            print("Stopping background FUSION API server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    print(f"\n== RESULT: {PASS} passed / {FAIL} failed ==")
    assert FAIL == 0, f"{FAIL} tests failed!"


if __name__ == "__main__":
    asyncio.run(test_mcp_all_tools())
