# core/band_client.py
"""
Wrapper for the Band SDK client that supports real and mock operation modes.
Real mode connects to the thenvoi (Band) platform via websockets.
Mock mode runs a local in-memory message bus for local offline testing.
"""
import os
import asyncio
import logging
from typing import Dict, List, Callable, Any

logger = logging.getLogger("fusion.band_client")

# Mock message bus for in-memory agent communication
class MockBandBus:
    def __init__(self):
        self.rooms: Dict[str, List[Any]] = {}
        self._background_tasks: set = set()

    def register(self, room: str, agent: Any):
        if room not in self.rooms:
            self.rooms[room] = []
        if agent not in self.rooms[room]:
            self.rooms[room].append(agent)
            logger.info(f"Mock Band Bus: Registered agent '{agent.name}' to room '{room}'")

    async def send_message(self, sender: str, target_room: str, message: str):
        # Resolve target room name to map handles and variants to registered rooms
        ROOM_MAPPING = {
            # ── FUSION rooms ──────────────────────────────────────
            "@managing-partner": "managing-partner-room",
            "@managing-partner-agent": "managing-partner-room",
            "@financial-partner": "finance-partner-room",
            "@financial-partner-agent": "finance-partner-room",
            "@legal-partner": "legal-partner-room",
            "@legal-partner-agent": "legal-partner-room",
            "@technical-partner": "tech-partner-room",
            "@technical-partner-agent": "tech-partner-room",
            "@market-partner": "market-partner-room",
            "@market-partner-agent": "market-partner-room",
            "managing-partner-room": "managing-partner-room",
            "managing-partner": "managing-partner-room",
            "finance-partner-room": "finance-partner-room",
            "finance-partner": "finance-partner-room",
            "financial-partner": "finance-partner-room",
            "legal-partner-room": "legal-partner-room",
            "legal-partner": "legal-partner-room",
            "tech-partner-room": "tech-partner-room",
            "tech-partner": "tech-partner-room",
            "technical-partner": "tech-partner-room",
            "market-partner-room": "market-partner-room",
            "market-partner": "market-partner-room",
            # ── Legacy ARGUS rooms (kept for backward compat) ─────
            "@threat-intel": "threat-intel-room",
            "@threat-intel-agent": "threat-intel-room",
            "@recon": "recon-room",
            "@recon-agent": "recon-room",
            "@red-team": "redteam-room",
            "@red-team-agent": "redteam-room",
            "@redteam": "redteam-room",
            "@attack-path": "attack-path-room",
            "@attack-path-agent": "attack-path-room",
            "@detection": "detection-room",
            "@detection-agent": "detection-room",
            "@malware-investigation": "malware-room",
            "@malware-investigation-agent": "malware-room",
            "@malware": "malware-room",
            "@malware-agent": "malware-room",
            "@blue-team": "blueteam-room",
            "@blue-team-agent": "blueteam-room",
            "@blueteam": "blueteam-room",
            "@incident-commander": "incident-command-room",
            "@incident-commander-agent": "incident-command-room",
            "@executive-decision": "executive-room",
            "@executive-decision-agent": "executive-room",
            "@executive": "executive-room",
            "threat-intel": "threat-intel-room",
            "recon": "recon-room",
            "redteam": "redteam-room",
            "red-team": "redteam-room",
            "attack-path": "attack-path-room",
            "detection": "detection-room",
            "malware": "malware-room",
            "blueteam": "blueteam-room",
            "blue-team": "blueteam-room",
            "incident-commander": "incident-command-room",
            "incident-command": "incident-command-room",
            "executive": "executive-room",
            "executive-decision": "executive-room",
        }
        
        cleaned = target_room.strip().lower()
        resolved = ROOM_MAPPING.get(cleaned, target_room)
        
        # Fuzzy checks as fallback
        if resolved not in self.rooms:
            # FUSION fuzzy matches
            if "managing" in cleaned or "chair" in cleaned:
                resolved = "managing-partner-room"
            elif "financ" in cleaned:
                resolved = "finance-partner-room"
            elif "legal" in cleaned:
                resolved = "legal-partner-room"
            elif "tech" in cleaned:
                resolved = "tech-partner-room"
            elif "market" in cleaned:
                resolved = "market-partner-room"
            # Legacy ARGUS fuzzy matches
            elif "intel" in cleaned:
                resolved = "threat-intel-room"
            elif "recon" in cleaned:
                resolved = "recon-room"
            elif "red" in cleaned:
                resolved = "redteam-room"
            elif "path" in cleaned or "attack" in cleaned:
                if "path" in cleaned:
                    resolved = "attack-path-room"
            elif "detect" in cleaned:
                resolved = "detection-room"
            elif "malware" in cleaned:
                resolved = "malware-room"
            elif "blue" in cleaned:
                resolved = "blueteam-room"
            elif "command" in cleaned or "incident" in cleaned:
                resolved = "incident-command-room"
            elif "exec" in cleaned:
                resolved = "executive-room"

        logger.info(f"Mock Band Bus: [{sender}] -> room '{target_room}' (resolved to '{resolved}'): {message[:120]}...")
        if resolved not in self.rooms:
            logger.warning(f"Mock Band Bus: Room '{resolved}' (original: '{target_room}') does not exist or has no listeners.")
            return

        for agent in self.rooms[resolved]:
            # Schedule execution of the agent asynchronously to mimic WebSocket trigger.
            # Wrap in an error handler so failures are logged (not silently swallowed).
            task = asyncio.create_task(
                self._safe_dispatch(agent, sender, message, resolved)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _safe_dispatch(self, agent, sender: str, message: str, room: str):
        """Dispatch a message to an agent with error handling and retry."""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                await agent.handle_mock_message(sender, message)
                return  # Success
            except Exception as e:
                logger.error(
                    f"Mock Band Bus: Agent '{agent.name}' in room '{room}' "
                    f"failed to process message (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    # All retries exhausted — broadcast alert so the dashboard shows the failure
                    try:
                        from core.event_bus import event_bus
                        await event_bus.broadcast(agent.name, "alert", {
                            "error": f"Failed to process message from {sender}: {str(e)[:200]}"
                        })
                    except Exception:
                        pass  # Last resort — at least the error is logged above

# Global singleton mock bus
mock_bus = MockBandBus()

def is_mock_mode() -> bool:
    """Returns True if Band SDK is running in offline mock mode."""
    # Default to True (mock mode) if BAND_MOCK is set to 'true', or if credentials are empty
    band_mock = os.getenv("BAND_MOCK", "true").lower() == "true"
    return band_mock
