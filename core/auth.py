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

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Request, HTTPException

logger = logging.getLogger("fusion.auth")

# ── Initialize Firebase Admin SDK once ────────────────────────────────────────
_initialized = False

def _init_firebase():
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return

    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64", "")
    if not b64:
        logger.warning(
            "FIREBASE_SERVICE_ACCOUNT_B64 not set — auth verification will fail. "
            "All requests will be rejected unless running with FUSION_AUTH_DISABLED=true."
        )
        _initialized = True
        return

    try:
        sa_dict = json.loads(base64.b64decode(b64).decode("utf-8"))
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
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

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
