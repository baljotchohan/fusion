#!/usr/bin/env python3
# mcp_server.py
"""
FUSION MCP Server — expose the 5-partner VC investment committee as tools for external AI apps.

Any MCP-capable client (Claude Desktop, Claude Code, custom agents) can
recruit FUSION agents:

  - chat_with_managing_partner(message)       -> Managing Partner chat
  - get_deal_record(incident_id)              -> shared-memory deal record
  - get_boardroom_verdict(incident_id)         -> Boardroom verdict
  - query_deal_vault(keyword)                  -> similar past deals
  - learn_risk_pattern(keyword, checklist)     -> teach the committee a pattern

The tools proxy to the running FUSION REST API (start it with `python run.py`).

Install:  pip install mcp
Run:      python mcp_server.py            (stdio transport)
Config:   FUSION_API_URL (default http://localhost:8000)
"""
import asyncio
import json
import logging
import os

import httpx

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fusion.mcp")

FUSION_API_URL = os.getenv("FUSION_API_URL", "http://localhost:8000")

server = Server("fusion-mcp")

TOOLS = [
    Tool(
        name="chat_with_managing_partner",
        description="Talk to the FUSION Managing Partner in plain English. Submitting a deal/pitch activates the committee.",
        inputSchema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    ),
    Tool(
        name="get_deal_record",
        description="Retrieve a past investment target timeline, decision, and risk scorecard data from the shared memory graph.",
        inputSchema={
            "type": "object",
            "properties": {"incident_id": {"type": "string", "description": "e.g. DEAL-20260610-084500"}},
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="get_boardroom_verdict",
        description="Get the investment committee's final verdict for a startup deal.",
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
        description="Teach the committee a due diligence checklist or risk pattern.",
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


@server.list_tools()
async def list_tools() -> list:
    return TOOLS


async def _api(method: str, path: str, payload: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        if method == "GET":
            resp = await client.get(f"{FUSION_API_URL}{path}")
        else:
            resp = await client.post(f"{FUSION_API_URL}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    try:
        if name == "chat_with_managing_partner":
            result = await _api("POST", "/api/v1/chat", {"user_message": arguments["message"]})
        elif name == "get_deal_record":
            result = await _api("GET", f"/api/v1/incident/{arguments['incident_id']}")
        elif name == "get_boardroom_verdict":
            inc = await _api("GET", f"/api/v1/incident/{arguments['incident_id']}")
            result = {
                "incident_id": arguments["incident_id"],
                "final_decision": inc.get("final_decision") or "Decision pending — the boardroom has not synthesis complete yet.",
            }
        elif name == "query_deal_vault":
            limit = arguments.get("limit", 5)
            result = await _api("GET", f"/api/v1/memory/similar/{arguments['keyword']}?limit={limit}")
        elif name == "learn_risk_pattern":
            from core.memory_graph import memory_graph
            await memory_graph.record_attack_pattern(
                arguments["keyword"],
                "observation",
                arguments["checklist"],
                arguments.get("success_rate", 0.8),
            )
            result = {"status": "learned", "keyword": arguments["keyword"]}
        else:
            result = {"error": f"Unknown tool: {name}"}
    except httpx.ConnectError:
        result = {
            "error": f"FUSION API not reachable at {FUSION_API_URL}. "
                     "Start it with `python run.py` or set FUSION_API_URL."
        }
    except Exception as e:
        result = {"error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    logger.info("FUSION MCP Server running on stdio...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
