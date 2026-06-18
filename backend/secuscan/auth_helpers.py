"""
API key helpers — import-safe subset with no FastAPI dependencies.

Contains init_api_key extracted from auth.py so it can be unit-tested
without pulling in FastAPI and the rest of the web framework stack.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path


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
