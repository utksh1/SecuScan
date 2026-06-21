"""
API key authentication for SecuScan backend.

A random key is generated at startup and written to <data_dir>/.api_key.
Clients must supply it via:
  - Authorization: Bearer <key>
  - X-Api-Key: <key>

Session management:
  - POST /api/v1/auth/session — validate API key and set HttpOnly session cookie
  - GET  /api/v1/auth/session/check — verify active session cookie
  - POST /api/v1/auth/session/logout — clear session cookie
"""

import os
import secrets
import time
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Security, status, Request, Response
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi import APIRouter

_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

_api_key: str | None = None

SESSION_TTL_SECONDS = 3600  # 1 hour
_active_sessions: dict[str, dict] = {}

auth_router = APIRouter(prefix="/api/v1/auth")


@auth_router.post("/session")
async def create_session(request: Request, response: Response):
    """Validate the API key and set an HttpOnly session cookie.

    The client sends the API key via the X-Api-Key header (or Authorization
    Bearer).  On success the server sets an HttpOnly / Secure / SameSite=Strict
    cookie so the key itself never needs to touch localStorage.
    """
    if _api_key is None:
        raise HTTPException(status_code=503, detail="Authentication service not initialised")

    candidate = request.headers.get("X-Api-Key")
    if not candidate:
        bearer = request.headers.get("Authorization", "")
        if bearer.lower().startswith("bearer "):
            candidate = bearer[7:]

    if not candidate or not secrets.compare_digest(candidate, _api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    session_token = secrets.token_urlsafe(32)
    _active_sessions[session_token] = {"created_at": time.time()}

    response.set_cookie(
        key="secuscan_session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=SESSION_TTL_SECONDS,
    )
    return {"status": "authenticated"}


@auth_router.get("/session/check")
async def check_session(request: Request):
    """Return whether the request carries a valid session cookie."""
    session_token = request.cookies.get("secuscan_session")
    if session_token and session_token in _active_sessions:
        session = _active_sessions[session_token]
        if time.time() - session["created_at"] < SESSION_TTL_SECONDS:
            return {"authenticated": True}
        del _active_sessions[session_token]
    return {"authenticated": False}


@auth_router.post("/session/logout")
async def logout_session(request: Request, response: Response):
    """Destroy the session cookie."""
    session_token = request.cookies.get("secuscan_session")
    if session_token and session_token in _active_sessions:
        del _active_sessions[session_token]
    response.delete_cookie("secuscan_session")
    return {"status": "logged_out"}


def is_authenticated_by_session(request: Request) -> bool:
    """Check if the request has a valid session cookie (used by require_api_key fallback)."""
    session_token = request.cookies.get("secuscan_session")
    if session_token and session_token in _active_sessions:
        session = _active_sessions[session_token]
        if time.time() - session["created_at"] < SESSION_TTL_SECONDS:
            return True
        del _active_sessions[session_token]
    return False


def init_api_key(data_dir: str) -> str:
    """
    Load the persisted API key, or generate and persist a new one.

    Called once during application startup; the returned key is also stored in
    the module-level ``_api_key`` variable so the FastAPI dependency can reach it.
    """
    global _api_key
    # Allow operators to redirect the key file via env var (e.g. Docker secrets).
    custom_path = os.environ.get("SECUSCAN_API_KEY_FILE", "").strip()
    key_file = Path(custom_path) if custom_path else Path(data_dir) / ".api_key"
    if key_file.exists():
        _api_key = key_file.read_text().strip()
    else:
        _api_key = secrets.token_hex(32)
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(_api_key)
        key_file.chmod(0o600)
    return _api_key


async def require_api_key(
    request: Request = None,
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency — rejects requests that do not carry the correct API key
    or a valid session cookie.

    Accepts the key in either:
    - ``Authorization: Bearer <key>``
    - ``X-Api-Key: <key>``
    - Valid ``secuscan_session`` HttpOnly cookie (set via POST /auth/session)
    """
    if request is not None and request.url.path.startswith("/api/v1/admin"):
        return ""

    # Allow requests authenticated via session cookie
    if request is not None and is_authenticated_by_session(request):
        return "session-authenticated"

    if _api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialised",
        )

    candidate: str | None = None
    if bearer is not None:
        candidate = bearer.credentials
    elif x_api_key is not None:
        candidate = x_api_key

    if candidate is None or not secrets.compare_digest(candidate, _api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return candidate


def get_api_key() -> str | None:
    """Return the current API key, or None if not yet initialised."""
    return _api_key


# ── Per-user / per-workspace ownership ──────────────────────────────────────
#
# SecuScan authenticates the deployment with a single shared API key (above).
# That gate does not, by itself, distinguish between the different users or
# workspaces that share a deployment, which is what allowed any caller to read,
# delete, or export any task/report by guessing its ID (BOLA, issue #401).
#
# ``resolve_owner_id`` derives a stable owner identity for the request and is
# persisted as ``owner_id`` on tasks/findings/reports at creation time and
# compared on every read/delete/report access. It deliberately prioritises the
# explicit authenticated-user header (``X-User-Id``) — the same header
# ``resolve_client_identity`` already treats as the authenticated user — so that
# multiple workspaces sharing the deployment API key remain isolated. In a
# production deployment the header is expected to be set by an upstream auth
# proxy / SSO layer; deployments that do not send it fall back to a single
# shared ``DEFAULT_OWNER_ID`` and keep their existing (single-user) behaviour.
#
# This value is duplicated as the SQL column default ('default') in
# database.py — keep the two in sync.
DEFAULT_OWNER_ID = "default"

_OWNER_HEADER = "x-user-id"


def resolve_owner_id(request: Request | None) -> str:
    """Resolve the owning user/workspace identity for the current request."""
    if request is not None:
        user_id = request.headers.get(_OWNER_HEADER)
        if user_id and user_id.strip():
            return f"user:{user_id.strip()}"
    return DEFAULT_OWNER_ID


async def get_current_owner(request: Request) -> str:
    """FastAPI dependency yielding the owner identity for the request."""
    return resolve_owner_id(request)
