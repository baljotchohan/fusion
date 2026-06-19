# core/event_bus.py
"""
Central event bus to broadcast agent activity and status updates
to the FastAPI WebSocket connections (to update the Next.js dashboard).
"""
import json
import logging
from datetime import datetime, timezone
from typing import Callable, List, Dict

logger = logging.getLogger("argus.event_bus")

class EventBus:
    def __init__(self):
        self._listeners: List[Callable[[dict], None]] = []

    def register_listener(self, callback: Callable[[dict], None]):
        """Register a callback that receives events."""
        if callback not in self._listeners:
            self._listeners.append(callback)
            logger.debug("Registered a new event bus listener.")

    def unregister_listener(self, callback: Callable[[dict], None]):
        """Unregister an existing callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)
            logger.debug("Unregistered an event bus listener.")

    async def broadcast(self, agent_name: str, status: str, output: dict = None):
        """Broadcast an agent state update to all registered listeners."""
        uid = None
        incident_id = None
        try:
            from core.auth import current_uid, current_incident_id
            uid = current_uid.get()
            incident_id = current_incident_id.get()
        except Exception:
            pass

        event_data = {
            "type": "agent_update",
            "agent": agent_name,
            "status": status,  # 'idle', 'working', 'done', 'alert'
            "output": output or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uid": uid,
            "incident_id": incident_id,
        }
        
        logger.info(f"Broadcasting event: Agent={agent_name}, Status={status}")
        
        # Snapshot the list so register/unregister during broadcast is safe
        for listener in list(self._listeners):
            try:
                # If listener is a coroutine function, await it, otherwise run it
                import inspect
                if inspect.iscoroutinefunction(listener):
                    await listener(event_data)
                else:
                    listener(event_data)
            except Exception as e:
                logger.error(f"Error calling event bus listener: {e}")

# Global singleton event bus
event_bus = EventBus()


class RealBandBus:
    """Live Band coordination for agent handoffs.

    Posts @mention messages into the real per-agent Band rooms (created by
    scripts/setup_band_rooms.py) so judges can verify agent-to-agent
    handoffs directly on the band.ai dashboard.
    """

    def __init__(self, api_key: str, agent_config: dict, api_base: str = None):
        import os
        self.api_key = api_key
        self.api_base = api_base or os.getenv("BAND_API_BASE", "https://api.band.ai/v1")
        self.agent_config = agent_config or {}
        # agent_name -> room_id, from the `agents:` section of agent_config.yaml
        self.rooms: Dict[str, str] = {}
        self._init_rooms()

    def _init_rooms(self):
        agents = self.agent_config.get("agents", {})
        for agent_name, config in agents.items():
            room_id = (config or {}).get("room_id")
            if room_id:
                self.rooms[agent_name] = room_id
            else:
                logger.warning(f"RealBandBus: no room_id for agent '{agent_name}' "
                               f"(run scripts/setup_band_rooms.py first)")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def post_message(
        self,
        from_agent: str,
        to_agents: List[str],
        message: str,
        context: dict = None,
    ) -> bool:
        """Post an @mention message to one or more agents' Band rooms.

        Example:
          await bus.post_message(
              from_agent="recon",
              to_agents=["red_team"],
              message="Found 3 exposed services. Proceeding with simulation.",
              context={"exposed_ports": [22, 443, 8080]},
          )
        """
        import httpx
        success = True
        agents_cfg = self.agent_config.get("agents", {})

        for to_agent in to_agents:
            room_id = self.rooms.get(to_agent)
            if not room_id:
                logger.error(f"RealBandBus: room for '{to_agent}' not found")
                success = False
                continue

            display_name = (agents_cfg.get(to_agent) or {}).get("name", to_agent)
            full_message = f"@{display_name} {message}"
            if context:
                full_message += f"\n```json\n{json.dumps(context, indent=2)}\n```"

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{self.api_base}/rooms/{room_id}/messages",
                        headers=self._headers(),
                        json={"content": full_message, "sender": from_agent},
                    )
                    resp.raise_for_status()
                logger.info(f"RealBandBus: {from_agent} -> {to_agent}: posted to Band")
            except Exception as e:
                logger.error(f"RealBandBus: post failed ({from_agent} -> {to_agent}): {e}")
                success = False

        return success

    async def read_room_history(self, agent_name: str, limit: int = 10) -> List[dict]:
        """Read an agent's room message history (for Commander context)."""
        import httpx
        room_id = self.rooms.get(agent_name)
        if not room_id:
            return []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.api_base}/rooms/{room_id}/messages",
                    headers=self._headers(),
                    params={"limit": limit},
                )
                resp.raise_for_status()
                messages = resp.json().get("messages", resp.json() if isinstance(resp.json(), list) else [])
            return [
                {"author": m.get("sender", m.get("from_agent", "unknown")),
                 "text": m.get("content", m.get("text", ""))}
                for m in messages
            ]
        except Exception as e:
            logger.error(f"RealBandBus: read history failed for '{agent_name}': {e}")
            return []
