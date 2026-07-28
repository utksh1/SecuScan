"""Pure helper functions extracted from backend/secuscan/executor.py.

This module is import-safe: it has no FastAPI/database/scanner dependencies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def _parse_discovered_at(finding: dict) -> Optional[datetime]:
    """Extract and parse discovered_at from a finding dict as timezone-aware UTC."""
    from .time_utils import parse_to_utc, utc_now

    parsed = parse_to_utc(finding.get("discovered_at"))
    return parsed if parsed is not None else utc_now()


def _validate_risk_fields(finding: dict) -> None:
    """Validate exploitability, confidence, and asset_exposure bounds in-place."""
    exp = finding.get("exploitability")
    if exp is not None:
        if not isinstance(exp, (int, float)):
            raise ValueError(f"exploitability must be numeric, got {type(exp).__name__}")
        if exp < 0 or exp > 10:
            raise ValueError(f"exploitability must be in [0, 10], got {exp}")

    conf = finding.get("confidence")
    if conf is not None:
        if not isinstance(conf, (int, float)):
            raise ValueError(f"confidence must be numeric, got {type(conf).__name__}")
        if conf < 0 or conf > 1:
            raise ValueError(f"confidence must be in [0, 1], got {conf}")

    ae = finding.get("asset_exposure")
    if ae is not None and ae.lower() not in ("critical", "high", "medium", "low"):
        raise ValueError(f"asset_exposure must be one of critical/high/medium/low, got {ae}")


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    """Read a dict/sqlite row key with a default for backward-compatible mocks."""
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default
