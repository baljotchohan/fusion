# core/firestore_memory.py
"""
Firestore write-through / read-fallback for MemoryGraph incidents.

Collection layout:
  fusion_incidents/{uid}/incidents/{incident_id}  -> incident dict

This means deal data survives HF Spaces server restarts.
All functions are best-effort: errors are logged at DEBUG level and
the caller falls back to local JSON files transparently.
"""
import json
import logging
from typing import Optional

logger = logging.getLogger("fusion.firestore_memory")


def _uid_key(uid: Optional[str]) -> str:
    return uid or "__public__"


def _inflate_pitch_data(data: dict) -> dict:
    """Re-inflate pitch_data if it was stored as a JSON string."""
    meta = data.get("metadata", {})
    if isinstance(meta.get("pitch_data"), str):
        try:
            meta = dict(meta)
            meta["pitch_data"] = json.loads(meta["pitch_data"])
            data = dict(data)
            data["metadata"] = meta
        except Exception:
            pass
    return data


def _deflate_pitch_data(data: dict) -> dict:
    """Convert pitch_data dict → JSON string to stay under Firestore 1 MB limit."""
    meta = data.get("metadata", {})
    if "pitch_data" in meta and isinstance(meta["pitch_data"], dict):
        meta = dict(meta)
        meta["pitch_data"] = json.dumps(meta["pitch_data"], default=str)[:900_000]
        data = dict(data)
        data["metadata"] = meta
    return data


def _collection(uid: Optional[str]):
    from firebase_admin import firestore as _fs
    db = _fs.client()
    return (
        db.collection("fusion_incidents")
          .document(_uid_key(uid))
          .collection("incidents")
    )


# ── Write ──────────────────────────────────────────────────────────────────────

def fs_save_incident(uid: Optional[str], incident_id: str, data: dict) -> None:
    """Mirror one incident to Firestore (best-effort)."""
    try:
        _collection(uid).document(incident_id).set(_deflate_pitch_data(data))
        logger.debug(f"[FS] saved incident {incident_id} for uid={_uid_key(uid)}")
    except Exception as e:
        logger.debug(f"[FS] save_incident skipped: {e}")


# ── Read ───────────────────────────────────────────────────────────────────────

def fs_get_incident(uid: Optional[str], incident_id: str) -> Optional[dict]:
    """Fetch one incident from Firestore. Returns None if not found/unavailable."""
    try:
        doc = _collection(uid).document(incident_id).get()
        if not doc.exists:
            return None
        return _inflate_pitch_data(doc.to_dict() or {})
    except Exception as e:
        logger.debug(f"[FS] get_incident skipped: {e}")
        return None


def fs_list_incidents(uid: Optional[str]) -> dict:
    """Return all incidents for a uid from Firestore as {incident_id: data}."""
    try:
        docs = _collection(uid).stream()
        return {doc.id: _inflate_pitch_data(doc.to_dict() or {}) for doc in docs}
    except Exception as e:
        logger.debug(f"[FS] list_incidents skipped: {e}")
        return {}


def fs_get_latest_incident_id(uid: Optional[str]) -> Optional[str]:
    """Return the most-recently created incident id from Firestore."""
    incidents = fs_list_incidents(uid)
    if not incidents:
        return None
    return max(incidents, key=lambda k: incidents[k].get("created_at", ""))
