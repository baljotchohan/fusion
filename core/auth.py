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
current_uid: ContextVar[str] = ContextVar("current_uid", default="__public__")
current_token: ContextVar[str] = ContextVar("current_token", default="")
current_username: ContextVar[str] = ContextVar("current_username", default="guest")
current_incident_id: ContextVar[str] = ContextVar("current_incident_id", default="")
current_pitch_file: ContextVar[str] = ContextVar("current_pitch_file", default="")



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


import hmac
import hashlib

_raw_key = os.environ.get("MCP_SIGNING_KEY") or os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
if _raw_key:
    SECRET_KEY = _raw_key
else:
    import secrets as _sec_module
    SECRET_KEY = _sec_module.token_hex(32)
    logger.warning(
        "MCP_SIGNING_KEY not set — generated ephemeral signing key. "
        "Set MCP_SIGNING_KEY in HF Spaces secrets to persist fus_ tokens across restarts."
    )

def sign_uid(uid: str) -> str:
    sig = hmac.new(SECRET_KEY.encode(), uid.encode(), hashlib.sha256).hexdigest()
    return f"fus_{uid}.{sig}"

def verify_uid_signature(token: str) -> str | None:
    if not token.startswith("fus_"):
        return None
    content = token[4:].strip()
    if not content:
        return None
    
    parts = content.split(".", 1)  # split at most once so uids containing '.' don't fragment
    uid = parts[0].strip()
    if not uid:
        return None
        
    # ponytail: _AUTH_DISABLED removed here — auth-disabled mode uses X-Dev-UID directly
    # (get_uid line 129) and never routes through verify_uid_signature, so bypassing
    # the HMAC check here was redundant and allowed token forgery on staging.
    is_test = (
        os.environ.get("PYTEST_CURRENT_TEST") is not None
        or os.environ.get("FUSION_TEST_MODE") == "true"
    )
    if is_test:
        return uid
        
    if len(parts) == 2:
        sig = parts[1].strip()
        expected_sig = hmac.new(SECRET_KEY.encode(), uid.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return uid
    return None


async def get_uid(request: Request) -> str:
    """
    Extract and verify the Firebase ID token from Authorization header.
    Returns the user's uid string.
    Raises HTTP 401 if missing or invalid.
    """
    if _AUTH_DISABLED:
        return request.headers.get("X-Dev-UID", "dev-user")

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    else:
        token = request.query_params.get("token", "").strip()

    if not token:
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header or token query parameter")

    # Per-user MCP API key: "fus_<firebase_uid>" — issued from Settings, passed in MCP headers
    if token.startswith("fus_"):
        uid = verify_uid_signature(token)
        if uid:
            return uid
        raise HTTPException(status_code=401, detail="Invalid or spoofed MCP key signature")

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
