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

logger = logging.getLogger("argus.band_client")

# Mock message bus for in-memory agent communication
class MockBandBus:
    def __init__(self):
        self.rooms: Dict[str, List[Any]] = {}

    def register(self, room: str, agent: Any):
        if room not in self.rooms:
            self.rooms[room] = []
        if agent not in self.rooms[room]:
            self.rooms[room].append(agent)
            logger.info(f"Mock Band Bus: Registered agent '{agent.name}' to room '{room}'")

    async def send_message(self, sender: str, target_room: str, message: str):
        logger.info(f"Mock Band Bus: [{sender}] -> room '{target_room}': {message[:120]}...")
        if target_room not in self.rooms:
            logger.warning(f"Mock Band Bus: Room '{target_room}' does not exist or has no listeners.")
            return

        for agent in self.rooms[target_room]:
            # Schedule execution of the agent asynchronously to mimic WebSocket trigger
            asyncio.create_task(agent.handle_mock_message(sender, message))

# Global singleton mock bus
mock_bus = MockBandBus()

def is_mock_mode() -> bool:
    """Returns True if Band SDK is running in offline mock mode."""
    # Default to True (mock mode) if BAND_MOCK is set to 'true', or if credentials are empty
    band_mock = os.getenv("BAND_MOCK", "true").lower() == "true"
    return band_mock
