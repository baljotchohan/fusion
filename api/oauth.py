"""
OAuth 2.0 Authorization Server for FUSION MCP.

Implements the MCP Authorization spec (PKCE S256 + Dynamic Client Registration)
so claude.ai web, ChatGPT, and any MCP client can connect with a single click —
no manual JSON editing, no mcp-remote, no npx.

The issued access_token is fus_<firebase_uid>, identical to the personal MCP key
users copy from Settings, so the rest of the auth stack (mcp_security middleware,
core/auth.py get_uid) is completely unchanged.

ponytail: in-memory stores. Auth codes expire in 5 min; client registrations are
ephemeral per process. Upgrade path: back with Redis or RTDB if needed.
"""
import os
import uuid
import time
import hashlib
import base64
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse

logger = logging.getLogger("fusion.oauth")
router = APIRouter()

BASE_URL = os.getenv("FUSION_BASE_URL", "https://baljot07-fusion.hf.space")
FRONTEND_URL = os.getenv("FUSION_FRONTEND_URL", "https://fusionos.vercel.app")

_clients: dict = {}   # client_id → {redirect_uris, client_name}
_codes: dict = {}     # code → {uid, client_id, redirect_uri, code_challenge, expires}


# ── Discovery ──────────────────────────────────────────────────────────────────

@router.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    return {
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "registration_endpoint": f"{BASE_URL}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["mcp"],
    }


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    return {
        "resource": f"{BASE_URL}/mcp/",
        "authorization_servers": [BASE_URL],
        "bearer_methods_supported": ["header"],
    }


# ── Dynamic Client Registration ─────────────────────────────────────────────────

@router.post("/oauth/register")
async def register_client(request: Request):
    body = await request.json()
    client_id = str(uuid.uuid4())
    _clients[client_id] = {
        "redirect_uris": body.get("redirect_uris", []),
        "client_name": body.get("client_name", "Unknown"),
    }
    return JSONResponse({
        "client_id": client_id,
        "client_id_issued_at": int(time.time()),
        "redirect_uris": _clients[client_id]["redirect_uris"],
        "client_name": _clients[client_id]["client_name"],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }, status_code=201)


# ── Authorization ─────────────────────────────────────────────────────────────

@router.get("/oauth/authorize")
async def authorize(
    response_type: str = "code",
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
    scope: str = "mcp",
):
    """Redirect browser to the FUSION frontend OAuth consent/login page."""
    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "scope": scope,
    })
    return RedirectResponse(f"{FRONTEND_URL}/oauth?{params}", status_code=302)


# ── Callback (called by frontend after Firebase sign-in) ──────────────────────

@router.post("/oauth/callback")
async def oauth_callback(request: Request):
    """
    Frontend POSTs Firebase ID token here after user signs in.
    Returns a one-time authorization code that the MCP client exchanges for a token.
    """
    body = await request.json()
    firebase_token = body.get("firebase_token", "")
    client_id = body.get("client_id", "")
    redirect_uri = body.get("redirect_uri", "")
    state = body.get("state", "")
    code_challenge = body.get("code_challenge", "")

    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(firebase_token)
        uid = decoded["uid"]
    except Exception as e:
        logger.warning("OAuth callback: Firebase token verification failed: %s", e)
        return JSONResponse({"error": "invalid_token", "error_description": str(e)}, status_code=401)

    code = base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
    _codes[code] = {
        "uid": uid,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "expires": time.time() + 300,
    }
    return {"code": code, "state": state, "redirect_uri": redirect_uri}


# ── Token Exchange ────────────────────────────────────────────────────────────

@router.post("/oauth/token")
async def token_endpoint(
    grant_type: str = Form(""),
    code: str = Form(""),
    code_verifier: str = Form(""),
    client_id: str = Form(""),
    redirect_uri: str = Form(""),
):
    """Exchange authorization code for fus_<uid> access token."""
    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    entry = _codes.pop(code, None)
    if not entry:
        return JSONResponse({"error": "invalid_grant", "error_description": "Code not found or already used"}, status_code=400)

    if time.time() > entry["expires"]:
        return JSONResponse({"error": "invalid_grant", "error_description": "Code expired"}, status_code=400)

    if entry.get("code_challenge"):
        digest = hashlib.sha256(code_verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        if challenge != entry["code_challenge"]:
            return JSONResponse({"error": "invalid_grant", "error_description": "PKCE verification failed"}, status_code=400)

    return {
        "access_token": f"fus_{entry['uid']}",
        "token_type": "bearer",
        "scope": "mcp",
    }
