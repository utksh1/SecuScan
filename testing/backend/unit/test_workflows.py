"""
Unit tests for backend/secuscan/workflow_scheduling.py _should_run helper.

Covers the pure datetime-computing function:
  - _should_run: elapsed-time scheduling logic

The function was extracted from WorkflowScheduler in workflows.py into
workflow_scheduling.py to allow safe unit testing without pulling in the
heavy dependency chain (database, ratelimit, executor).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.secuscan.workflow_scheduling import _should_run


class TestShouldRun:
    """WorkflowScheduler._should_run datetime logic."""

    def test_none_last_run_at_returns_true(self):
        """Never-run workflows (last_run_at=None) should always run."""
        now = datetime(2026, 7, 6, tzinfo=timezone.utc)
        result = _should_run(now, None, 3600)
        assert result is True

    def test_never_run_empty_string_returns_true(self):
        """Empty string last_run_at is treated as never run."""
        now = datetime(2026, 7, 6, tzinfo=timezone.utc)
        result = _should_run(now, "", 3600)
        assert result is True

    def test_elapsed_exceeds_schedule_returns_true(self):
        """Run when elapsed time >= schedule interval."""
        now = datetime(2026, 7, 6, 2, 0, 0, tzinfo=timezone.utc)
        last = datetime(2026, 7, 6, 1, 0, 0, tzinfo=timezone.utc)
        result = _should_run(now, last.isoformat(), 3600)
        assert result is True

    def test_elapsed_equals_schedule_returns_true(self):
        """Run when elapsed time exactly equals schedule (boundary)."""
        now = datetime(2026, 7, 6, 2, 0, 0, tzinfo=timezone.utc)
        last = datetime(2026, 7, 6, 1, 0, 0, tzinfo=timezone.utc)
        result = _should_run(now, last.isoformat(), 3600)
        assert result is True

    def test_elapsed_less_than_schedule_returns_false(self):
        """Skip when not enough time has elapsed."""
        now = datetime(2026, 7, 6, 1, 30, 0, tzinfo=timezone.utc)
        last = datetime(2026, 7, 6, 1, 0, 0, tzinfo=timezone.utc)
        result = _should_run(now, last.isoformat(), 3600)
        assert result is False

    def test_naive_datetime_treated_as_utc(self):
        """SQLite datetime('now') returns naive datetime (no Z suffix).

        The method must treat naive timestamps as UTC (the comment in
        workflows.py explains this).
        """
        now = datetime(2026, 7, 6, 2, 0, 0, tzinfo=timezone.utc)
        # SQLite format: "2026-07-06 01:00:00" (no Z, no +00:00)
        naive_last = "2026-07-06 01:00:00"
        result = _should_run(now, naive_last, 3600)
        assert result is True

    def test_naive_datetime_still_in_future_returns_false(self):
        """Naive last_run_at that is still within the schedule window."""
        now = datetime(2026, 7, 6, 1, 30, 0, tzinfo=timezone.utc)
        naive_last = "2026-07-06 01:00:00"
        result = _should_run(now, naive_last, 3600)
        assert result is False

    def test_z_suffix_datetime_handled(self):
        """Datetime with Z suffix is parsed correctly."""
        now = datetime(2026, 7, 6, 2, 0, 0, tzinfo=timezone.utc)
        last = "2026-07-06T01:00:00Z"
        result = _should_run(now, last, 3600)
        assert result is True

    def test_positive_offset_timezone_handled(self):
        """Datetime with explicit +HH:MM timezone is parsed correctly."""
        now = datetime(2026, 7, 6, 6, 30, 0, tzinfo=timezone.utc)
        last = "2026-07-06T02:00:00+05:30"
        # 02:00+05:30 == 20:30Z, elapsed ~4h, 3600s threshold
        result = _should_run(now, last, 3600)
        assert result is True

    def test_negative_offset_timezone_handled(self):
        """Datetime with negative timezone offset is parsed correctly."""
        now = datetime(2026, 7, 6, 8, 0, 0, tzinfo=timezone.utc)
        last = "2026-07-06T02:00:00-05:00"
        # 02:00-05:00 == 07:00Z, elapsed from 07:00 to 08:00 = 1h = 3600s -> True (boundary)
        result = _should_run(now, last, 3600)
        assert result is True

    def test_short_schedule_interval(self):
        """Schedule interval of 60 seconds works correctly."""
        now = datetime(2026, 7, 6, 1, 1, 0, tzinfo=timezone.utc)
        last = datetime(2026, 7, 6, 1, 0, 0, tzinfo=timezone.utc)
        result = _should_run(now, last.isoformat(), 60)
        assert result is True

    def test_short_interval_not_yet_elapsed(self):
        """60-second interval not elapsed returns False."""
        now = datetime(2026, 7, 6, 1, 0, 30, tzinfo=timezone.utc)
        last = datetime(2026, 7, 6, 1, 0, 0, tzinfo=timezone.utc)
        result = _should_run(now, last.isoformat(), 60)
        assert result is False

    def test_does_not_mutate_now_parameter(self):
        """_should_run must not mutate the passed-in now datetime."""
        now = datetime(2026, 7, 6, tzinfo=timezone.utc)
        now_before = now.isoformat()
        _should_run(now, None, 3600)
        assert now.isoformat() == now_before

    def test_zero_schedule_seconds_is_true(self):
        """schedule_seconds=0: elapsed >= 0 is always True for any past timestamp."""
        now = datetime(2026, 7, 6, tzinfo=timezone.utc)
        last = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = _should_run(now, last.isoformat(), 0)
        assert result is True
