# api/state.py
"""
Shared mutable API state, split out so api.main and api.v1 can both use it
without circular imports.
"""
from typing import Dict, Optional


class SimulationState:
    def __init__(self):
        self.running: bool = False
        # Last known status per agent ('idle' | 'working' | 'done' | 'alert')
        self.agent_statuses: Dict[str, str] = {}
        # Incident currently being worked by the swarm
        self.active_incident_id: Optional[str] = None

    def reset(self):
        self.running = False
        self.agent_statuses = {}


sim_state = SimulationState()
