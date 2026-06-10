# core/memory_graph.py
"""
Graphify-backed shared incident memory for all 9 agents.

Every incident is logged to a shared on-disk graph (JSON namespace under
./argus_memory). Agents query past incidents and learned defense recipes
before acting, so the team gets measurably faster on repeat attacks.

Files:
  - incidents.json:        all past incidents with per-agent finding timelines
  - attack_patterns.json:  learned defenses per MITRE technique
  - agent_profiles.json:   per-agent learning stats (findings, incidents seen)
"""
import json
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("argus.memory_graph")

# Single process-wide lock: the JSON namespace is small and write
# contention only happens during agent fan-out, so coarse locking is fine.
_LOCK = threading.Lock()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryGraph:
    """Shared incident memory graph used by every ARGUS agent."""

    def __init__(self, graphify_dir: str = "./argus_memory"):
        self.base_path = Path(graphify_dir)
        self.base_path.mkdir(exist_ok=True)
        self.incidents_file = self.base_path / "incidents.json"
        self.patterns_file = self.base_path / "attack_patterns.json"
        self.agent_profiles_file = self.base_path / "agent_profiles.json"
        self.chat_file = self.base_path / "chat_history.json"
        self._ensure_files()

    def _ensure_files(self):
        for f in [self.incidents_file, self.patterns_file, self.agent_profiles_file]:
            if not f.exists():
                f.write_text(json.dumps({}, indent=2))
        if not self.chat_file.exists():
            self.chat_file.write_text(json.dumps([], indent=2))

    # ── Incidents ─────────────────────────────────────────────────────────

    def create_incident(self, incident_id: str, metadata: dict) -> dict:
        """Start a new incident record.

        incident_id: e.g. "INC-20260610-084500"
        metadata:    e.g. {"trigger": "phishing_email", "threat_level": 7}
        """
        with _LOCK:
            incidents = self._read_file(self.incidents_file)
            incidents[incident_id] = {
                "metadata": metadata,
                "timeline": [],
                "final_decision": None,
                "created_at": _utcnow(),
            }
            self._write_file(self.incidents_file, incidents)
            logger.info(f"Memory: created incident {incident_id}")
            return incidents[incident_id]

    def get_incident(self, incident_id: str) -> Optional[dict]:
        return self._read_file(self.incidents_file).get(incident_id)

    def list_incidents(self) -> Dict[str, dict]:
        return self._read_file(self.incidents_file)

    def get_latest_incident_id(self) -> Optional[str]:
        incidents = self._read_file(self.incidents_file)
        if not incidents:
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
        with _LOCK:
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

            # Update agent learning profile
            profiles = self._read_file(self.agent_profiles_file)
            profile = profiles.setdefault(agent_name, {"findings_logged": 0, "incidents": []})
            profile["findings_logged"] += 1
            if incident_id not in profile["incidents"]:
                profile["incidents"].append(incident_id)
            profile["last_active"] = _utcnow()
            self._write_file(self.agent_profiles_file, profiles)
        return True

    def set_final_decision(self, incident_id: str, decision: str) -> bool:
        with _LOCK:
            incidents = self._read_file(self.incidents_file)
            if incident_id not in incidents:
                return False
            incidents[incident_id]["final_decision"] = decision
            self._write_file(self.incidents_file, incidents)
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

    def append_chat(self, role: str, content: str, meta: Optional[dict] = None) -> dict:
        """Persist one chat turn (user or commander) so the conversation
        survives reloads and shows up in the Memory tab."""
        turn = {
            "role": role,
            "content": content,
            "meta": meta or {},
            "timestamp": _utcnow(),
        }
        with _LOCK:
            history = self._read_list(self.chat_file)
            history.append(turn)
            # Keep the on-disk log bounded; the UI only needs recent context
            self._write_file(self.chat_file, history[-500:])
        return turn

    def get_chat_history(self, limit: int = 100) -> List[dict]:
        return self._read_list(self.chat_file)[-limit:]

    def clear_chat_history(self):
        with _LOCK:
            self._write_file(self.chat_file, [])

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
        except Exception:
            return {}

    def _read_list(self, path: Path) -> list:
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_file(self, path: Path, data):
        path.write_text(json.dumps(data, indent=2))


# Global singleton shared by the API, the agents, and the MCP server
memory_graph = MemoryGraph()
