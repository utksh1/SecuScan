"""
API key authentication for SecuScan backend.

A random key is generated at startup and written to <data_dir>/.api_key.
Clients must supply it via:
  - Authorization: Bearer <key>
  - X-Api-Key: <key>
"""

import os
import secrets
from pathlib import Path

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

_api_key: str | None = None


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
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency — rejects requests that do not carry the correct API key.

    Accepts the key in either:
    - ``Authorization: Bearer <key>``
    - ``X-Api-Key: <key>``
    """
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
