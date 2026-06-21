# api/state.py
"""
Request-aware isolated API state to prevent data leakage between different users.
Uses the current_uid ContextVar to partition state data per user dynamically.
"""
import time
import threading
from collections import defaultdict
from typing import Dict, Optional, Set, Any

# Committee session tracking — in-memory, resets on server restart (fine for hackathon)
_week_sessions: dict = defaultdict(list)  # key → [epoch_float, ...]

def count_sessions_this_week(key: str) -> int:
    cutoff = time.time() - 7 * 86400
    _week_sessions[key] = [t for t in _week_sessions[key] if t > cutoff]
    return len(_week_sessions[key])

def record_session(key: str) -> None:
    cutoff = time.time() - 7 * 86400
    _week_sessions[key] = [t for t in _week_sessions[key] if t > cutoff]
    _week_sessions[key].append(time.time())


# Global incident to uid registry
_incident_to_uid: Dict[str, str] = {}
_incident_registry_lock = threading.Lock()

def register_incident_uid(incident_id: str, uid: str):
    if incident_id and uid:
        with _incident_registry_lock:
            _incident_to_uid[incident_id] = uid

def get_uid_for_incident(incident_id: str) -> Optional[str]:
    with _incident_registry_lock:
        return _incident_to_uid.get(incident_id)


class SimulationState:
    def __init__(self):
        # Store state dictionaries keyed by "uid:incident_id"
        self._states: Dict[str, Dict[str, Any]] = {}

    def _get_state(self) -> Dict[str, Any]:
        uid = "__public__"
        incident_id = None
        try:
            from core.auth import current_uid, current_incident_id
            uid = current_uid.get()
            incident_id = current_incident_id.get()
        except Exception:
            pass

        if uid == "__mcp_client__":
            import os
            uid = os.getenv("FUSION_UID") or os.getenv("FUSION_ACTIVE_UID") or "__mcp_client__"

        # If incident_id is not in context, try to look up or find an active one for the uid
        if not incident_id:
            active_state = None
            for key, state in list(self._states.items()):
                if key.startswith(f"{uid}:") and state.get("running"):
                    active_state = state
                    break
            if active_state:
                return active_state

            user_keys = [k for k in list(self._states.keys()) if k.startswith(f"{uid}:")]
            if user_keys:
                user_keys.sort(key=lambda k: self._states[k].get("last_event_at", 0), reverse=True)
                return self._states[user_keys[0]]

            incident_id = "default"

        # Register mapping if we have both
        # ponytail: removed the unauthenticated→authenticated namespace escalation that was here.
        # That block allowed any caller who knew an incident_id to be silently remapped to the
        # owner's namespace. Background tasks (watchdog) explicitly set current_uid themselves.
        if uid and incident_id and incident_id != "default" and uid not in ("__public__", "__mcp_client__"):
            register_incident_uid(incident_id, uid)

        state_key = f"{uid}:{incident_id}"
        if state_key not in self._states:
            self._states[state_key] = {
                "running": False,
                "active_uid": uid if uid not in ("__public__", "__mcp_client__") else None,
                "active_user_name": None,
                "agent_statuses": {},
                "active_incident_id": incident_id if incident_id != "default" else None,
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
        return self._states[state_key]

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
