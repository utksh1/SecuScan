"""
Tests for WorkflowScheduler._should_run()

Covers the timezone-naive/aware datetime bug where SQLite's datetime('now')
produces strings without a timezone suffix, causing TypeError on subtraction.
"""

from datetime import datetime, timezone, timedelta
import pytest

from backend.secuscan.workflows import WorkflowScheduler


@pytest.fixture
def scheduler():
    return WorkflowScheduler()


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------

def test_should_run_when_no_last_run(scheduler):
    """First-ever run: last_run_at is None → always run."""
    assert scheduler._should_run(_now(), None, 3600) is True


def test_should_run_when_elapsed_exceeds_schedule(scheduler):
    """Last run was longer ago than schedule_seconds → run."""
    last = (_now() - timedelta(seconds=7200)).isoformat()
    assert scheduler._should_run(_now(), last, 3600) is True


def test_should_not_run_when_elapsed_below_schedule(scheduler):
    """Last run was recent → do not run."""
    last = (_now() - timedelta(seconds=60)).isoformat()
    assert scheduler._should_run(_now(), last, 3600) is False


def test_should_run_at_exact_boundary(scheduler):
    """Exactly at schedule_seconds elapsed → run."""
    last = (_now() - timedelta(seconds=3600)).isoformat()
    assert scheduler._should_run(_now(), last, 3600) is True


# ---------------------------------------------------------------------------
# Regression: SQLite naive datetime string must not raise TypeError
# ---------------------------------------------------------------------------

def test_sqlite_naive_datetime_does_not_raise(scheduler):
    """
    Regression: SQLite datetime('now') produces '2026-05-25 08:02:28' —
    no Z, no +00:00 suffix. fromisoformat() returns a naive datetime.
    Subtracting naive from aware raises TypeError.
    This test fails on the unfixed code and passes after the fix.
    """
    sqlite_format = "2026-05-25 08:02:28"   # exact format SQLite produces
    now = datetime.now(timezone.utc)

    # Must not raise TypeError
    try:
        result = scheduler._should_run(now, sqlite_format, 3600)
        assert isinstance(result, bool)
    except TypeError as e:
        pytest.fail(
            f"_should_run raised TypeError on SQLite naive datetime: {e}\n"
            "Fix: add 'if last.tzinfo is None: last = last.replace(tzinfo=timezone.utc)'"
        )


def test_z_suffix_still_works(scheduler):
    """ISO strings ending in Z (UTC marker) must still be handled correctly."""
    last = (_now() - timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert scheduler._should_run(_now(), last, 3600) is True


def test_offset_aware_iso_string_still_works(scheduler):
    """Full ISO strings with +00:00 suffix must still be handled correctly."""
    last = (_now() - timedelta(seconds=7200)).isoformat()
    assert scheduler._should_run(_now(), last, 3600) is True


def test_empty_string_treated_as_no_last_run(scheduler):
    """Empty string last_run_at should behave like None → run."""
    assert scheduler._should_run(_now(), "", 3600) is True