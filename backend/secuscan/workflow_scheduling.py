"""
Workflow scheduling datetime helpers.

Extracted from workflows.py for safe unit testing (the parent module imports
database/ratelimit/executor which require heavy runtime dependencies).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _should_run(now: datetime, last_run_at: str | None, schedule_seconds: int) -> bool:
    """Return True if the schedule interval has elapsed since last_run_at.

    Args:
        now: current timestamp (UTC, timezone-aware)
        last_run_at: ISO-format timestamp of last execution, or None/"" if never run
        schedule_seconds: minimum seconds between executions

    Returns:
        True when the workflow should fire now.
    """
    if not last_run_at:
        return True
    last = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
    # SQLite's datetime('now') produces "2026-05-25 08:02:28" - no Z and
    # no +00:00 suffix - so fromisoformat() returns a naive datetime.
    # Subtracting a naive datetime from an aware one raises TypeError.
    # Treat any naive timestamp from the DB as UTC.
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = (now - last).total_seconds()
    return elapsed >= schedule_seconds
