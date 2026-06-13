#!/usr/bin/env python3
# mcp_server.py
"""
FUSION MCP Server (stdio transport) — expose the 5-partner VC investment committee
as tools for local MCP clients (Claude Desktop, Claude Code, custom agents):

  - chat_with_managing_partner(message)       -> Managing Partner chat (triggers committee)
  - get_deal_record(incident_id)              -> shared-memory deal record
  - get_boardroom_verdict(incident_id)        -> committee verdict (INVEST/CONDITIONAL/PASS)
  - query_deal_vault(keyword)                 -> similar past deals
  - learn_risk_pattern(keyword, checklist)    -> teach the committee a pattern

The tool surface + behavior live in mcp_tools.py and are shared with the remote
HTTP transport mounted at /mcp by api/main.py. This file is the stdio entrypoint.

Install:  pip install -r requirements.txt   (mcp)
Run:      python mcp_server.py               (stdio)
Config:   FUSION_API_URL (default http://localhost:8000) — the running `python run.py` API.
Remote:   prefer the hosted endpoint at <deploy>/mcp (no local process needed).
"""
import asyncio
import json
import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

from mcp_tools import TOOLS, dispatch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fusion.mcp")

server = Server("fusion-mcp")


@server.list_tools()
async def list_tools() -> list:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    result = await dispatch(name, arguments)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    logger.info("FUSION MCP Server running on stdio...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
