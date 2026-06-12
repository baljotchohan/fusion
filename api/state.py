# api/state.py
"""
Shared mutable API state, split out so api.main and api.v1 can both use it
without circular imports.
"""
import time
from typing import Dict, Optional, Set


class SimulationState:
    def __init__(self):
        self.running: bool = False
        # Last known status per agent ('idle' | 'working' | 'done' | 'alert')
        self.agent_statuses: Dict[str, str] = {}
        # Incident currently being worked by the swarm
        self.active_incident_id: Optional[str] = None
        # Pitch file (in data/) the committee should evaluate
        self.active_pitch_file: str = "novapay_pitch.json"
        # Deals that have already had their partner notifications dispatched
        self.dispatched_deals: Set[str] = set()
        # Wall-clock time of the last agent event — used to detect a stalled
        # run so the trigger lock can never stay stuck forever.
        self.last_event_at: float = 0.0
        # SaaS upload limit
        self.max_file_size_mb: int = 10
        # Active company name for current analysis
        self.active_company_name: Optional[str] = None

    def touch(self):
        self.last_event_at = time.time()

    def is_stale(self, max_idle_seconds: float = 90.0) -> bool:
        """True if a run claims to be in progress but no agent has emitted
        an event for max_idle_seconds — i.e. the chain died mid-flight."""
        return self.running and (time.time() - self.last_event_at) > max_idle_seconds

    def reset(self):
        self.running = False
        self.agent_statuses = {}
        self.dispatched_deals.clear()
        self.active_company_name = None
        self.active_pitch_file = "novapay_pitch.json"


sim_state = SimulationState()
