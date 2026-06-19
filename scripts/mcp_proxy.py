#!/usr/bin/env python3
"""
FUSION MCP Proxy — stdio <-> HTTP bridge. No OAuth, no npx, no mcp-remote.

This is the most reliable way to use FUSION from Claude Desktop on Windows,
where npx path-spaces and header-quote mangling break mcp-remote. It speaks
plain stdio JSON-RPC to the client and forwards each message to the hosted
FUSION MCP endpoint over HTTPS with your personal Bearer key.

Usage:
    python mcp_proxy.py <your-fus_-key>

Claude Desktop config (Windows / Mac / Linux):
    {
      "mcpServers": {
        "fusion-vc": {
          "command": "python",
          "args": ["C:\\\\Users\\\\you\\\\mcp_proxy.py", "fus_YOUR_KEY"]
        }
      }
    }

All diagnostics go to stderr, so they show up in Claude Desktop's MCP log
(the file you'd paste when troubleshooting) without corrupting the protocol.
"""
import sys
import json
import urllib.request
import urllib.error

# Ensure standard streams use UTF-8 encoding (especially critical on Windows)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

MCP_URL = "https://baljot07-fusion.hf.space/mcp/"
TOKEN = sys.argv[1].strip() if len(sys.argv) > 1 else ""


def _log(msg: str) -> None:
    """Write a diagnostic line to stderr (visible in Claude Desktop logs)."""
    print(f"[fusion-mcp-proxy] {msg}", file=sys.stderr, flush=True)


# Fail loudly and clearly if the key is missing or malformed — the #1 setup mistake.
if not TOKEN:
    _log("ERROR: no key given. Add your fus_ key as the 2nd arg in the config: "
         '["...mcp_proxy.py", "fus_YOUR_KEY"]. Get it from Settings -> Connect via MCP.')
elif not TOKEN.startswith("fus_"):
    _log(f"WARNING: key {TOKEN[:6]}... does not start with 'fus_'. "
         "Copy your exact key from Settings -> Connect via MCP -> Your private key.")

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
if TOKEN:
    _HEADERS["Authorization"] = f"Bearer {TOKEN}"

_log(f"started, bridging to {MCP_URL} as {TOKEN[:8] + '...' if TOKEN else '(no key)'}")


def _call(payload: bytes) -> str:
    req = urllib.request.Request(MCP_URL, data=payload, headers=_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            if "text/event-stream" in resp.headers.get("Content-Type", ""):
                # Unwrap SSE: keep only non-empty `data:` payload lines.
                lines = [ln[6:] for ln in raw.splitlines() if ln.startswith("data: ") and ln[6:].strip()]
                return "\n".join(lines)
            return raw
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 401:
            _log("HTTP 401 Unauthorized — your fus_ key is wrong or expired. Re-copy it from Settings.")
        elif e.code == 429:
            _log("HTTP 429 — rate limited. Wait a bit and retry.")
        else:
            _log(f"HTTP {e.code}: {body[:200]}")
        return json.dumps({"jsonrpc": "2.0", "id": None,
                           "error": {"code": -32000, "message": f"HTTP {e.code}: {body[:200]}"}})
    except Exception as e:
        _log(f"network error: {e}")
        return json.dumps({"jsonrpc": "2.0", "id": None,
                           "error": {"code": -32000, "message": str(e)}})


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    out = _call(line.encode()).strip()
    if out:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
