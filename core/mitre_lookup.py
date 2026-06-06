# core/mitre_lookup.py
"""
Utility module to look up threat tactics and techniques from the local
MITRE ATT&CK Enterprise dataset JSON file.
"""
import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger("argus.mitre")

class MITREDatabase:
    def __init__(self, json_path: str = "data/enterprise-attack.json"):
        self.techniques: Dict[str, dict] = {}
        self.mitigations: Dict[str, dict] = {}
        self.json_path = json_path
        self._loaded = False

    def load_db(self):
        if self._loaded:
            return
        
        if not os.path.exists(self.json_path):
            logger.warning(f"MITRE database not found at {self.json_path}. Run download script first.")
            return

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            
            for obj in raw.get("objects", []):
                obj_type = obj.get("type")
                if obj_type == "attack-pattern":
                    # Extract technique ID (e.g. T1566, T1059)
                    for ref in obj.get("external_references", []):
                        if ref.get("source_name") == "mitre-attack":
                            tid = ref.get("external_id", "")
                            self.techniques[tid.upper()] = {
                                "id": tid,
                                "name": obj.get("name", ""),
                                "description": obj.get("description", "")[:400] + "...",
                                "tactic": self._get_tactic(obj)
                            }
                elif obj_type == "course-of-action":
                    for ref in obj.get("external_references", []):
                        if ref.get("source_name") == "mitre-attack":
                            mid = ref.get("external_id", "")
                            self.mitigations[mid.upper()] = {
                                "id": mid,
                                "name": obj.get("name", ""),
                                "description": obj.get("description", "")[:400] + "..."
                            }
            self._loaded = True
            logger.info(f"Loaded {len(self.techniques)} techniques and {len(self.mitigations)} mitigations from MITRE database.")
        except Exception as e:
            logger.error(f"Failed to load MITRE database: {e}")

    def _get_tactic(self, obj: dict) -> str:
        for phase in obj.get("kill_chain_phases", []):
            if phase.get("kill_chain_name") == "mitre-attack":
                return phase.get("phase_name", "unknown")
        return "unknown"

    def search(self, keyword: str) -> List[Dict]:
        """Search techniques by keyword in name or description."""
        self.load_db()
        keyword = keyword.lower()
        results = []
        for tid, tech in self.techniques.items():
            if keyword in tech["name"].lower() or keyword in tech["description"].lower():
                results.append(tech)
        return results[:5]  # Limit to top 5 for context budgeting

    def get_by_id(self, technique_id: str) -> Dict:
        """Get technique by exact ID like T1566."""
        self.load_db()
        return self.techniques.get(technique_id.upper(), {})

# Global singleton
_db = MITREDatabase()

def search_ttp(keyword: str) -> List[Dict]:
    return _db.search(keyword)

def get_technique(tid: str) -> Dict:
    return _db.get_by_id(tid)
