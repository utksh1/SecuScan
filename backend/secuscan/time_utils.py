"""Timezone helpers: canonical UTC-aware timestamps for API + reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional






def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_to_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)

    text = str(value).strip()
    if not text or text.lower() == "now":
        return utc_now() if text.lower() == "now" else None

    # SQLite stores "YYYY-MM-DD HH:MM:SS" (UTC, no offset)
    candidate = text.replace(" ", "T") if "T" not in text else text
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return ensure_utc(parsed)


def to_utc_iso(value: Any = None, *, timespec: str = "auto") -> str:
    parsed = utc_now() if value is None else parse_to_utc(value)
    if parsed is None:
        parsed = utc_now()
    return parsed.isoformat(timespec=timespec)


def format_utc_display(value: Any, *, fmt: str = "%b %d, %Y %H:%M UTC") -> str:
    parsed = parse_to_utc(value)
    if parsed is None:
        return "Unknown"
    return parsed.strftime(fmt)
