# core/event_bus.py
"""
Central event bus to broadcast agent activity and status updates
to the FastAPI WebSocket connections (to update the Next.js dashboard).
"""
import json
import logging
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
        event_data = {
            "type": "agent_update",
            "agent": agent_name,
            "status": status,  # 'idle', 'working', 'done', 'alert'
            "output": output or {},
            "timestamp": "2026-06-19T08:45:00Z"  # Standardized mock demo timestamp
        }
        
        logger.info(f"Broadcasting event: Agent={agent_name}, Status={status}")
        
        # Call all listener callbacks (which should be async-safe or handled)
        for listener in self._listeners:
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
