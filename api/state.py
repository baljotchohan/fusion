# api/state.py
"""
Request-aware isolated API state to prevent data leakage between different users.
Uses the current_uid ContextVar to partition state data per user dynamically.
"""
import time
from typing import Dict, Optional, Set, Any


class SimulationState:
    def __init__(self):
        # Store state dictionaries keyed by uid
        self._states: Dict[str, Dict[str, Any]] = {}

    def _get_state(self) -> Dict[str, Any]:
        uid = "__public__"
        try:
            from core.auth import current_uid
            uid = current_uid.get()
            if uid == "__mcp_client__":
                # Fallback for stdio or background tasks
                import os
                uid = os.getenv("FUSION_UID") or os.getenv("FUSION_ACTIVE_UID") or "__mcp_client__"
        except Exception:
            pass

        if uid not in self._states:
            self._states[uid] = {
                "running": False,
                "active_uid": uid if uid not in ("__public__", "__mcp_client__") else None,
                "active_user_name": None,
                "agent_statuses": {},
                "active_incident_id": None,
                "active_pitch_file": "novapay_pitch.json",
                "dispatched_deals": set(),
                "completed_agents": set(),
                "deal_concluded": False,
                "verdict_dispatched": False,
                "last_event_at": time.time(),
                "started_at": 0.0,
                "max_file_size_mb": 10,
                "active_company_name": None,
                "final_verdict_card": None,
                "_mp_verdict_pending": False,
                "_mp_verdict_triggered": False,
            }
        return self._states[uid]

    @property
    def running(self) -> bool:
        return self._get_state()["running"]

    @running.setter
    def running(self, val: bool):
        self._get_state()["running"] = val

    @property
    def active_uid(self) -> Optional[str]:
        return self._get_state()["active_uid"]

    @active_uid.setter
    def active_uid(self, val: Optional[str]):
        self._get_state()["active_uid"] = val

    @property
    def active_user_name(self) -> Optional[str]:
        return self._get_state()["active_user_name"]

    @active_user_name.setter
    def active_user_name(self, val: Optional[str]):
        self._get_state()["active_user_name"] = val

    @property
    def agent_statuses(self) -> Dict[str, str]:
        return self._get_state()["agent_statuses"]

    @agent_statuses.setter
    def agent_statuses(self, val: Dict[str, str]):
        self._get_state()["agent_statuses"] = val

    @property
    def active_incident_id(self) -> Optional[str]:
        return self._get_state()["active_incident_id"]

    @active_incident_id.setter
    def active_incident_id(self, val: Optional[str]):
        self._get_state()["active_incident_id"] = val

    @property
    def active_pitch_file(self) -> str:
        return self._get_state()["active_pitch_file"]

    @active_pitch_file.setter
    def active_pitch_file(self, val: str):
        self._get_state()["active_pitch_file"] = val

    @property
    def dispatched_deals(self) -> Set[str]:
        return self._get_state()["dispatched_deals"]

    @dispatched_deals.setter
    def dispatched_deals(self, val: Set[str]):
        self._get_state()["dispatched_deals"] = val

    @property
    def completed_agents(self) -> Set[str]:
        return self._get_state()["completed_agents"]

    @completed_agents.setter
    def completed_agents(self, val: Set[str]):
        self._get_state()["completed_agents"] = val

    @property
    def deal_concluded(self) -> bool:
        return self._get_state()["deal_concluded"]

    @deal_concluded.setter
    def deal_concluded(self, val: bool):
        self._get_state()["deal_concluded"] = val

    @property
    def verdict_dispatched(self) -> bool:
        return self._get_state()["verdict_dispatched"]

    @verdict_dispatched.setter
    def verdict_dispatched(self, val: bool):
        self._get_state()["verdict_dispatched"] = val

    @property
    def last_event_at(self) -> float:
        return self._get_state()["last_event_at"]

    @last_event_at.setter
    def last_event_at(self, val: float):
        self._get_state()["last_event_at"] = val

    @property
    def started_at(self) -> float:
        return self._get_state()["started_at"]

    @started_at.setter
    def started_at(self, val: float):
        self._get_state()["started_at"] = val

    @property
    def max_file_size_mb(self) -> int:
        return self._get_state()["max_file_size_mb"]

    @max_file_size_mb.setter
    def max_file_size_mb(self, val: int):
        self._get_state()["max_file_size_mb"] = val

    @property
    def active_company_name(self) -> Optional[str]:
        return self._get_state()["active_company_name"]

    @active_company_name.setter
    def active_company_name(self, val: Optional[str]):
        self._get_state()["active_company_name"] = val

    @property
    def final_verdict_card(self) -> Optional[str]:
        return self._get_state()["final_verdict_card"]

    @final_verdict_card.setter
    def final_verdict_card(self, val: Optional[str]):
        self._get_state()["final_verdict_card"] = val

    @property
    def _mp_verdict_pending(self) -> bool:
        return self._get_state()["_mp_verdict_pending"]

    @_mp_verdict_pending.setter
    def _mp_verdict_pending(self, val: bool):
        self._get_state()["_mp_verdict_pending"] = val

    @property
    def _mp_verdict_triggered(self) -> bool:
        return self._get_state()["_mp_verdict_triggered"]

    @_mp_verdict_triggered.setter
    def _mp_verdict_triggered(self, val: bool):
        self._get_state()["_mp_verdict_triggered"] = val

    def touch(self):
        self.last_event_at = time.time()

    def is_stale(self, max_idle_seconds: float = 300.0) -> bool:
        """True if a run claims to be in progress but no agent has emitted
        an event for max_idle_seconds."""
        return self.running and (time.time() - self.last_event_at) > max_idle_seconds

    def reset(self):
        st = self._get_state()
        st["running"] = False
        st["active_user_name"] = None
        st["agent_statuses"] = {}
        st["active_incident_id"] = None
        st["dispatched_deals"].clear()
        st["completed_agents"].clear()
        st["deal_concluded"] = False
        st["active_company_name"] = None
        st["active_pitch_file"] = "novapay_pitch.json"
        st["verdict_dispatched"] = False
        st["final_verdict_card"] = None
        st["started_at"] = 0.0
        st["_mp_verdict_pending"] = False
        st["_mp_verdict_triggered"] = False


sim_state = SimulationState()
