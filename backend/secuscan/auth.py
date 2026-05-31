"""
API key authentication dependency for SecuScan.

On first startup, if SECUSCAN_API_KEY is not set, a random key is generated,
written to data/api_key.txt, and logged once so the user can copy it.
Every non-health-check request must supply the key as:
  - Authorization: Bearer <key>   OR
  - X-Api-Key: <key>
"""
from __future__ import annotations

import logging
import secrets
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

_API_KEY_FILE = Path(__file__).resolve().parent.parent / "data" / "api_key.txt"


@lru_cache(maxsize=1)
def _get_active_key() -> str:
    from .config import settings
    if settings.api_key:
        return settings.api_key
    if _API_KEY_FILE.exists():
        key = _API_KEY_FILE.read_text().strip()
        if key:
            return key
    key = secrets.token_hex(32)
    _API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _API_KEY_FILE.write_text(key)
    logger.warning(
        "No SECUSCAN_API_KEY set. Generated key saved to %s -- API KEY: %s",
        _API_KEY_FILE, key,
    )
    return key


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    active_key = _get_active_key()
    if credentials and secrets.compare_digest(credentials.credentials, active_key):
        return
    x_api_key = request.headers.get("X-Api-Key", "")
    if x_api_key and secrets.compare_digest(x_api_key, active_key):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )
