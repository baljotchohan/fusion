#!/usr/bin/env python3
# scripts/setup_band_rooms.py
"""
Create the 9 real Band rooms — one per Fusion agent — and write the assigned
room IDs back into agent_config.yaml.

Run this ONCE at hackathon kickoff (Jun 12) after exporting BAND_API_KEY:

    export BAND_API_KEY="<key from band.ai dashboard>"
    python scripts/setup_band_rooms.py

Idempotent: agents that already have a room_id in agent_config.yaml are
skipped, so it is safe to re-run after a partial failure.
"""
import os
import sys
import asyncio
import logging

import httpx
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("fusion.setup_band_rooms")

CONFIG_PATH = "agent_config.yaml"
EXAMPLE_PATH = "agent_config.example.yaml"
BAND_API_BASE = os.getenv("BAND_API_BASE", "https://api.band.ai/v1")


def load_config() -> dict:
    path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else EXAMPLE_PATH
    with open(path, "r") as f:
        config = yaml.safe_load(f) or {}
    if path == EXAMPLE_PATH:
        logger.info(f"No {CONFIG_PATH} found — seeding from {EXAMPLE_PATH}")
    return config


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    logger.info(f"✓ Saved room IDs to {CONFIG_PATH}")


async def get_or_create_workspace(client: httpx.AsyncClient, headers: dict, config: dict) -> str:
    workspace_id = (config.get("band") or {}).get("workspace_id")
    if workspace_id:
        return workspace_id

    resp = await client.get(f"{BAND_API_BASE}/workspaces", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    workspaces = data.get("workspaces", data if isinstance(data, list) else [])
    if workspaces:
        workspace_id = workspaces[0].get("id")
        logger.info(f"Using existing workspace: {workspace_id}")
    else:
        resp = await client.post(
            f"{BAND_API_BASE}/workspaces",
            headers=headers,
            json={"name": "Fusion SOC"},
        )
        resp.raise_for_status()
        workspace_id = resp.json().get("id")
        logger.info(f"Created workspace: {workspace_id}")
    return workspace_id


async def create_room(client, headers, workspace_id, agent_name, agent_cfg) -> str:
    payload = {
        "name": agent_cfg.get("name", agent_name),
        "description": (
            f"Fusion agent room — {agent_cfg.get('role', agent_name)}.\n\n"
            f"{agent_cfg.get('system_prompt', '')[:500]}"
        ),
    }
    resp = await client.post(
        f"{BAND_API_BASE}/workspaces/{workspace_id}/rooms",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json().get("id")


async def main():
    api_key = os.getenv("BAND_API_KEY", "")
    if not api_key or "get-from" in api_key:
        logger.error("✗ BAND_API_KEY is not set. Export it first:\n"
                     "    export BAND_API_KEY=\"<key from band.ai>\"")
        sys.exit(1)

    config = load_config()
    agents = config.get("agents")
    if not agents:
        logger.error(f"✗ No 'agents:' section found in {CONFIG_PATH} / {EXAMPLE_PATH}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        workspace_id = await get_or_create_workspace(client, headers, config)
        config.setdefault("band", {})["workspace_id"] = workspace_id

        created, skipped, failed = 0, 0, 0
        for agent_name, agent_cfg in agents.items():
            agent_cfg = agent_cfg or {}
            if agent_cfg.get("room_id"):
                logger.info(f"• {agent_name}: room already exists ({agent_cfg['room_id']}) — skipping")
                skipped += 1
                continue
            try:
                room_id = await create_room(client, headers, workspace_id, agent_name, agent_cfg)
                agent_cfg["room_id"] = room_id
                agents[agent_name] = agent_cfg
                logger.info(f"✓ {agent_name}: created room {room_id}")
                created += 1
            except Exception as e:
                logger.error(f"✗ {agent_name}: room creation failed: {e}")
                failed += 1

    save_config(config)
    logger.info(f"\nDone. Created {created}, skipped {skipped}, failed {failed}.")
    logger.info("Verify all 9 rooms on the band.ai dashboard, then run with BAND_MOCK=false.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
