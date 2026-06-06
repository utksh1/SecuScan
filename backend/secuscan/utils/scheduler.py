"""
Scheduling helpers for recurring scans with timezone support, blackout windows,
and missed-run recovery. Used by WorkflowScheduler in workflows.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from croniter import croniter

Clock = Callable[[], datetime]


def _resolve_tz(tz_string: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_string)
    except Exception as exc:
        raise ValueError(f"Invalid timezone '{tz_string}': {exc}") from exc


def parse_db_timestamp(value: str | None) -> datetime | None:
    """Parse SQLite / ISO timestamps from the database as UTC-aware datetimes."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(ZoneInfo("UTC"))


def get_next_run_time(
    cron_expr: str,
    tz_string: str,
    base_time: datetime | None = None,
    *,
    now: datetime | None = None,
) -> datetime:
    """
    Calculate the next cron run time in the operator's timezone.

    Args:
        cron_expr: Standard 5-part cron expression
        tz_string: IANA timezone string
        base_time: Starting point for croniter; defaults to ``now`` in ``tz_string``
        now: Injectable clock override when ``base_time`` is omitted (for tests)
    """
    tz = _resolve_tz(tz_string)

    if base_time is None:
        base_time = now if now is not None else datetime.now(tz)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=tz)
    else:
        base_time = base_time.astimezone(tz)

    try:
        cron = croniter(cron_expr, base_time)
        return cron.get_next(datetime)
    except Exception as exc:
        raise ValueError(f"Invalid cron expression '{cron_expr}': {exc}") from exc


def is_in_blackout_window(
    current_time: datetime,
    blackout_start: str,
    blackout_end: str,
) -> bool:
    """Return True when ``current_time`` falls inside the blackout window."""
    if not blackout_start or not blackout_end:
        return False

    try:
        current_time_str = current_time.strftime("%H:%M")
        start_hour, start_min = map(int, blackout_start.split(":"))
        end_hour, end_min = map(int, blackout_end.split(":"))
        current_hour, current_min = map(int, current_time_str.split(":"))

        current_minutes = current_hour * 60 + current_min
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        if start_minutes > end_minutes:
            return current_minutes >= start_minutes or current_minutes < end_minutes
        return start_minutes <= current_minutes < end_minutes
    except (ValueError, AttributeError):
        return False


def should_recover_missed_run(
    last_run_time: datetime,
    cron_expr: str,
    tz_string: str,
    blackout_start: str | None = None,
    blackout_end: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Return True when a missed cron run should execute immediately after recovery."""
    try:
        tz = _resolve_tz(tz_string)
        if now is None:
            now = datetime.now(tz)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=tz)
        else:
            now = now.astimezone(tz)

        expected_run = get_next_run_time(cron_expr, tz_string, last_run_time)
        if expected_run > now:
            return False
        if is_in_blackout_window(now, blackout_start or "", blackout_end or ""):
            return False
        return True
    except Exception:
        return False


def should_run_cron_workflow(
    now_utc: datetime,
    last_run_at: str | None,
    cron_expr: str,
    tz_string: str,
    blackout_start: str | None = None,
    blackout_end: str | None = None,
) -> bool:
    """
    Decide whether a cron-scheduled workflow should run on this scheduler tick.

    ``now_utc`` must be timezone-aware UTC (injectable for deterministic tests).
    """
    if not cron_expr:
        return False

    tz = _resolve_tz(tz_string)
    now_local = now_utc.astimezone(tz)

    if is_in_blackout_window(now_local, blackout_start or "", blackout_end or ""):
        return False

    last_run = parse_db_timestamp(last_run_at)
    if last_run is None:
        day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        first_slot = get_next_run_time(cron_expr, tz_string, day_start - timedelta(seconds=1))
        return first_slot <= now_local

    last_local = last_run.astimezone(tz)
    return should_recover_missed_run(
        last_local,
        cron_expr,
        tz_string,
        blackout_start,
        blackout_end,
        now=now_local,
    )


def validate_cron_expression(cron_expr: str) -> bool:
    """Validate a 5-part cron expression."""
    try:
        parts = cron_expr.strip().split()
        return len(parts) == 5 and croniter.is_valid(cron_expr)
    except Exception:
        return False


def validate_time_format(time_str: str) -> bool:
    """Validate HH:MM time strings used for blackout windows."""
    if not time_str:
        return True

    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return False
        hour, minute = int(parts[0]), int(parts[1])
        return 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, AttributeError):
        return False


def validate_workflow_schedule(
    schedule_seconds: int | None,
    cron_expression: str | None,
    timezone: str | None,
    blackout_start: str | None,
    blackout_end: str | None,
) -> None:
    """Raise ValueError when workflow schedule fields are inconsistent or invalid."""
    has_interval = schedule_seconds is not None and schedule_seconds > 0
    has_cron = bool(cron_expression and cron_expression.strip())

    if has_interval and has_cron:
        raise ValueError("Provide either schedule_seconds or cron_expression, not both")

    if has_cron:
        if not validate_cron_expression(cron_expression):
            raise ValueError("Invalid cron expression")
        try:
            _resolve_tz(timezone or "UTC")
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if blackout_start and not validate_time_format(blackout_start):
            raise ValueError("Invalid blackout start time")
        if blackout_end and not validate_time_format(blackout_end):
            raise ValueError("Invalid blackout end time")
        if bool(blackout_start) != bool(blackout_end):
            raise ValueError("Both blackout start and end are required, or neither")
