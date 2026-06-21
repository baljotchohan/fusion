# core/band_client.py
"""
Wrapper for the Band SDK client that supports real and mock operation modes.
Real mode connects to the thenvoi (Band) platform via websockets.
Mock mode runs a local in-memory message bus for local offline testing.

Key design: messages sent before an agent registers are buffered in `_pending`
and flushed the moment that agent registers. This eliminates the race condition
where trigger-deal fires before staggered-startup agents are online.
"""
import os
import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Any

logger = logging.getLogger("fusion.band_client")


# ── Canonical room name resolver ──────────────────────────────────────────────
_ROOM_ALIASES: Dict[str, str] = {
    # Managing Partner
    "@managing-partner": "managing-partner-room",
    "@managing-partner-agent": "managing-partner-room",
    "managing-partner": "managing-partner-room",
    "managing-partner-room": "managing-partner-room",
    # Financial Partner
    "@financial-partner": "finance-partner-room",
    "@financial-partner-agent": "finance-partner-room",
    "finance-partner": "finance-partner-room",
    "finance-partner-room": "finance-partner-room",
    "financial-partner": "finance-partner-room",
    # Legal Partner
    "@legal-partner": "legal-partner-room",
    "@legal-partner-agent": "legal-partner-room",
    "legal-partner": "legal-partner-room",
    "legal-partner-room": "legal-partner-room",
    # Technical Partner
    "@technical-partner": "tech-partner-room",
    "@technical-partner-agent": "tech-partner-room",
    "tech-partner": "tech-partner-room",
    "tech-partner-room": "tech-partner-room",
    "technical-partner": "tech-partner-room",
    # Market Partner
    "@market-partner": "market-partner-room",
    "@market-partner-agent": "market-partner-room",
    "market-partner": "market-partner-room",
    "market-partner-room": "market-partner-room",
}


def _resolve_room(target_room: str) -> str:
    """Return the canonical FUSION room name for any alias/handle."""
    cleaned = target_room.strip().lower()
    if cleaned in _ROOM_ALIASES:
        return _ROOM_ALIASES[cleaned]
    # Fuzzy fallback
    if "managing" in cleaned or "chair" in cleaned:
        return "managing-partner-room"
    if "financ" in cleaned:
        return "finance-partner-room"
    if "legal" in cleaned:
        return "legal-partner-room"
    if "tech" in cleaned:
        return "tech-partner-room"
    if "market" in cleaned:
        return "market-partner-room"
    return target_room  # unknown room — pass through unchanged


# ── MockBandBus ───────────────────────────────────────────────────────────────

class MockBandBus:
    """In-memory message bus.

    Messages sent to a room with no listeners are buffered in `_pending` and
    delivered automatically when an agent registers for that room.
    """

    def __init__(self):
        self.rooms: Dict[str, List[Any]] = {}
        # pending[(room)] = list of (sender, message, incident_id) tuples
        self._pending: Dict[str, list] = defaultdict(list)
        self._background_tasks: set = set()

    def register(self, room: str, agent: Any):
        """Register an agent to a room and flush any buffered messages."""
        if room not in self.rooms:
            self.rooms[room] = []
        if agent not in self.rooms[room]:
            self.rooms[room].append(agent)
            logger.info(f"Mock Band Bus: Registered agent '{agent.name}' to room '{room}'")

        # Flush buffered messages
        pending = self._pending.pop(room, [])
        for sender, message, incident_id in pending:
            logger.info(
                f"Mock Band Bus: Flushing buffered message to '{agent.name}' in '{room}' "
                f"(was buffered before agent registered)"
            )
            task = asyncio.create_task(
                self._safe_dispatch(agent, sender, message, room, incident_id)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def send_message(
        self,
        sender: str,
        target_room: str,
        message: str,
        incident_id: str | None = None,
    ):
        resolved = _resolve_room(target_room)
        logger.info(
            f"Mock Band Bus: [{sender}] -> room '{target_room}' "
            f"(resolved to '{resolved}'): {message[:120]}..."
        )

        if resolved not in self.rooms or not self.rooms[resolved]:
            # Buffer for delivery when the agent registers
            logger.info(
                f"Mock Band Bus: Room '{resolved}' has no listeners yet — "
                f"buffering message from '{sender}' for later delivery."
            )
            self._pending[resolved].append((sender, message, incident_id))
            return

        for agent in self.rooms[resolved]:
            task = asyncio.create_task(
                self._safe_dispatch(agent, sender, message, resolved, incident_id)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _safe_dispatch(
        self, agent, sender: str, message: str, room: str, incident_id: str | None
    ):
        """Dispatch a message to an agent with error handling and retry."""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                await agent.handle_mock_message(sender, message, incident_id)
                return
            except Exception as e:
                logger.error(
                    f"Mock Band Bus: Agent '{agent.name}' in room '{room}' "
                    f"failed to process message (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    # Don't emit "alert" for transient errors (TimeoutError, busy) —
                    # those would prematurely clear the run lock.
                    if not isinstance(e, (asyncio.TimeoutError, TimeoutError)):
                        try:
                            from core.event_bus import event_bus
                            await event_bus.broadcast(agent.name, "alert", {
                                "error": f"Failed to process message from {sender}: {str(e)[:200]}"
                            })
                        except Exception:
                            pass


# Global singleton mock bus
mock_bus = MockBandBus()


def is_mock_mode() -> bool:
    """Returns True if Band SDK is running in offline mock mode."""
    return os.getenv("BAND_MOCK", "true").lower() == "true"
