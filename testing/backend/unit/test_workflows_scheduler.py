"""
Tests for WorkflowScheduler._should_run()

Covers the timezone-naive/aware datetime bug where SQLite's datetime('now')
produces strings without a timezone suffix, causing TypeError on subtraction.
"""

from datetime import datetime, timezone, timedelta
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

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


# ---------------------------------------------------------------------------
# _run_workflow error-path tests
# ---------------------------------------------------------------------------

def _make_mock_db():
    mock_db = MagicMock()
    mock_db.fetchone = AsyncMock(return_value=None)
    mock_db.fetchall = AsyncMock(return_value=[])
    mock_db.snapshot_workflow_version = AsyncMock(return_value={"id": "v-1", "version_number": 1})
    mock_db.record_workflow_run = AsyncMock(return_value="run-1")
    return mock_db


def _make_mock_plugin(category="scan", safety=None):
    p = MagicMock()
    p.category = category
    p.safety = safety or {}
    return p


async def _run_workflow_with_mocks(scheduler, steps, mock_db, plugin, validate_result=(True, "")):
    """Run _run_workflow with patched dependencies, return mock_executor for assertions."""
    mock_pm = MagicMock()
    mock_pm.get_plugin.return_value = plugin

    mock_executor = MagicMock()
    mock_executor.create_task = AsyncMock(return_value="tid-test")
    mock_executor.mark_task_failed = AsyncMock()

    mock_concurrent_limiter = MagicMock()
    mock_concurrent_limiter.acquire = AsyncMock(return_value=(True, ""))

    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (True, "", None)

    with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock, return_value=mock_db):
        with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm):
            with patch("backend.secuscan.validation.validate_target", return_value=validate_result):
                with patch("backend.secuscan.network_policy.get_policy_engine", return_value=mock_engine):
                    with patch("backend.secuscan.workflows.executor", mock_executor):
                        with patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent_limiter):
                            with patch("backend.secuscan.workflows.get_target_policy", new_callable=AsyncMock, return_value=None):
                                with patch("backend.secuscan.workflows.normalize_execution_context", return_value={}):
                                    with patch("backend.secuscan.workflows.get_request_id", return_value="req-1"):
                                        await scheduler._run_workflow("wf-1", steps)

    return mock_executor


class TestRunWorkflowErrorPaths:
    def test_skips_missing_plugin(self):
        """When plugin not found, _run_workflow skips the step and does not create a task."""
        scheduler = WorkflowScheduler()
        mock_db = _make_mock_db()
        mock_executor = asyncio.run(
            _run_workflow_with_mocks(scheduler, [{"plugin_id": "nonexistent", "inputs": {}}], mock_db, plugin=None)
        )
        mock_executor.create_task.assert_not_called()

    def test_skips_invalid_target(self):
        """When target validation fails, _run_workflow skips the step and does not create a task."""
        scheduler = WorkflowScheduler()
        mock_db = _make_mock_db()
        mock_executor = asyncio.run(
            _run_workflow_with_mocks(
                scheduler,
                [{"plugin_id": "nmap", "inputs": {"target": "bad-target"}}],
                mock_db,
                plugin=_make_mock_plugin(category="scan"),
                validate_result=(False, "Invalid target"),
            )
        )
        mock_executor.create_task.assert_not_called()

    def test_skips_target_validation_timeout(self):
        """When target validation times out, _run_workflow skips the step without creating a task."""
        scheduler = WorkflowScheduler()
        mock_db = _make_mock_db()

        mock_pm = MagicMock()
        mock_pm.get_plugin.return_value = _make_mock_plugin(category="scan")

        mock_executor = MagicMock()
        mock_executor.create_task = AsyncMock(return_value="tid-test")

        mock_concurrent_limiter = MagicMock()
        mock_concurrent_limiter.acquire = AsyncMock(return_value=(True, ""))

        mock_engine = MagicMock()
        mock_engine.check_access.return_value = (True, "", None)

        def sync_timeout_validate(*args, **kwargs):
            raise TimeoutError()

        async def run_test():
            with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock, return_value=mock_db):
                with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm):
                    with patch("backend.secuscan.validation.validate_target", side_effect=sync_timeout_validate):
                        with patch("backend.secuscan.network_policy.get_policy_engine", return_value=mock_engine):
                            with patch("backend.secuscan.workflows.executor", mock_executor):
                                with patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent_limiter):
                                    with patch("backend.secuscan.workflows.get_target_policy", new_callable=AsyncMock, return_value=None):
                                        with patch("backend.secuscan.workflows.normalize_execution_context", return_value={}):
                                            with patch("backend.secuscan.workflows.get_request_id", return_value="req-1"):
                                                await scheduler._run_workflow("wf-1", [{"plugin_id": "nmap", "inputs": {"target": "bad"}}])

        asyncio.run(run_test())
        mock_executor.create_task.assert_not_called()

    def test_creates_task_when_valid(self):
        """When plugin found and target valid, _run_workflow creates a task."""
        scheduler = WorkflowScheduler()
        mock_db = _make_mock_db()
        mock_executor = asyncio.run(
            _run_workflow_with_mocks(
                scheduler,
                [{"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}}],
                mock_db,
                plugin=_make_mock_plugin(category="scan"),
                validate_result=(True, ""),
            )
        )
        mock_executor.create_task.assert_called_once()


from backend.secuscan.workflows import validate_schedule_timezone

class TestScheduleTimezoneValidation:
    def test_valid_iana_timezones(self):
        valid_tzs = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo", "   UTC   "]
        for tz in valid_tzs:
            ok, err = validate_schedule_timezone(tz)
            assert ok is True, f"Expected {tz} to be valid, got error: {err}"
            assert err == ""

    def test_invalid_timezone_abbreviations(self):
        invalid_tzs = ["EDT", "PDT", "BST"]
        for tz in invalid_tzs:
            ok, err = validate_schedule_timezone(tz)
            assert ok is False, f"Expected {tz} to be invalid"
            assert "Invalid timezone" in err

    def test_invalid_timezone_offsets(self):
        invalid_tzs = ["GMT+5", "UTC-8", "+05:30"]
        for tz in invalid_tzs:
            ok, err = validate_schedule_timezone(tz)
            assert ok is False, f"Expected {tz} to be invalid"
            assert "Invalid timezone" in err

    def test_invalid_types_and_empty_values(self):
        invalid_vals = ["", "   ", None, 123, []]
        for val in invalid_vals:
            ok, err = validate_schedule_timezone(val)
            assert ok is False
            assert "must be a non-empty string" in err

    def test_nonsense_strings(self):
        ok, err = validate_schedule_timezone("America/Invalid_Place")
        assert ok is False
        assert "Invalid timezone" in err
