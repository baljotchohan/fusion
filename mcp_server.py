#!/usr/bin/env python3
# mcp_server.py
"""
ARGUS MCP Server — expose the 9-agent SOC team as tools for external AI apps.

Any MCP-capable client (Claude Desktop, Claude Code, custom agents) can
recruit ARGUS agents:

  - run_security_scan(repo_url, scan_type)   -> Recon + Detection + Threat Intel
  - analyze_threat(indicator, ioc_type)      -> Threat Intel IoC analysis
  - chat_with_commander(message)             -> Incident Commander chat
  - get_incident(incident_id)                -> shared-memory incident record
  - get_team_decision(incident_id)           -> Executive Decision verdict
  - query_team_memory(attack_technique)      -> similar past incidents
  - learn_attack_pattern(mitre_id, defense)  -> teach the team a defense

The tools proxy to the running ARGUS REST API (start it with `python run.py`).

Install:  pip install mcp
Run:      python mcp_server.py            (stdio transport)
Config:   ARGUS_API_URL (default http://localhost:8000)

Claude Desktop config (claude_desktop_config.json):
  {
    "mcpServers": {
      "argus": {"command": "python", "args": ["/path/to/argus/mcp_server.py"]}
    }
  }
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
logger = logging.getLogger("argus.mcp")

ARGUS_API_URL = os.getenv("ARGUS_API_URL", "http://localhost:8000")

server = Server("argus-mcp")

TOOLS = [
    Tool(
        name="run_security_scan",
        description="Recruit ARGUS Recon + Detection + Threat Intel agents to scan a GitHub repository for exposed secrets, vulnerable dependencies, and Dependabot alerts. Returns findings, a 1-10 threat level, and recommendations.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_url": {"type": "string", "description": "GitHub repo URL or 'owner/repo'"},
                "scan_type": {"type": "string", "enum": ["full", "secrets", "deps"], "default": "full"},
            },
            "required": ["repo_url"],
        },
    ),
    Tool(
        name="analyze_threat",
        description="Recruit the ARGUS Threat Intel agent to analyze an indicator of compromise (IP, domain, file hash, or keyword) against live NVD CVE data and the team's shared incident memory.",
        inputSchema={
            "type": "object",
            "properties": {
                "indicator": {"type": "string"},
                "ioc_type": {"type": "string", "enum": ["ip", "domain", "hash", "keyword"], "default": "domain"},
            },
            "required": ["indicator"],
        },
    ),
    Tool(
        name="chat_with_commander",
        description="Talk to the ARGUS Incident Commander in plain English. Reporting an attack activates the full 9-agent response team via Band coordination.",
        inputSchema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    ),
    Tool(
        name="get_incident",
        description="Retrieve a past incident from the team's shared memory graph: timeline of agent findings, threat level, and final decision.",
        inputSchema={
            "type": "object",
            "properties": {"incident_id": {"type": "string", "description": "e.g. INC-20260610-084500"}},
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="get_team_decision",
        description="Get the Executive Decision board's final verdict for an incident.",
        inputSchema={
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    ),
    Tool(
        name="query_team_memory",
        description="Query the team's collective memory for similar past incidents by MITRE ATT&CK technique ID (e.g. T1566.002) or keyword.",
        inputSchema={
            "type": "object",
            "properties": {
                "attack_technique": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["attack_technique"],
        },
    ),
    Tool(
        name="learn_attack_pattern",
        description="Teach the ARGUS team a defense recipe for a MITRE technique so future incidents are handled faster.",
        inputSchema={
            "type": "object",
            "properties": {
                "mitre_id": {"type": "string", "description": "e.g. T1566.001"},
                "defense": {"type": "string"},
                "success_rate": {"type": "number", "default": 0.8},
            },
            "required": ["mitre_id", "defense"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list:
    return TOOLS


async def _api(method: str, path: str, payload: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        if method == "GET":
            resp = await client.get(f"{ARGUS_API_URL}{path}")
        else:
            resp = await client.post(f"{ARGUS_API_URL}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    try:
        if name == "run_security_scan":
            result = await _api("POST", "/api/v1/scan", {
                "repo_url": arguments["repo_url"],
                "scan_type": arguments.get("scan_type", "full"),
            })
        elif name == "analyze_threat":
            result = await _api("POST", "/api/v1/analyze-threat", {
                "indicator": arguments["indicator"],
                "ioc_type": arguments.get("ioc_type", "domain"),
            })
        elif name == "chat_with_commander":
            result = await _api("POST", "/api/v1/chat", {"user_message": arguments["message"]})
        elif name == "get_incident":
            result = await _api("GET", f"/api/v1/incident/{arguments['incident_id']}")
        elif name == "get_team_decision":
            inc = await _api("GET", f"/api/v1/incident/{arguments['incident_id']}")
            result = {
                "incident_id": arguments["incident_id"],
                "final_decision": inc.get("final_decision") or "Decision pending — the boardroom has not convened yet.",
            }
        elif name == "query_team_memory":
            limit = arguments.get("limit", 5)
            result = await _api("GET", f"/api/v1/memory/similar/{arguments['attack_technique']}?limit={limit}")
        elif name == "learn_attack_pattern":
            # Direct shared-memory write — works even when the API is down
            from core.memory_graph import memory_graph
            await memory_graph.record_attack_pattern(
                arguments["mitre_id"],
                "observation",
                arguments["defense"],
                arguments.get("success_rate", 0.8),
            )
            result = {"status": "learned", "mitre_id": arguments["mitre_id"]}
        else:
            result = {"error": f"Unknown tool: {name}"}
    except httpx.ConnectError:
        result = {
            "error": f"ARGUS API not reachable at {ARGUS_API_URL}. "
                     "Start it with `python run.py` or set ARGUS_API_URL."
        }
    except Exception as e:
        result = {"error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    logger.info("ARGUS MCP Server running on stdio...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
