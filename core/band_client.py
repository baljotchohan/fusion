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

    def register(self, room: str, agent: Any):
        if room not in self.rooms:
            self.rooms[room] = []
        if agent not in self.rooms[room]:
            self.rooms[room].append(agent)
            logger.info(f"Mock Band Bus: Registered agent '{agent.name}' to room '{room}'")

    async def send_message(self, sender: str, target_room: str, message: str):
        # Resolve target room name to map handles and variants to registered rooms
        ROOM_MAPPING = {
            # handles
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
            # room variations
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
            if "intel" in cleaned:
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
            # Schedule execution of the agent asynchronously to mimic WebSocket trigger
            asyncio.create_task(agent.handle_mock_message(sender, message))

# Global singleton mock bus
mock_bus = MockBandBus()

def is_mock_mode() -> bool:
    """Returns True if Band SDK is running in offline mock mode."""
    # Default to True (mock mode) if BAND_MOCK is set to 'true', or if credentials are empty
    band_mock = os.getenv("BAND_MOCK", "true").lower() == "true"
    return band_mock
