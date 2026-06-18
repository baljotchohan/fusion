# core/rtdb.py
"""
Firebase Realtime Database — durable, per-user session storage.

Every deal verdict, chat exchange, and session event is written here so data
survives HF Spaces redeployments. The Admin SDK bypasses security rules, so
this module is backend-only. Falls back silently if FIREBASE_DATABASE_URL is
not configured (local dev without RTDB).

Data layout:
  /users/{uid}/deals/{deal_id}       — final verdict + partner reports
  /users/{uid}/chats/{push_id}       — each chat message + response
  /users/{uid}/sessions/{session_id} — deal session lifecycle
  /users/{uid}/activity/{push_id}    — page visits, trigger events, etc.
  /users/{uid}/profile               — display name, email, last seen
"""
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("fusion.rtdb")

_db = None
_ready = False


def _init() -> bool:
    global _db, _ready
    if _db is not None:
        return True  # already connected

    url = os.environ.get("FIREBASE_DATABASE_URL", "").strip()
    if not url:
        if not _ready:
            logger.info("FIREBASE_DATABASE_URL not set — RTDB writes disabled")
        _ready = True
        return False

    try:
        import firebase_admin
        from firebase_admin import db as _fdb

        if not firebase_admin._apps:
            # Admin not yet initialized — don't set _ready so we retry next call
            logger.debug("RTDB init deferred: Firebase Admin not ready yet")
            return False

        _fdb.reference("/")   # validates the URL without a network round-trip
        _db = _fdb
        _ready = True
        logger.info("Firebase RTDB ready ✓  url=%s", url)
        return True
    except Exception as exc:
        logger.error("RTDB init failed: %s", exc)
        _ready = True   # permanent failure — stop retrying
        return False


def _ref(path: str):
    if _db is None and not _init():
        return None
    try:
        return _db.reference(path)
    except Exception as exc:
        logger.debug("RTDB _ref(%s) failed: %s", path, exc)
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Public write helpers ───────────────────────────────────────────────────────

def write_deal(uid: str, deal_id: str, data: dict) -> bool:
    """Upsert a deal record — call after verdict is produced."""
    ref = _ref(f"/users/{uid}/deals/{deal_id}")
    if ref is None:
        return False
    try:
        ref.update({**data, "updatedAt": _now()})
        return True
    except Exception as exc:
        logger.error("RTDB write_deal %s/%s: %s", uid, deal_id, exc)
        return False


def write_chat(uid: str, session_id: str, message: str,
               response: str, intent: str = "general") -> bool:
    """Append one chat exchange (user message + assistant reply)."""
    ref = _ref(f"/users/{uid}/chats")
    if ref is None:
        return False
    try:
        ref.push({
            "sessionId": session_id or "default",
            "message": message[:1000],
            "response": response[:2000],
            "intent": intent,
            "timestamp": _now(),
        })
        return True
    except Exception as exc:
        logger.error("RTDB write_chat %s: %s", uid, exc)
        return False


def write_session(uid: str, session_id: str, data: dict) -> bool:
    """Create or update a session record (deal lifecycle)."""
    ref = _ref(f"/users/{uid}/sessions/{session_id}")
    if ref is None:
        return False
    try:
        ref.update({**data, "updatedAt": _now()})
        return True
    except Exception as exc:
        logger.error("RTDB write_session %s/%s: %s", uid, session_id, exc)
        return False


def write_activity(uid: str, activity_type: str, data: dict | None = None) -> bool:
    """Append a lightweight activity event (trigger, upload, reset, etc.)."""
    ref = _ref(f"/users/{uid}/activity")
    if ref is None:
        return False
    try:
        ref.push({
            "type": activity_type,
            "data": data or {},
            "timestamp": _now(),
        })
        return True
    except Exception as exc:
        logger.error("RTDB write_activity %s/%s: %s", uid, activity_type, exc)
        return False


def upsert_profile(uid: str, name: str | None, email: str | None,
                   picture: str | None = None) -> bool:
    """Keep a lightweight profile node so the Firebase console shows who's who."""
    ref = _ref(f"/users/{uid}/profile")
    if ref is None:
        return False
    payload: dict = {"lastSeen": _now()}
    if name:
        payload["displayName"] = name
    if email:
        payload["email"] = email
    if picture:
        payload["photoURL"] = picture
    try:
        ref.update(payload)
        return True
    except Exception as exc:
        logger.error("RTDB upsert_profile %s: %s", uid, exc)
        return False
