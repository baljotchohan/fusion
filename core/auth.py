# core/auth.py
"""
Firebase ID token verification for FastAPI endpoints.
The service account JSON is stored as a base64-encoded env var (HF Spaces Secrets),
so no file needs to be committed to the repo.
"""
import os
import json
import base64
import logging
from contextvars import ContextVar

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Request, HTTPException

logger = logging.getLogger("fusion.auth")

# ContextVar to track the authenticated user uid for the current request (e.g. MCP tool calls)
current_uid: ContextVar[str] = ContextVar("current_uid", default="__mcp_client__")
current_token: ContextVar[str] = ContextVar("current_token", default="")
current_username: ContextVar[str] = ContextVar("current_username", default="guest")



# ── Initialize Firebase Admin SDK once ────────────────────────────────────────
_initialized = False

def _init_firebase():
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return

    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64", "").strip()

    if not sa_json and not b64:
        logger.warning(
            "Neither FIREBASE_SERVICE_ACCOUNT_JSON nor FIREBASE_SERVICE_ACCOUNT_B64 set — auth verification will fail. "
            "All requests will be rejected unless running with FUSION_AUTH_DISABLED=true."
        )
        _initialized = True
        return

    try:
        if sa_json:
            sa_dict = json.loads(sa_json)
        else:
            # HF Spaces strips trailing '=' from secrets — re-pad before decoding
            b64_padded = b64 + "=" * (-len(b64) % 4)
            sa_dict = json.loads(base64.b64decode(b64_padded).decode("utf-8"))
        
        cred = credentials.Certificate(sa_dict)
        db_url = os.environ.get("FIREBASE_DATABASE_URL", "").strip()
        options = {"databaseURL": db_url} if db_url else {}
        firebase_admin.initialize_app(cred, options)
        logger.info("Firebase Admin SDK initialized ✓%s", " (RTDB enabled)" if db_url else " (no RTDB URL)")
    except Exception as e:
        logger.error(f"Firebase Admin SDK init failed: {e}")
    _initialized = True


_init_firebase()

_AUTH_DISABLED = os.environ.get("FUSION_AUTH_DISABLED", "").lower() == "true"
if _AUTH_DISABLED:
    _env = os.environ.get("ENVIRONMENT", "dev").lower()
    if _env in ("production", "prod"):
        raise RuntimeError("FUSION_AUTH_DISABLED must not be set in production — remove it from HF Space secrets.")
    logger.warning("⚠️  Auth is DISABLED (FUSION_AUTH_DISABLED=true) — any caller can set X-Dev-UID. Dev/staging only.")


async def get_uid(request: Request) -> str:
    """
    Extract and verify the Firebase ID token from Authorization header.
    Returns the user's uid string.
    Raises HTTP 401 if missing or invalid.
    """
    if _AUTH_DISABLED:
        # Dev shortcut: skip auth, return a fixed dev uid
        return request.headers.get("X-Dev-UID", "dev-user")

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    else:
        token = request.query_params.get("token", "").strip()

    if not token:
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header or token query parameter")

    try:
        decoded = firebase_auth.verify_id_token(token)
        return decoded["uid"]
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expired — please sign in again")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_uid_optional(request: Request) -> str | None:
    """Returns uid or None — for public endpoints that work with or without auth."""
    try:
        return await get_uid(request)
    except HTTPException:
        return None
