# core/rtdb.py
"""
Firebase Realtime Database — durable, per-user session storage.
Clean tree-form structure using human-readable usernames and separate sections.
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


def clean_key(s: str) -> str:
    """Normalize a string to be a safe Firebase Realtime Database path key."""
    if not s:
        return "unknown"
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")).lower()


def get_user_folder(uid: str) -> str:
    """Map a Firebase UID to a clean human-readable username key."""
    if uid == "__public__":
        return "__public__"
    if uid == "__mcp_client__":
        return "mcp_client"
    
    # Check ContextVar current_username first
    try:
        from core.auth import current_username
        uname = current_username.get()
        if uname and uname not in ("guest", "__public__", "__mcp_client__"):
            return clean_key(uname)
    except Exception:
        pass
    
    # Fallback: guest or unknown username -> guest_xxxxx
    if uid and len(uid) > 5:
        return f"guest_{uid[-5:]}".lower()
    return clean_key(uid or "guest")


# ── Public write helpers ───────────────────────────────────────────────────────

def write_deal(uid: str, deal_id: str, data: dict) -> bool:
    """Upsert a deal record under /users/{username}/deals/{deal_id}."""
    username = get_user_folder(uid)
    ref = _ref(f"/users/{username}/deals/{deal_id}")
    if ref is None:
        return False
    try:
        ref.update({**data, "updatedAt": _now()})
        return True
    except Exception as exc:
        logger.error("RTDB write_deal %s/%s: %s", username, deal_id, exc)
        return False


def write_chat(uid: str, session_id: str, message: str,
               response: str, intent: str = "general") -> bool:
    """Append one chat exchange under /users/{username}/chats."""
    username = get_user_folder(uid)
    ref = _ref(f"/users/{username}/chats")
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
        logger.error("RTDB write_chat %s: %s", username, exc)
        return False


def write_review_message(uid: str, message: str) -> bool:
    """Save user reported issue/error to the dedicated root /issues/{username} section."""
    username = get_user_folder(uid)
    ref = _ref(f"/issues/{username}")
    if ref is None:
        return False
    try:
        ref.push({
            "message": message[:2000],
            "timestamp": _now(),
            "realName": username,
        })
        return True
    except Exception as exc:
        logger.error("RTDB write_review_message %s: %s", username, exc)
        return False


def write_session(uid: str, session_id: str, data: dict) -> bool:
    """Create or update a session record under /users/{username}/sessions/{session_id}."""
    username = get_user_folder(uid)
    ref = _ref(f"/users/{username}/sessions/{session_id}")
    if ref is None:
        return False
    try:
        ref.update({**data, "updatedAt": _now()})
        return True
    except Exception as exc:
        logger.error("RTDB write_session %s/%s: %s", username, session_id, exc)
        return False


def write_activity(uid: str, activity_type: str, data: dict | None = None) -> bool:
    """Append a lightweight activity event under /users/{username}/activity and global /diagnostics/visits."""
    username = get_user_folder(uid)
    ref = _ref(f"/users/{username}/activity")
    if ref is None:
        return False
    try:
        payload = {
            "type": activity_type,
            "data": data or {},
            "timestamp": _now(),
        }
        ref.push(payload)
        
        # Log to global /diagnostics/visits
        try:
            diag_ref = _ref("/diagnostics/visits")
            if diag_ref is not None:
                email = data.get("email") if data else None
                diag_ref.push({
                    "username": username,
                    "type": activity_type,
                    "email": email or "anonymous",
                    "timestamp": _now(),
                    "details": data or {}
                })
        except Exception as e:
            logger.debug("Failed to write to global /diagnostics/visits: %s", e)

        return True
    except Exception as exc:
        logger.error("RTDB write_activity %s/%s: %s", username, activity_type, exc)
        return False


def upsert_profile(uid: str, name: str | None, email: str | None,
                   picture: str | None = None, ip: str | None = None,
                   user_agent: str | None = None) -> bool:
    """Keep profile node under /users/{username}/profile containing IP & device info."""
    username = get_user_folder(uid)
    ref = _ref(f"/users/{username}/profile")
    if ref is None:
        return False
    payload: dict = {"lastSeen": _now()}
    if name:
        payload["displayName"] = name
    if email:
        payload["email"] = email
    if picture:
        payload["photoURL"] = picture
    if ip:
        payload["ip"] = ip
    if user_agent:
        payload["device"] = user_agent
    try:
        ref.update(payload)
        return True
    except Exception as exc:
        logger.error("RTDB upsert_profile %s: %s", username, exc)
        return False


def write_connection_log(uid: str, ip: str, details: dict) -> bool:
    """Log site entry telemetry under dedicated /connections/{username} root."""
    username = get_user_folder(uid)
    ref = _ref(f"/connections/{username}")
    if ref is None:
        return False
    try:
        ref.push({
            "ip": ip,
            "timestamp": _now(),
            "realName": username,
            **details
        })
        return True
    except Exception as exc:
        logger.error("RTDB write_connection_log %s: %s", username, exc)
        return False


def write_mcp_usage(uid: str, tool_name: str, arguments: dict) -> bool:
    """Log MCP tool execution events to dedicated /mcp_usage/{username} root."""
    username = get_user_folder(uid)
    ref = _ref(f"/mcp_usage/{username}")
    if ref is None:
        return False
    try:
        ref.push({
            "tool": tool_name,
            "arguments": arguments,
            "timestamp": _now(),
            "realName": username,
        })
        return True
    except Exception as exc:
        logger.error("RTDB write_mcp_usage %s: %s", username, exc)
        return False


def clear_user_data(uid: str) -> bool:
    """Clear all data for the user in the Realtime Database under /users/{username}."""
    username = get_user_folder(uid)
    ref = _ref(f"/users/{username}")
    if ref is None:
        return False
    try:
        ref.delete()
        # Also clear user's connection logs, mcp usage, and issues for completeness
        for path in [f"/connections/{username}", f"/issues/{username}", f"/mcp_usage/{username}"]:
            r = _ref(path)
            if r is not None:
                r.delete()
        return True
    except Exception as exc:
        logger.error("RTDB clear_user_data %s: %s", username, exc)
        return False
