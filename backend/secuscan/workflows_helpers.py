"""
Pure workflow scheduling helpers extracted from workflows.py.

These helpers contain no database or FastAPI dependencies.
workflows.py re-imports them so existing call sites keep working.
"""
from __future__ import annotations

from datetime import datetime
from typing import Tuple

try:
    from zoneinfo import ZoneInfo
    _ZONEINFO_AVAILABLE = True
except ImportError:
    _ZONEINFO_AVAILABLE = False


def validate_schedule_timezone(tz: str) -> Tuple[bool, str]:
    """
    Validate a timezone string.

    Returns (True, tz_name) for valid IANA timezone strings.
    Returns (False, error_message) for invalid strings.
    """
    if not tz:
        return (False, "timezone cannot be empty")

    if not _ZONEINFO_AVAILABLE:
        return (False, "zoneinfo not available")

    try:
        ZoneInfo(tz)
        return (True, tz)
    except Exception:
        return (False, f"Unknown timezone '{tz}'")
