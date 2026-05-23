"""Startup-generated API key authentication for SecuScan.

On first run a cryptographically random key is written to backend/data/.api_key
and printed to the console. Every subsequent request must supply it as:
    Authorization: Bearer <key>
or
    X-Api-Key: <key>
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_api_key: Optional[str] = None
_key_file: Optional[Path] = None


def init_api_key(data_dir: str) -> str:
    """Load or generate the API key and persist it to data_dir/.api_key."""
    global _api_key, _key_file
    _key_file = Path(data_dir) / ".api_key"
    _key_file.parent.mkdir(parents=True, exist_ok=True)

    if _key_file.exists():
        _api_key = _key_file.read_text().strip()
        if _api_key:
            logger.info("Loaded existing API key from %s", _key_file)
            return _api_key

    _api_key = secrets.token_hex(32)
    _key_file.write_text(_api_key)
    _key_file.chmod(0o600)

    logger.warning(
        "\n"
        "╔══════════════════════════════════════════════════════╗\n"
        "║          SecuScan API Key (first-run)                ║\n"
        "║                                                      ║\n"
        "║  %s  ║\n"
        "║                                                      ║\n"
        "║  Add this to your requests:                          ║\n"
        "║    Authorization: Bearer <key>                       ║\n"
        "║  Key saved at: backend/data/.api_key                 ║\n"
        "╚══════════════════════════════════════════════════════╝",
        _api_key,
    )
    return _api_key


def _get_api_key() -> str:
    if _api_key is None:
        raise RuntimeError("API key not initialised — call init_api_key() during startup")
    return _api_key


async def require_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> None:
    """FastAPI dependency that enforces API key authentication."""
    supplied: Optional[str] = None

    # Accept Bearer token
    if credentials and credentials.scheme.lower() == "bearer":
        supplied = credentials.credentials

    # Also accept X-Api-Key header (convenience for curl / scripts)
    if not supplied:
        supplied = request.headers.get("X-Api-Key")

    expected = _get_api_key()

    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Supply it as 'Authorization: Bearer <key>' or 'X-Api-Key: <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
