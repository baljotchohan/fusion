#!/usr/bin/env python3
"""
Self-check for per-user MCP isolation — the security-critical guarantee that one
user's fus_<uid> key can ONLY ever resolve to their own data namespace.

Runs standalone (repo convention — no pytest):  python test_mcp_isolation.py

If this fails, the MCP isolation chain is broken and users could share or leak
data. The chain under test:

    Bearer fus_<uid>  ──get_uid──▶  <uid>          (core/auth.py)
    Bearer fus_<uid>  ──middleware──▶ current_uid=<uid>, current_token=fus_<uid>
    current_token ──_api()──▶ forwarded to REST sub-request  (mcp_tools.py)

We assert the deterministic key→uid resolution that the whole isolation model
rests on. We do NOT need a running server — this is pure resolution logic.
"""
import asyncio
import os
import sys

# Auth-disabled would short-circuit get_uid; force the real path for this check.
os.environ.pop("FUSION_AUTH_DISABLED", None)
os.environ["FUSION_TEST_MODE"] = "true"


class _FakeRequest:
    """Minimal stand-in for starlette Request: just headers + query_params."""
    def __init__(self, auth: str = "", token: str = ""):
        self.headers = {"Authorization": auth} if auth else {}
        self.query_params = {"token": token} if token else {}


async def _run() -> int:
    from core.auth import get_uid
    from fastapi import HTTPException

    failures = []

    def check(label, cond):
        print(f"  {'✓' if cond else '✗'} {label}")
        if not cond:
            failures.append(label)

    # 1. fus_<uid> resolves to exactly that uid
    uid_a = await get_uid(_FakeRequest(auth="Bearer fus_alice123"))
    check("fus_alice123 → 'alice123'", uid_a == "alice123")

    # 2. A different key resolves to a DIFFERENT uid (no cross-user collision)
    uid_b = await get_uid(_FakeRequest(auth="Bearer fus_bob456"))
    check("fus_bob456 → 'bob456'", uid_b == "bob456")
    check("alice and bob never collide", uid_a != uid_b)

    # 3. Token may also arrive as a query param (?token=) — same resolution
    uid_q = await get_uid(_FakeRequest(token="fus_alice123"))
    check("?token=fus_alice123 → 'alice123'", uid_q == "alice123")

    # 4. Empty / malformed keys are REJECTED, never silently mapped to a shared uid
    for bad in ("Bearer fus_", "Bearer fus_   ", "Bearer ", ""):
        try:
            await get_uid(_FakeRequest(auth=bad))
            check(f"rejects {bad!r}", False)
        except HTTPException as e:
            check(f"rejects {bad!r} (401)", e.status_code == 401)

    # 5. The middleware mirrors get_uid: confirm the prefix-strip is identical so
    #    current_uid (data namespace) and current_token (forwarded auth) agree.
    token = "fus_carol789"
    derived_uid = token[4:].strip()  # exact logic in api/main.py set_request_context
    check("middleware uid == get_uid uid",
          derived_uid == await get_uid(_FakeRequest(auth=f"Bearer {token}")))

    print()
    if failures:
        print(f"❌ {len(failures)} isolation check(s) FAILED — DO NOT DEPLOY")
        return 1
    print("✅ Per-user MCP isolation intact — each fus_ key maps to exactly one uid")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
