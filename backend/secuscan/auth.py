"""
API key authentication for SecuScan backend.

A random key is generated at startup and written to <data_dir>/.api_key as
JSON (``{"key": ..., "created_at": <epoch seconds>}``), which lets the key
carry an age/expiry (issue #1619) instead of being valid indefinitely with
no revocation path short of deleting the file and restarting the process.
Older deployments with a plaintext key file are migrated in place on next
boot -- the existing key is kept, wrapped with a fresh created_at.

Clients must supply it via:
  - Authorization: Bearer <key>
  - X-Api-Key: <key>

Rotation and expiry (admin-key-gated, issue #1619):
  - POST /api/v1/admin/api-key/rotate — generate a new key, invalidate the old one
  - GET  /api/v1/admin/api-key/status — report key age and (if configured) expiry
  - SECUSCAN_API_KEY_TTL_SECONDS (default 0 = disabled) rejects requests once the
    key is older than the configured TTL, forcing rotation.

Session management (signed cookie, no server-side state):
  - POST /api/v1/auth/session — validate API key and set HttpOnly session cookie
  - GET  /api/v1/auth/session/check — verify active session cookie
  - POST /api/v1/auth/session/logout — clear session cookie
"""

import base64
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, HTTPException, Security, status, Request, Response
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi import APIRouter

_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

_api_key: str | None = None
_api_key_created_at: float | None = None
_api_key_file: Path | None = None

SESSION_TTL_SECONDS = 3600  # 1 hour
COOKIE_NAME = "secuscan_session"
_SIGNING_KEY: bytes | None = None


def _init_signing_key() -> bytes:
    global _SIGNING_KEY
    if _SIGNING_KEY is None:
        _SIGNING_KEY = secrets.token_bytes(32)
    return _SIGNING_KEY


def _make_signed_token() -> str:
    key = _init_signing_key()
    expires = int(time.time()) + SESSION_TTL_SECONDS
    payload = json.dumps({"s": secrets.token_urlsafe(16), "e": expires}, separators=(",", ":")).encode()
    payload_b64 = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(key, payload, "sha256").hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_signed_token(token: str) -> bool:
    key = _init_signing_key()
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        payload_b64, sig = parts
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = base64.urlsafe_b64decode(payload_b64.encode())
        expected_sig = hmac.new(key, payload, "sha256").hexdigest()
        if not secrets.compare_digest(expected_sig, sig):
            return False
        data = json.loads(payload)
        if time.time() > data["e"]:
            return False
        return True
    except Exception:
        return False


def _cookie_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto.lower() == "https":
        return True
    return request.url.scheme == "https"


auth_router = APIRouter(prefix="/api/v1/auth")


@auth_router.post("/session")
async def create_session(request: Request, response: Response):
    """Validate the API key and set an HttpOnly session cookie.

    The client sends the API key via the X-Api-Key header (or Authorization
    Bearer). On success the server sets a signed HttpOnly session cookie so
    the key itself never needs to touch localStorage. The cookie is self-
    contained (HMAC-signed) and requires no server-side session store.
    The Secure flag is only set when the request arrives over HTTPS or
    carries an X-Forwarded-Proto: https header, preserving HTTP localhost
    development.
    """
    if _api_key is None:
        raise HTTPException(
            status_code=503, detail="Authentication service not initialised"
        )

    candidate = request.headers.get("X-Api-Key")
    if not candidate:
        bearer = request.headers.get("Authorization", "")
        if bearer.lower().startswith("bearer "):
            candidate = bearer[7:]

    if not candidate or not secrets.compare_digest(candidate, _api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    from .config import settings

    ttl = settings.api_key_ttl_seconds
    if ttl > 0 and _api_key_created_at is not None and time.time() - _api_key_created_at > ttl:
        raise HTTPException(
            status_code=401,
            detail="API key has expired. An administrator must rotate it via "
            "POST /api/v1/admin/api-key/rotate.",
        )

    token = _make_signed_token()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="strict",
        max_age=SESSION_TTL_SECONDS,
    )
    return {"status": "authenticated"}


@auth_router.get("/session/check")
async def check_session(request: Request):
    """Return whether the request carries a valid signed session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if token and _verify_signed_token(token):
        return {"authenticated": True}
    return {"authenticated": False}


@auth_router.post("/session/logout")
async def logout_session(request: Request, response: Response):
    """Destroy the session cookie."""
    response.delete_cookie(COOKIE_NAME)
    return {"status": "logged_out"}


def is_authenticated_by_session(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    return bool(token and _verify_signed_token(token))


def _resolve_key_file(data_dir: str) -> Path:
    # Allow operators to redirect the key file via env var (e.g. Docker secrets).
    custom_path = os.environ.get("SECUSCAN_API_KEY_FILE", "").strip()
    return Path(custom_path) if custom_path else Path(data_dir) / ".api_key"


def _write_key_file(key_file: Path, key: str, created_at: float) -> None:
    key_file.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"key": key, "created_at": created_at})
    # Write to a temp file in the same directory and atomically rename, so a
    # crash mid-write can never leave a truncated/corrupt key file behind.
    tmp_path = key_file.with_suffix(f"{key_file.suffix}.tmp")
    tmp_path.write_text(payload)
    tmp_path.chmod(0o600)
    tmp_path.replace(key_file)


def init_api_key(data_dir: str) -> str:
    """
    Load the persisted API key, or generate and persist a new one.

    Called once during application startup; the returned key is also stored in
    the module-level ``_api_key`` variable so the FastAPI dependency can reach it.

    The key file is JSON (``{"key": ..., "created_at": ...}``) so the key's age
    can be checked against ``SECUSCAN_API_KEY_TTL_SECONDS`` and reported via
    ``GET /api/v1/admin/api-key/status``. A pre-existing plaintext key file
    (from before issue #1619) is migrated in place: the key is kept, wrapped
    with a fresh ``created_at`` timestamp.
    """
    global _api_key, _api_key_created_at, _api_key_file
    key_file = _resolve_key_file(data_dir)
    _api_key_file = key_file

    if key_file.exists():
        raw = key_file.read_text().strip()
        try:
            data = json.loads(raw)
            _api_key = str(data["key"])
            _api_key_created_at = float(data["created_at"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # Legacy plaintext key file -- keep the existing key, but it has
            # no known creation time, so treat it as freshly issued and
            # migrate the file to the new JSON format.
            _api_key = raw
            _api_key_created_at = time.time()
            _write_key_file(key_file, _api_key, _api_key_created_at)
    else:
        _api_key = secrets.token_hex(32)
        _api_key_created_at = time.time()
        _write_key_file(key_file, _api_key, _api_key_created_at)

    return _api_key


def rotate_api_key() -> dict:
    """Generate a new API key, persist it, and invalidate the old one.

    The old key stops working the instant this returns, since ``_api_key``
    is the single value ``require_api_key`` compares against -- there is no
    grace period. Returns the new key so the caller (an admin-authenticated
    request) can retrieve it; there is no other way to read it back out,
    since the key file is not exposed over the API.
    """
    global _api_key, _api_key_created_at
    if _api_key_file is None:
        raise RuntimeError("API key not initialised -- call init_api_key() first")

    new_key = secrets.token_hex(32)
    created_at = time.time()
    _write_key_file(_api_key_file, new_key, created_at)
    _api_key = new_key
    _api_key_created_at = created_at
    return {"key": new_key, "created_at": created_at}


def get_api_key_status() -> dict:
    """Report the current key's age and, if SECUSCAN_API_KEY_TTL_SECONDS is
    set, when it expires -- without exposing the key itself."""
    from .config import settings

    ttl = settings.api_key_ttl_seconds
    age_seconds = None
    expires_at = None
    expired = False
    if _api_key_created_at is not None:
        age_seconds = time.time() - _api_key_created_at
        if ttl > 0:
            expires_at = _api_key_created_at + ttl
            expired = age_seconds > ttl
    return {
        "created_at": _api_key_created_at,
        "age_seconds": age_seconds,
        "ttl_seconds": ttl or None,
        "expires_at": expires_at,
        "expired": expired,
    }


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
        # Admin endpoints have their own separate verify_admin_access dependency.
        # We bypass require_api_key verification to avoid blocking valid admin key requests.
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

    from .config import settings

    ttl = settings.api_key_ttl_seconds
    if ttl > 0 and _api_key_created_at is not None and time.time() - _api_key_created_at > ttl:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired. An administrator must rotate it via "
            "POST /api/v1/admin/api-key/rotate.",
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
