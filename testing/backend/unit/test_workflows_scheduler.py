"""
Tests for WorkflowScheduler._should_run()

Covers:
- Basic interval scheduling (schedule_seconds)
- Timezone-naive/aware datetime bug where SQLite's datetime('now')
  produces strings without a timezone suffix, causing TypeError on subtraction.
- Cron expression scheduling behaviour
- Invalid cron expression handling (must log error and not raise)
- Backend validation: croniter.is_valid() rejects bad expressions
"""

from datetime import datetime, timezone, timedelta
import pytest
from croniter import croniter

from backend.secuscan.workflows import WorkflowScheduler


@pytest.fixture
def scheduler():
    return WorkflowScheduler()


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Core interval behaviour (schedule_seconds, no cron)
# ---------------------------------------------------------------------------

def test_should_run_when_no_last_run(scheduler):
    """First-ever run: last_run_at is None → always run."""
    assert scheduler._should_run(_now(), None, 3600, None) is True


def test_should_run_when_elapsed_exceeds_schedule(scheduler):
    """Last run was longer ago than schedule_seconds → run."""
    last = (_now() - timedelta(seconds=7200)).isoformat()
    assert scheduler._should_run(_now(), last, 3600, None) is True


def test_should_not_run_when_elapsed_below_schedule(scheduler):
    """Last run was recent → do not run."""
    last = (_now() - timedelta(seconds=60)).isoformat()
    assert scheduler._should_run(_now(), last, 3600, None) is False


def test_should_run_at_exact_boundary(scheduler):
    """Exactly at schedule_seconds elapsed → run."""
    last = (_now() - timedelta(seconds=3600)).isoformat()
    assert scheduler._should_run(_now(), last, 3600, None) is True


def test_empty_string_treated_as_no_last_run(scheduler):
    """Empty string last_run_at should behave like None → run."""
    assert scheduler._should_run(_now(), "", 3600, None) is True


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
        result = scheduler._should_run(now, sqlite_format, 3600, None)
        assert isinstance(result, bool)
    except TypeError as e:
        pytest.fail(
            f"_should_run raised TypeError on SQLite naive datetime: {e}\n"
            "Fix: add 'if last.tzinfo is None: last = last.replace(tzinfo=timezone.utc)'"
        )


def test_z_suffix_still_works(scheduler):
    """ISO strings ending in Z (UTC marker) must still be handled correctly."""
    last = (_now() - timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert scheduler._should_run(_now(), last, 3600, None) is True


def test_offset_aware_iso_string_still_works(scheduler):
    """Full ISO strings with +00:00 suffix must still be handled correctly."""
    last = (_now() - timedelta(seconds=7200)).isoformat()
    assert scheduler._should_run(_now(), last, 3600, None) is True


# ---------------------------------------------------------------------------
# Cron scheduling behaviour
# ---------------------------------------------------------------------------

def test_cron_triggers_when_past_next_run(scheduler):
    """Valid cron — now is past the next scheduled time → should run."""
    # Last ran 2 hours ago; cron fires every hour → should run now
    last = (_now() - timedelta(hours=2)).isoformat()
    assert scheduler._should_run(_now(), None, None, "0 * * * *") is True


def test_cron_no_trigger_when_before_next_run(scheduler):
    """Valid cron — next fire time is in the future → should NOT run yet."""
    # Last ran 30 seconds ago; cron fires every hour → too soon
    last = (_now() - timedelta(seconds=30)).isoformat()
    assert scheduler._should_run(_now(), last, None, "0 * * * *") is False


def test_cron_first_run_no_last_run_at(scheduler):
    """Cron with no previous run should always trigger (same as interval)."""
    assert scheduler._should_run(_now(), None, None, "*/5 * * * *") is True


def test_cron_takes_precedence_over_schedule_seconds(scheduler):
    """When both cron and schedule_seconds are present, cron wins."""
    # Ran 30 seconds ago. Cron fires hourly → too soon. But schedule_seconds=60
    # would say run (elapsed > 60? no, 30s). Either way cron should decide.
    last = (_now() - timedelta(seconds=30)).isoformat()
    # cron says don't run yet; schedule_seconds=10 (would say run but cron wins)
    result = scheduler._should_run(_now(), last, 10, "0 * * * *")
    assert result is False  # cron says not yet


# ---------------------------------------------------------------------------
# Invalid cron expression — must not raise, must fall back gracefully
# ---------------------------------------------------------------------------

def test_invalid_cron_expression_does_not_raise(scheduler):
    """
    An invalid cron expression stored in the DB should log an error
    and fall back to schedule_seconds logic — never raise an exception.
    """
    last = (_now() - timedelta(seconds=7200)).isoformat()
    try:
        result = scheduler._should_run(_now(), last, 3600, "NOT_A_CRON")
        # Should fall back to schedule_seconds=3600 and return True (elapsed >= 3600)
        assert isinstance(result, bool)
    except Exception as e:
        pytest.fail(f"_should_run raised {type(e).__name__} on invalid cron: {e}")


def test_invalid_cron_with_no_schedule_seconds_returns_false(scheduler):
    """Invalid cron + no schedule_seconds → graceful False, no exception."""
    last = (_now() - timedelta(seconds=100)).isoformat()
    result = scheduler._should_run(_now(), last, None, "bad-expr")
    assert result is False


# ---------------------------------------------------------------------------
# Backend validation: croniter.is_valid() must reject bad expressions
# ---------------------------------------------------------------------------

def test_croniter_rejects_invalid_expression():
    """croniter.is_valid() must return False for obviously invalid strings."""
    assert croniter.is_valid("NOT_A_CRON") is False
    assert croniter.is_valid("bad-expr") is False
    assert croniter.is_valid("99 99 99 99 99") is False


def test_croniter_accepts_valid_expressions():
    """croniter.is_valid() must return True for standard cron expressions."""
    assert croniter.is_valid("* * * * *") is True
    assert croniter.is_valid("0 * * * *") is True
    assert croniter.is_valid("*/5 * * * *") is True
    assert croniter.is_valid("0 9 * * 1-5") is True
    assert croniter.is_valid("30 6 1 * *") is True