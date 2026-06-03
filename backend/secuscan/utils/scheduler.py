"""
Scheduling engine for recurring scans with timezone support, blackout windows,
and missed-run recovery.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from croniter import croniter


def get_next_run_time(cron_expr: str, tz_string: str, base_time: datetime = None) -> datetime:
    """
    Calculates the next run time respecting the operator's timezone.

    Args:
        cron_expr: Standard 5-part cron expression (minute, hour, day, month, day-of-week)
        tz_string: IANA timezone string (e.g., 'UTC', 'America/New_York', 'Asia/Kolkata')
        base_time: Optional starting point; defaults to current time in the specified timezone

    Returns:
        Next valid run time as a timezone-aware datetime object

    Raises:
        ValueError: If cron expression or timezone is invalid
    """
    try:
        tz = ZoneInfo(tz_string)
    except Exception as e:
        raise ValueError(f"Invalid timezone '{tz_string}': {e}")

    if not base_time:
        base_time = datetime.now(tz)
    else:
        # Ensure base_time is timezone-aware
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=tz)
        else:
            base_time = base_time.astimezone(tz)

    try:
        cron = croniter(cron_expr, base_time)
        return cron.get_next(datetime)
    except Exception as e:
        raise ValueError(f"Invalid cron expression '{cron_expr}': {e}")


def is_in_blackout_window(
    current_time: datetime,
    blackout_start: str,
    blackout_end: str
) -> bool:
    """
    Evaluates if current_time falls between blackout_start and blackout_end.

    Handles overnight windows (e.g., 23:00 to 02:00) correctly.

    Args:
        current_time: Timezone-aware datetime to check
        blackout_start: Time string in 'HH:MM' format (e.g., '22:00')
        blackout_end: Time string in 'HH:MM' format (e.g., '06:00')

    Returns:
        True if current_time is within the blackout window; False otherwise
    """
    if not blackout_start or not blackout_end:
        return False

    try:
        # Extract time from current_time in its timezone
        current_time_str = current_time.strftime("%H:%M")

        # Parse start and end times
        start_hour, start_min = map(int, blackout_start.split(':'))
        end_hour, end_min = map(int, blackout_end.split(':'))

        current_hour, current_min = map(int, current_time_str.split(':'))

        # Convert times to minutes for easier comparison
        current_minutes = current_hour * 60 + current_min
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Overnight window (e.g., 23:00 to 02:00)
        if start_minutes > end_minutes:
            return current_minutes >= start_minutes or current_minutes < end_minutes
        # Same-day window (e.g., 14:00 to 18:00)
        else:
            return start_minutes <= current_minutes < end_minutes

    except (ValueError, AttributeError):
        # Invalid format; treat as no blackout
        return False


def should_recover_missed_run(
    last_run_time: datetime,
    cron_expr: str,
    tz_string: str,
    blackout_start: str = None,
    blackout_end: str = None,
    now: datetime = None
) -> bool:
    """
    Determines if a missed scan should execute immediately upon system recovery.

    Recovery logic:
    - If the expected next run is in the past AND not currently in a blackout window,
      the scan should execute immediately to catch up.
    - If the expected next run hasn't arrived yet, wait.
    - If the expected next run is in a blackout window, skip until next cycle.

    Args:
        last_run_time: Timezone-aware datetime of the last successful scan
        cron_expr: Cron expression for the recurring scan
        tz_string: IANA timezone string
        blackout_start: Optional blackout window start time ('HH:MM')
        blackout_end: Optional blackout window end time ('HH:MM')
        now: Optional override of current time (for testing). Defaults to datetime.now(tz)

    Returns:
        True if the missed scan should be recovered; False otherwise
    """
    try:
        tz = ZoneInfo(tz_string)
        if now is None:
            now = datetime.now(tz)
        else:
            # Ensure now is in the specified timezone
            if now.tzinfo is None:
                now = now.replace(tzinfo=tz)
            else:
                now = now.astimezone(tz)

        # Calculate what the next expected run was after the last successful run
        expected_run = get_next_run_time(cron_expr, tz_string, last_run_time)

        # If the expected run is still in the future, don't recover yet
        if expected_run > now:
            return False

        # If the expected run is in the past, check if we're currently in a blackout window
        if is_in_blackout_window(now, blackout_start or "", blackout_end or ""):
            # We're in a blackout; don't execute
            return False

        # Expected run was missed and we're not in blackout; recover
        return True

    except Exception:
        # On any error, default to no recovery to avoid double-execution
        return False


def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validates that a cron expression has exactly 5 parts.

    Args:
        cron_expr: Cron expression string

    Returns:
        True if valid 5-part cron; False otherwise
    """
    try:
        parts = cron_expr.strip().split()
        # Standard cron has 5 parts; extended may have 6 (with seconds), but we enforce 5
        return len(parts) == 5 and croniter.is_valid(cron_expr)
    except Exception:
        return False


def validate_time_format(time_str: str) -> bool:
    """
    Validates that a time string is in 'HH:MM' format and represents a valid time.

    Args:
        time_str: Time string to validate

    Returns:
        True if valid 'HH:MM' format; False otherwise
    """
    if not time_str:
        return True  # Empty is valid (no blackout)

    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return False
        hour, minute = int(parts[0]), int(parts[1])
        return 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, AttributeError):
        return False
