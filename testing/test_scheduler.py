"""
Unit tests for the scheduler module.

Tests cover:
- Cron expression parsing with timezone awareness
- Blackout window detection (including overnight windows)
- Missed-run recovery logic
- Input validation
"""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.secuscan.utils.scheduler import (
    get_next_run_time,
    is_in_blackout_window,
    should_recover_missed_run,
    validate_cron_expression,
    validate_time_format,
)


class TestGetNextRunTime:
    """Tests for get_next_run_time function."""

    def test_basic_daily_cron(self):
        """Test parsing a simple daily cron expression."""
        # "0 2 * * *" = every day at 2 AM
        next_run = get_next_run_time("0 2 * * *", "UTC")
        assert isinstance(next_run, datetime)
        assert next_run.hour == 2
        assert next_run.minute == 0

    def test_timezone_aware(self):
        """Test that the function respects timezone."""
        tz_ny = ZoneInfo("America/New_York")
        tz_tokyo = ZoneInfo("Asia/Tokyo")

        base_time = datetime(2026, 6, 3, 12, 0, 0, tzinfo=tz_ny)

        next_run_ny = get_next_run_time("0 14 * * *", "America/New_York", base_time)
        assert next_run_ny.tzinfo == tz_ny
        assert next_run_ny.hour == 14

    def test_invalid_cron_raises_error(self):
        """Test that invalid cron expressions raise ValueError."""
        with pytest.raises(ValueError):
            get_next_run_time("invalid cron", "UTC")

    def test_invalid_timezone_raises_error(self):
        """Test that invalid timezones raise ValueError."""
        with pytest.raises(ValueError):
            get_next_run_time("0 2 * * *", "Invalid/Timezone")

    def test_every_six_hours(self):
        """Test parsing cron for every 6 hours."""
        # "0 */6 * * *" = every 6 hours at minute 0
        base_time = datetime(2026, 6, 3, 10, 30, 0, tzinfo=ZoneInfo("UTC"))
        next_run = get_next_run_time("0 */6 * * *", "UTC", base_time)

        # Next run should be at 12:00 (next 6-hour boundary)
        assert next_run.hour in [0, 6, 12, 18]
        assert next_run.minute == 0


class TestIsInBlackoutWindow:
    """Tests for is_in_blackout_window function."""

    def test_time_in_simple_window(self):
        """Test detection of time within a simple blackout window."""
        current = datetime(2026, 6, 3, 15, 30, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "14:00", "18:00") is True

    def test_time_outside_simple_window(self):
        """Test detection of time outside a simple blackout window."""
        current = datetime(2026, 6, 3, 13, 0, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "14:00", "18:00") is False

    def test_time_in_overnight_window(self):
        """Test detection of time within an overnight blackout window."""
        # Blackout from 23:00 to 06:00

        # Test 01:00 (should be in blackout)
        current = datetime(2026, 6, 3, 1, 0, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "23:00", "06:00") is True

        # Test 23:30 (should be in blackout)
        current = datetime(2026, 6, 3, 23, 30, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "23:00", "06:00") is True

    def test_time_outside_overnight_window(self):
        """Test detection of time outside an overnight blackout window."""
        # Blackout from 23:00 to 06:00

        # Test 12:00 (should NOT be in blackout)
        current = datetime(2026, 6, 3, 12, 0, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "23:00", "06:00") is False

    def test_empty_blackout_returns_false(self):
        """Test that empty blackout times return False."""
        current = datetime(2026, 6, 3, 15, 30, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "", "") is False
        assert is_in_blackout_window(current, None, None) is False

    def test_boundary_conditions(self):
        """Test behavior at exact boundary times."""
        current = datetime(2026, 6, 3, 14, 0, tzinfo=ZoneInfo("UTC"))
        # At start boundary, should be in blackout
        assert is_in_blackout_window(current, "14:00", "18:00") is True

        # Just before end, should be in blackout
        current = datetime(2026, 6, 3, 17, 59, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "14:00", "18:00") is True

    def test_invalid_time_format(self):
        """Test that invalid time formats return False."""
        current = datetime(2026, 6, 3, 15, 30, tzinfo=ZoneInfo("UTC"))
        assert is_in_blackout_window(current, "invalid", "18:00") is False


class TestShouldRecoverMissedRun:
    """Tests for should_recover_missed_run function."""

    def test_expected_run_not_yet_arrived(self):
        """Test that recovery returns False if next run hasn't arrived yet."""
        # Last run at 10:00, cron is daily at 14:00
        # Next expected: 14:00 (today). Current time: 11:00. Should NOT recover.
        last_run = datetime(2026, 6, 3, 10, 0, tzinfo=ZoneInfo("UTC"))
        current_time = datetime(2026, 6, 3, 11, 0, tzinfo=ZoneInfo("UTC"))

        result = should_recover_missed_run(
            last_run,
            "0 14 * * *",  # Daily at 14:00
            "UTC",
            now=current_time
        )
        # Next run is at 14:00, current is 11:00, so should NOT recover
        assert result is False

    def test_missed_run_not_in_blackout(self):
        """Test that missed runs outside blackout windows are recovered."""
        # Last run at 10:00, cron is every 6 hours
        # Next expected: 16:00. Current time: 18:00 (past expected run, not in blackout)
        last_run = datetime(2026, 6, 3, 10, 0, tzinfo=ZoneInfo("UTC"))
        current_time = datetime(2026, 6, 3, 18, 0, tzinfo=ZoneInfo("UTC"))

        result = should_recover_missed_run(
            last_run,
            "0 */6 * * *",  # Every 6 hours
            "UTC",
            "23:00",
            "06:00",
            now=current_time
        )
        # Expected run (16:00) is past, current (18:00) is outside blackout → should recover
        assert result is True

    def test_missed_run_in_blackout_window(self):
        """Test that missed runs in blackout window are NOT recovered."""
        # Last run at 22:00, cron is every 2 hours
        # Next expected: 00:00 (midnight). Current time: 01:00 (in blackout 23:00-06:00)
        last_run = datetime(2026, 6, 3, 22, 0, tzinfo=ZoneInfo("UTC"))
        current_time = datetime(2026, 6, 4, 1, 0, tzinfo=ZoneInfo("UTC"))

        result = should_recover_missed_run(
            last_run,
            "0 */2 * * *",  # Every 2 hours
            "UTC",
            "23:00",
            "06:00",
            now=current_time
        )
        # Expected run is past, but we're in blackout → should NOT recover
        assert result is False

    def test_invalid_inputs_return_false(self):
        """Test that invalid inputs default to False for safety."""
        last_run = datetime(2026, 6, 3, 10, 0, tzinfo=ZoneInfo("UTC"))

        # Invalid cron should return False (no exception)
        result = should_recover_missed_run(
            last_run,
            "invalid cron",
            "UTC"
        )
        assert result is False


class TestValidateCronExpression:
    """Tests for validate_cron_expression function."""

    def test_valid_cron_expressions(self):
        """Test validation of valid cron expressions."""
        valid_crons = [
            "0 2 * * *",           # Daily at 2 AM
            "0 */6 * * *",         # Every 6 hours
            "30 14 * * MON",       # Mondays at 2:30 PM
            "*/15 * * * *",        # Every 15 minutes
            "0 0 1 * *",           # Monthly on the 1st
        ]

        for cron in valid_crons:
            assert validate_cron_expression(cron) is True, f"Cron '{cron}' should be valid"

    def test_invalid_cron_expressions(self):
        """Test validation of invalid cron expressions."""
        invalid_crons = [
            "0 2",                 # Too few parts
            "0 2 * * * *",         # Too many parts
            "invalid",             # Complete nonsense
            "",                    # Empty
            "0 25 * * *",          # Hour out of range (25)
        ]

        for cron in invalid_crons:
            assert validate_cron_expression(cron) is False, f"Cron '{cron}' should be invalid"


class TestValidateTimeFormat:
    """Tests for validate_time_format function."""

    def test_valid_time_formats(self):
        """Test validation of valid time formats."""
        valid_times = [
            "00:00",  # Midnight
            "23:59",  # Just before midnight
            "12:30",  # Afternoon
            "06:45",  # Morning
            "",       # Empty is valid (optional field)
        ]

        for time_str in valid_times:
            assert validate_time_format(time_str) is True, f"Time '{time_str}' should be valid"

    def test_invalid_time_formats(self):
        """Test validation of invalid time formats."""
        invalid_times = [
            "24:00",  # Hour out of range
            "12:60",  # Minute out of range
            "13",     # Missing minutes
            "25:30",  # Hour too high
            "12:30:00",  # Includes seconds
            "invalid",
        ]

        for time_str in invalid_times:
            assert validate_time_format(time_str) is False, f"Time '{time_str}' should be invalid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
