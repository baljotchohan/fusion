#!/usr/bin/env python3
"""
FUSION MCP Proxy — stdio ↔ HTTP bridge, no OAuth required.

Usage:
    python mcp_proxy.py <your-fus_-key>

Claude Desktop config (Windows & Mac):
    {
      "mcpServers": {
        "fusion-vc": {
          "command": "python",
          "args": ["C:\\path\\to\\mcp_proxy.py", "fus_YOUR_KEY"]
        }
      }
    }
"""
import sys
import json
import urllib.request
import urllib.error

MCP_URL = "https://baljot07-fusion.hf.space/mcp/"
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
if TOKEN:
    _HEADERS["Authorization"] = f"Bearer {TOKEN}"


def _call(payload: bytes) -> str:
    req = urllib.request.Request(MCP_URL, data=payload, headers=_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            if "text/event-stream" in resp.headers.get("Content-Type", ""):
                # Extract data: lines from SSE envelope
                lines = [l[6:] for l in raw.splitlines() if l.startswith("data: ") and l[6:].strip()]
                return "\n".join(lines)
            return raw
    except urllib.error.HTTPError as e:
        return json.dumps({
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32000, "message": f"HTTP {e.code}: {e.read().decode()}"},
        })
    except Exception as e:
        return json.dumps({
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32000, "message": str(e)},
        })


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    out = _call(line.encode()).strip()
    if out:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
