# core/memory_graph.py
"""
Graphify-backed shared deal memory for all 5 partner agents.

Every deal evaluation is logged to a shared on-disk graph (JSON namespace under
./fusion_memory). Agents query past deals and learned checklist items
before acting, so the team gets measurably faster on repeat evaluations.

Files:
  - incidents.json:        all past deals with per-partner finding timelines
  - attack_patterns.json:  learned checklists per risk category
  - agent_profiles.json:   per-partner learning stats (findings, deals seen)
"""
import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timezone

logger = logging.getLogger("fusion.memory_graph")

# Sync lock for all synchronous callers (create_incident, delete_incident, etc.)
# ponytail: threading.Lock in async functions blocks the event loop thread; use
# _ASYNC_LOCK for async methods instead.
_LOCK = threading.Lock()
# Async lock for log_finding (called concurrently by the five parallel agents).
_ASYNC_LOCK = asyncio.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryGraph:
    """Shared deal memory graph used by every FUSION agent."""

    def __init__(self, graphify_dir: str = str(Path(__file__).parent.parent / "fusion_memory"), uid: str | None = None):
        self.graphify_dir = graphify_dir
        self._explicit_uid = uid

    @property
    def _resolved_uid(self) -> "str | None":
        """The effective uid — explicit override, else current_uid ContextVar, else None.
        ponytail: sim_state.active_uid fallback removed — it caused cross-session namespace leakage
        because the global sim_state carries the last active uid, not the requesting user's uid."""
        uid = self._explicit_uid
        if uid is None:
            try:
                from core.auth import current_uid
                val = current_uid.get(None)
                if val and val not in ("__mcp_client__", "__public__"):
                    uid = val
            except Exception:
                pass
        return uid

    @staticmethod
    def _sanitize_uid(uid: str) -> str:
        # Allow only characters safe for a directory component — same set as session_id.
        # ponytail: Firebase UIDs are alphanumeric in practice, but a crafted or
        # compromised token containing '..' or '/' would escape fusion_memory/ without this.
        return "".join(c for c in uid if c.isalnum() or c in ("-", "_"))

    @property
    def base_path(self) -> Path:
        base = Path(self.graphify_dir)
        raw = self._resolved_uid or "__public__"
        safe = self._sanitize_uid(raw) or "__public__"
        p = base / safe
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def incidents_file(self) -> Path:
        self._ensure_files()
        return self.base_path / "incidents.json"

    @property
    def patterns_file(self) -> Path:
        self._ensure_files()
        return self.base_path / "attack_patterns.json"

    @property
    def agent_profiles_file(self) -> Path:
        self._ensure_files()
        return self.base_path / "agent_profiles.json"

    @property
    def chat_file(self) -> Path:
        self._ensure_files()
        return self.base_path / "chat_history.json"

    def _ensure_files(self):
        # Use base_path directly to prevent infinite recursion
        base = self.base_path
        inc = base / "incidents.json"
        pat = base / "attack_patterns.json"
        prof = base / "agent_profiles.json"
        chat = base / "chat_history.json"
        
        for f in [inc, pat, prof]:
            if not f.exists():
                f.write_text(json.dumps({}, indent=2))
        if not chat.exists():
            chat.write_text(json.dumps([], indent=2))

    # ── Incidents ─────────────────────────────────────────────────────────

    def create_incident(self, incident_id: str, metadata: dict) -> dict:
        """Start a new incident record.

        incident_id: e.g. "INC-20260610-084500"
        metadata:    e.g. {"trigger": "phishing_email", "threat_level": 7}
        """
        ruid = self._resolved_uid
        fs_uid = ruid or "__public__"
        # Only register real authenticated uids — prevents None → None poisoning the registry
        if ruid:
            try:
                from api.state import register_incident_uid
                register_incident_uid(incident_id, ruid)
            except Exception:
                pass
        with _LOCK:
            incidents = self._read_file(self.incidents_file)
            # If local is empty (e.g. after a server restart), seed from Firestore first
            # so that creating a new deal doesn't erase prior history from the dashboard.
            if not incidents:
                try:
                    from core.firestore_memory import fs_list_incidents
                    remote = fs_list_incidents(fs_uid)
                    if remote:
                        incidents = remote
                        logger.info("Memory: seeded local cache from Firestore (%d incidents)", len(remote))
                except Exception:
                    pass
            incidents[incident_id] = {
                "metadata": metadata,
                "timeline": [],
                "final_decision": None,
                "created_at": _utcnow(),
            }
            self._write_file(self.incidents_file, incidents)
            logger.info(f"Memory: created incident {incident_id}")
        # Mirror to Firestore so it survives server restarts
        try:
            from core.firestore_memory import fs_save_incident
            fs_save_incident(fs_uid, incident_id, incidents[incident_id])
        except Exception:
            pass
        return incidents[incident_id]

    def delete_incident(self, incident_id: str):
        """Delete an incident record locally and from Firestore."""
        with _LOCK:
            incidents = self._read_file(self.incidents_file)
            if incident_id in incidents:
                del incidents[incident_id]
                self._write_file(self.incidents_file, incidents)
                logger.info(f"Memory: deleted incident {incident_id}")
        # Mirror deletion to Firestore — use resolved uid with explicit fallback so
        # a None uid doesn't silently target __public__ on behalf of a real user.
        try:
            from core.firestore_memory import fs_delete_incident
            fs_delete_incident(self._resolved_uid or "__public__", incident_id)
        except Exception as e:
            logger.debug(f"Failed to delete incident from Firestore: {e}")

    def get_all_incidents(self) -> dict:
        """Return all incidents keyed by incident_id."""
        return self._read_file(self.incidents_file)

    def get_incident(self, incident_id: str) -> Optional[dict]:
        ruid = self._resolved_uid
        if ruid:
            try:
                from api.state import register_incident_uid
                register_incident_uid(incident_id, ruid)
            except Exception:
                pass
        data = self._read_file(self.incidents_file).get(incident_id)
        if data:
            return data
        # Fallback: local file was wiped (server restart) — try Firestore
        try:
            from core.firestore_memory import fs_get_incident
            fs_data = fs_get_incident(self._resolved_uid or "__public__", incident_id)
            if fs_data:
                logger.info(f"[Memory] Recovered incident {incident_id} from Firestore")
                # Write back to local file so subsequent reads are fast
                with _LOCK:
                    incidents = self._read_file(self.incidents_file)
                    incidents[incident_id] = fs_data
                    self._write_file(self.incidents_file, incidents)
                return fs_data
        except Exception:
            pass
        return None

    def list_incidents(self) -> Dict[str, dict]:
        local = self._read_file(self.incidents_file)
        if local:
            return local
        # Fallback to Firestore on a fresh container (local wiped by restart)
        try:
            from core.firestore_memory import fs_list_incidents
            remote = fs_list_incidents(self._resolved_uid or "__public__")
            if remote:
                # Cache locally so subsequent reads don't hit Firestore every time
                with _LOCK:
                    self._write_file(self.incidents_file, remote)
            return remote
        except Exception:
            return {}

    def get_latest_incident_id(self) -> Optional[str]:
        incidents = self._read_file(self.incidents_file)
        if not incidents:
            # Fallback to Firestore
            try:
                from core.firestore_memory import fs_get_latest_incident_id
                return fs_get_latest_incident_id(self._resolved_uid)
            except Exception:
                return None
        return max(incidents, key=lambda k: incidents[k].get("created_at", ""))

    async def log_finding(
        self,
        incident_id: str,
        agent_name: str,
        finding: str,
        severity: int = 5,
        tags: Optional[list] = None,
    ) -> bool:
        """Agent logs a finding. Shared across all agents."""
        async with _ASYNC_LOCK:
            incidents = self._read_file(self.incidents_file)
            if incident_id not in incidents:
                logger.warning(f"Memory: incident {incident_id} not found for finding")
                return False
            incidents[incident_id]["timeline"].append({
                "agent": agent_name,
                "finding": finding,
                "severity": severity,
                "tags": tags or [],
                "timestamp": _utcnow(),
            })
            self._write_file(self.incidents_file, incidents)
            updated = incidents[incident_id]

            # Update agent learning profile
            profiles = self._read_file(self.agent_profiles_file)
            profile = profiles.setdefault(agent_name, {"findings_logged": 0, "incidents": []})
            profile["findings_logged"] += 1
            if incident_id not in profile["incidents"]:
                profile["incidents"].append(incident_id)
            profile["last_active"] = _utcnow()
            self._write_file(self.agent_profiles_file, profiles)
        # Mirror updated incident to Firestore
        try:
            from core.firestore_memory import fs_save_incident
            fs_save_incident(self._resolved_uid, incident_id, updated)
        except Exception:
            pass
        return True

    def set_final_decision(self, incident_id: str, decision: str) -> bool:
        with _LOCK:
            incidents = self._read_file(self.incidents_file)
            if incident_id not in incidents:
                return False
            incidents[incident_id]["final_decision"] = decision
            self._write_file(self.incidents_file, incidents)
            updated = incidents[incident_id]
        # Mirror to Firestore
        try:
            from core.firestore_memory import fs_save_incident
            fs_save_incident(self._resolved_uid, incident_id, updated)
        except Exception:
            pass
        return True

    async def query_similar_incidents(
        self,
        attack_technique: str,
        limit: int = 5,
    ) -> List[dict]:
        """Search memory for past incidents tagged with a MITRE technique."""
        incidents = self._read_file(self.incidents_file)
        results = []
        needle = attack_technique.strip().upper()
        for inc_id, inc in incidents.items():
            for event in inc.get("timeline", []):
                tags = [str(t).upper() for t in event.get("tags", [])]
                if needle in tags or needle in str(event.get("finding", "")).upper():
                    results.append({
                        "incident_id": inc_id,
                        "agent": event["agent"],
                        "finding": event["finding"],
                        "severity": event.get("severity", 5),
                        "timestamp": event["timestamp"],
                    })
        # Most recent matches first
        results.sort(key=lambda r: r["timestamp"], reverse=True)
        return results[:limit]

    # ── Learned attack patterns ───────────────────────────────────────────

    async def record_attack_pattern(
        self,
        mitre_id: str,
        detection_method: str,
        defense_action: str,
        success_rate: float = 0.8,
    ):
        """Team learns: this MITRE technique is best blocked by X."""
        with _LOCK:
            patterns = self._read_file(self.patterns_file)
            patterns.setdefault(mitre_id, []).append({
                "detection": detection_method,
                "defense": defense_action,
                "success_rate": success_rate,
                "learned_at": _utcnow(),
            })
            self._write_file(self.patterns_file, patterns)
            logger.info(f"Memory: learned defense recipe for {mitre_id}")

    async def get_defense_recipe(self, mitre_id: str) -> Optional[dict]:
        """Retrieve the team's best-known defense for a MITRE technique."""
        patterns = self._read_file(self.patterns_file)
        methods = patterns.get(mitre_id, [])
        if not methods:
            return None
        return max(methods, key=lambda x: x.get("success_rate", 0))

    # ── Commander chat history ────────────────────────────────────────────

    def _get_chat_file_for_session(self, session_id: Optional[str]) -> Path:
        if session_id:
            safe_id = "".join([c for c in session_id if c.isalnum() or c in ("-", "_")])
            if safe_id:
                return self.base_path / f"chat_history_{safe_id}.json"
        return self.chat_file

    def append_chat(self, role: str, content: str, meta: Optional[dict] = None, session_id: Optional[str] = None) -> dict:
        """Persist one chat turn (user or commander) so the conversation
        survives reloads and shows up in the Memory tab."""
        turn = {
            "role": role,
            "content": content,
            "meta": meta or {},
            "timestamp": _utcnow(),
        }
        chat_file = self._get_chat_file_for_session(session_id)
        with _LOCK:
            history = self._read_list(chat_file)
            history.append(turn)
            # Keep the on-disk log bounded; the UI only needs recent context
            self._write_file(chat_file, history[-500:])
        # Mirror to Firestore so chat survives server restarts
        try:
            from core.firestore_memory import fs_append_chat
            fs_append_chat(self._resolved_uid, session_id, turn)
        except Exception:
            pass
        return turn

    def get_chat_history(self, limit: int = 100, session_id: Optional[str] = None) -> List[dict]:
        chat_file = self._get_chat_file_for_session(session_id)
        local = self._read_list(chat_file)
        if local:
            return local[-limit:]
        # Fallback to Firestore on a fresh container
        try:
            from core.firestore_memory import fs_get_chat_history
            remote = fs_get_chat_history(self._resolved_uid, session_id, limit)
            if remote:
                with _LOCK:
                    self._write_file(chat_file, remote[-500:])
            return remote
        except Exception:
            return []

    def clear_chat_history(self, session_id: Optional[str] = None):
        chat_file = self._get_chat_file_for_session(session_id)
        with _LOCK:
            if session_id and chat_file.exists():
                try:
                    chat_file.unlink()
                    logger.info(f"Memory: unlinked session file {chat_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete session file {chat_file}: {e}")
            else:
                self._write_file(chat_file, [])
        # Mirror deletion to Firestore so deleted sessions don't resurrect on restart
        try:
            from core.firestore_memory import _chat_turns
            for doc in _chat_turns(self._resolved_uid, session_id).stream():
                doc.reference.delete()
            logger.info(f"Memory: cleared Firestore chat turns for session={session_id or 'default'}")
        except Exception as e:
            logger.debug(f"Memory: Firestore chat clear skipped: {e}")

    def clear_all(self):
        """Wipe everything: all deals, learned patterns, agent profiles, and chat history.
        Used by the Settings 'Reset & Clear All History' control."""
        with _LOCK:
            self._write_file(self.incidents_file, {})
            self._write_file(self.patterns_file, {})
            self._write_file(self.agent_profiles_file, {})
            self._write_file(self.chat_file, [])
            for p in self.base_path.glob("chat_history_*.json"):
                try:
                    p.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete session file {p}: {e}")
        logger.info("Memory: cleared ALL history (incidents, patterns, profiles, chat).")

    # ── Summaries ─────────────────────────────────────────────────────────

    def get_team_summary(self, incident_id: str) -> str:
        """Generate a plain-English summary of team findings."""
        inc = self.get_incident(incident_id)
        if not inc:
            return "Incident not found."
        summary = f"Incident {incident_id}:\n"
        summary += f"Threat Level: {inc['metadata'].get('threat_level', '?')}/10\n\n"
        summary += "Agent Findings:\n"
        for event in inc["timeline"]:
            summary += f"- {event['agent']}: {event['finding']} (severity: {event['severity']})\n"
        if inc.get("final_decision"):
            summary += f"\nFinal Decision: {inc['final_decision']}\n"
        return summary

    def get_memory_stats(self) -> dict:
        """High-level stats: how much the team has learned so far."""
        incidents = self._read_file(self.incidents_file)
        patterns = self._read_file(self.patterns_file)
        profiles = self._read_file(self.agent_profiles_file)
        return {
            "total_incidents": len(incidents),
            "total_findings": sum(len(i.get("timeline", [])) for i in incidents.values()),
            "learned_patterns": {k: len(v) for k, v in patterns.items()},
            "agent_profiles": profiles,
        }

    # ── IO ────────────────────────────────────────────────────────────────

    def _read_file(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except Exception as e:
            if path.exists():
                logger.warning("_read_file: corrupt or unreadable %s — %s", path, e)
            return {}

    def _read_list(self, path: Path) -> list:
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except Exception as e:
            if path.exists():
                logger.warning("_read_list: corrupt or unreadable %s — %s", path, e)
            return []

    def _write_file(self, path: Path, data):
        # Write to a temp file first, then rename atomically to prevent
        # a server crash mid-write from leaving a corrupt JSON file.
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)


# Global singleton shared by the API, the agents, and the MCP server
memory_graph = MemoryGraph()
