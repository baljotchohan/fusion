# mcp_tools.py
"""
Shared FUSION MCP tool surface — one definition of the 5 committee tools and their
behavior, reused by BOTH transports:

  - stdio  (mcp_server.py)            — local clients (Claude Desktop, Claude Code)
  - HTTP   (api/main.py, mounted /mcp) — remote clients connect by URL

Each tool proxies to the running FUSION REST API (FUSION_API_URL, default
http://localhost:8000); learn_risk_pattern writes directly to the shared memory graph.
"""
import os
import logging

import httpx
from mcp.types import Tool

logger = logging.getLogger("fusion.mcp.tools")

FUSION_API_URL = os.getenv("FUSION_API_URL", f"http://localhost:{os.getenv('PORT', '8000')}")

# ── Tool surface (schemas) ───────────────────────────────────────────────────
TOOLS = [
    Tool(
        name="chat_with_managing_partner",
        description="Talk to the FUSION Managing Partner in plain English. Submitting a deal/pitch activates the 5-partner committee (Financial, Legal, Technical, Market).",
        inputSchema={
            "type": "object",
            "properties": {"message": {"type": "string", "description": "Your message, e.g. 'evaluate NovaPay Inc'"}},
            "required": ["message"],
        },
    ),
    Tool(
        name="get_deal_record",
        description="Retrieve a past investment target timeline, decision, and risk scorecard from the shared memory graph.",
        inputSchema={
            "type": "object",
            "properties": {"incident_id": {"type": "string", "description": "e.g. DEAL-20260610-084500"}},
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="get_boardroom_verdict",
        description="Get the investment committee's final verdict (INVEST / CONDITIONAL / PASS) for a startup deal.",
        inputSchema={
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="query_deal_vault",
        description="Query collective memory for similar past evaluations by sector or risk pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["keyword"],
        },
    ),
    Tool(
        name="learn_risk_pattern",
        description="Teach the committee a due-diligence checklist or risk pattern it should apply to future deals.",
        inputSchema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "e.g. money-transmitter"},
                "checklist": {"type": "string"},
                "success_rate": {"type": "number", "default": 0.8},
            },
            "required": ["keyword", "checklist"],
        },
    ),
]

TOOL_NAMES = [t.name for t in TOOLS]


async def _api(method: str, path: str, payload: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        if method == "GET":
            resp = await client.get(f"{FUSION_API_URL}{path}")
        else:
            resp = await client.post(f"{FUSION_API_URL}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


async def dispatch(name: str, arguments: dict) -> dict:
    """Execute a FUSION MCP tool by name. Returns a JSON-serializable dict.

    Transport-agnostic: both the stdio server and the mounted HTTP app call this.
    """
    arguments = arguments or {}
    try:
        if name == "chat_with_managing_partner":
            return await _api("POST", "/api/v1/chat", {"user_message": arguments["message"]})

        if name == "get_deal_record":
            return await _api("GET", f"/api/v1/incident/{arguments['incident_id']}")

        if name == "get_boardroom_verdict":
            inc = await _api("GET", f"/api/v1/incident/{arguments['incident_id']}")
            return {
                "incident_id": arguments["incident_id"],
                "final_decision": inc.get("final_decision")
                or "Decision pending — the boardroom has not completed synthesis yet.",
            }

        if name == "query_deal_vault":
            limit = arguments.get("limit", 5)
            return await _api("GET", f"/api/v1/memory/similar/{arguments['keyword']}?limit={limit}")

        if name == "learn_risk_pattern":
            from core.memory_graph import memory_graph
            await memory_graph.record_attack_pattern(
                arguments["keyword"],
                "observation",
                arguments["checklist"],
                arguments.get("success_rate", 0.8),
            )
            return {"status": "learned", "keyword": arguments["keyword"]}

        return {"error": f"Unknown tool: {name}"}

    except httpx.ConnectError:
        return {
            "error": f"FUSION API not reachable at {FUSION_API_URL}. "
                     "Start it with `python run.py` or set FUSION_API_URL."
        }
    except KeyError as e:
        return {"error": f"Missing required argument: {e}"}
    except Exception as e:
        return {"error": str(e)}
