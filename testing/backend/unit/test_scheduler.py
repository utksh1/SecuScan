"""
Unit tests for scheduler helpers used by WorkflowScheduler.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.secuscan.utils.scheduler import (
    get_next_run_time,
    is_in_blackout_window,
    should_recover_missed_run,
    should_run_cron_workflow,
    validate_cron_expression,
    validate_time_format,
    validate_workflow_schedule,
)


UTC = ZoneInfo("UTC")


class TestGetNextRunTime:
    def test_basic_daily_cron(self):
        base_time = datetime(2026, 6, 3, 1, 0, 0, tzinfo=UTC)
        next_run = get_next_run_time("0 2 * * *", "UTC", base_time)
        assert next_run.hour == 2
        assert next_run.minute == 0

    def test_timezone_aware(self):
        tz_ny = ZoneInfo("America/New_York")
        base_time = datetime(2026, 6, 3, 12, 0, 0, tzinfo=tz_ny)
        next_run_ny = get_next_run_time("0 14 * * *", "America/New_York", base_time)
        assert next_run_ny.tzinfo == tz_ny
        assert next_run_ny.hour == 14

    def test_invalid_cron_raises_error(self):
        with pytest.raises(ValueError):
            get_next_run_time("invalid cron", "UTC", datetime(2026, 6, 3, tzinfo=UTC))

    def test_invalid_timezone_raises_error(self):
        with pytest.raises(ValueError):
            get_next_run_time("0 2 * * *", "Invalid/Timezone", datetime(2026, 6, 3, tzinfo=UTC))

    def test_every_six_hours(self):
        base_time = datetime(2026, 6, 3, 10, 30, 0, tzinfo=UTC)
        next_run = get_next_run_time("0 */6 * * *", "UTC", base_time)
        assert next_run.hour in [0, 6, 12, 18]
        assert next_run.minute == 0


class TestIsInBlackoutWindow:
    def test_time_in_simple_window(self):
        current = datetime(2026, 6, 3, 15, 30, tzinfo=UTC)
        assert is_in_blackout_window(current, "14:00", "18:00") is True

    def test_time_outside_simple_window(self):
        current = datetime(2026, 6, 3, 13, 0, tzinfo=UTC)
        assert is_in_blackout_window(current, "14:00", "18:00") is False

    def test_time_in_overnight_window(self):
        current = datetime(2026, 6, 3, 1, 0, tzinfo=UTC)
        assert is_in_blackout_window(current, "23:00", "06:00") is True
        current = datetime(2026, 6, 3, 23, 30, tzinfo=UTC)
        assert is_in_blackout_window(current, "23:00", "06:00") is True

    def test_time_outside_overnight_window(self):
        current = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)
        assert is_in_blackout_window(current, "23:00", "06:00") is False

    def test_empty_blackout_returns_false(self):
        current = datetime(2026, 6, 3, 15, 30, tzinfo=UTC)
        assert is_in_blackout_window(current, "", "") is False


class TestShouldRecoverMissedRun:
    def test_expected_run_not_yet_arrived(self):
        last_run = datetime(2026, 6, 3, 10, 0, tzinfo=UTC)
        current_time = datetime(2026, 6, 3, 11, 0, tzinfo=UTC)
        assert (
            should_recover_missed_run(last_run, "0 14 * * *", "UTC", now=current_time)
            is False
        )

    def test_missed_run_not_in_blackout(self):
        last_run = datetime(2026, 6, 3, 10, 0, tzinfo=UTC)
        current_time = datetime(2026, 6, 3, 18, 0, tzinfo=UTC)
        assert (
            should_recover_missed_run(
                last_run,
                "0 */6 * * *",
                "UTC",
                "23:00",
                "06:00",
                now=current_time,
            )
            is True
        )

    def test_missed_run_in_blackout_window(self):
        last_run = datetime(2026, 6, 3, 22, 0, tzinfo=UTC)
        current_time = datetime(2026, 6, 4, 1, 0, tzinfo=UTC)
        assert (
            should_recover_missed_run(
                last_run,
                "0 */2 * * *",
                "UTC",
                "23:00",
                "06:00",
                now=current_time,
            )
            is False
        )


class TestShouldRunCronWorkflow:
    def test_first_run_due(self):
        now = datetime(2026, 6, 3, 3, 0, tzinfo=UTC)
        assert should_run_cron_workflow(now, None, "0 2 * * *", "UTC") is True

    def test_first_run_not_due(self):
        now = datetime(2026, 6, 3, 1, 0, tzinfo=UTC)
        assert should_run_cron_workflow(now, None, "0 2 * * *", "UTC") is False

    def test_skips_during_blackout(self):
        now = datetime(2026, 6, 3, 15, 0, tzinfo=UTC)
        assert (
            should_run_cron_workflow(
                now,
                "2026-06-03 10:00:00",
                "0 */6 * * *",
                "UTC",
                "14:00",
                "18:00",
            )
            is False
        )


class TestValidateWorkflowSchedule:
    def test_rejects_both_schedule_modes(self):
        with pytest.raises(ValueError, match="not both"):
            validate_workflow_schedule(3600, "0 2 * * *", "UTC", None, None)

    def test_accepts_cron_only(self):
        validate_workflow_schedule(None, "0 2 * * *", "UTC", "22:00", "06:00")


class TestValidateCronExpression:
    def test_valid_cron_expressions(self):
        for cron in ["0 2 * * *", "0 */6 * * *", "30 14 * * MON"]:
            assert validate_cron_expression(cron) is True

    def test_invalid_cron_expressions(self):
        for cron in ["0 2", "0 2 * * * *", "invalid", "", "0 25 * * *"]:
            assert validate_cron_expression(cron) is False


class TestValidateTimeFormat:
    def test_valid_time_formats(self):
        for time_str in ["00:00", "23:59", "12:30", ""]:
            assert validate_time_format(time_str) is True

    def test_invalid_time_formats(self):
        for time_str in ["24:00", "12:60", "13", "25:30", "12:30:00", "invalid"]:
            assert validate_time_format(time_str) is False
