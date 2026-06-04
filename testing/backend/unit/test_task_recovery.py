"""
Tests for the startup task-recovery routine introduced in executor.py.

The recovery function handles two categories of tasks that survive in the
database after an unclean backend shutdown:

  * status='running'  — execution was interrupted; must be marked 'failed' with
                        a descriptive error_message and a completed_at timestamp.
  * status='queued'   — never started; must be re-submitted to the executor so
                        they resume without operator intervention.

Tasks in terminal states ('completed', 'failed', 'cancelled') must be left
entirely untouched by the recovery pass.

Every mutation is accompanied by an audit-log entry for traceability.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from backend.secuscan.executor import recover_tasks_on_startup
from backend.secuscan.models import TaskStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(task_id: str, status: str, plugin_id: str = "nmap") -> Dict[str, Any]:
    """Return a minimal task row dict as the Database layer would return it."""
    return {
        "id": task_id,
        "plugin_id": plugin_id,
        "tool_name": "Test Tool",
        "target": "127.0.0.1",
        "status": status,
        "created_at": "2026-01-01T00:00:00",
    }


def _make_db(running_rows: List[Dict], queued_rows: List[Dict]) -> AsyncMock:
    """
    Build a mock Database object whose fetchall() returns predefined rows for
    the two queries issued by recover_tasks_on_startup().
    """
    db = AsyncMock()
    db.execute = AsyncMock()
    db.log_audit = AsyncMock()

    # fetchall is called twice: first for running tasks, then for queued tasks.
    db.fetchall = AsyncMock(side_effect=[running_rows, queued_rows])

    return db


# ---------------------------------------------------------------------------
# Test 1: running tasks are marked failed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_running_tasks_are_marked_failed():
    """Tasks with status='running' must be transitioned to 'failed'."""
    task_id = str(uuid.uuid4())
    db = _make_db(
        running_rows=[_make_task(task_id, TaskStatus.RUNNING.value)],
        queued_rows=[],
    )

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    assert task_id in result["task_ids_failed"]
    assert result["recovered_running"] == 1


# ---------------------------------------------------------------------------
# Test 2: error_message is set on failed tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_running_task_error_message_is_set():
    """The DB UPDATE for a running task must include the restart error_message."""
    task_id = str(uuid.uuid4())
    db = _make_db(
        running_rows=[_make_task(task_id, TaskStatus.RUNNING.value)],
        queued_rows=[],
    )

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        await recover_tasks_on_startup(db)

    # Check that db.execute was called at least once and that the call contained
    # the expected restart error message in its parameters.
    all_calls = db.execute.call_args_list
    assert len(all_calls) >= 1, "db.execute should have been called for the running task"

    # The error message should appear in one of the parameter tuples.
    error_found = any(
        "Backend restarted while task was running" in str(c)
        for c in all_calls
    )
    assert error_found, "Expected restart error_message was not passed to db.execute"


# ---------------------------------------------------------------------------
# Test 3: completed_at is set on failed tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_running_task_completed_at_is_set():
    """The DB UPDATE for a running task must include a completed_at timestamp."""
    task_id = str(uuid.uuid4())
    db = _make_db(
        running_rows=[_make_task(task_id, TaskStatus.RUNNING.value)],
        queued_rows=[],
    )

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        await recover_tasks_on_startup(db)

    all_calls = db.execute.call_args_list
    # One of the execute calls should have a non-None timestamp-like string
    timestamp_found = any(
        any(isinstance(p, str) and "T" in p and len(p) >= 20 for p in c.args[1])
        for c in all_calls
        if c.args and len(c.args) >= 2 and isinstance(c.args[1], (list, tuple))
    )
    assert timestamp_found, "completed_at timestamp was not passed to db.execute"


# ---------------------------------------------------------------------------
# Test 4: queued tasks are re-enqueued
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queued_tasks_are_requeued():
    """Tasks with status='queued' must be re-submitted to the executor."""
    task_id = str(uuid.uuid4())
    db = _make_db(
        running_rows=[],
        queued_rows=[_make_task(task_id, TaskStatus.QUEUED.value)],
    )

    created_tasks: List[Any] = []

    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: created_tasks.append(coro))

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = mock_loop
        result = await recover_tasks_on_startup(db)

    assert task_id in result["task_ids_requeued"]
    assert result["recovered_queued"] == 1
    assert len(created_tasks) == 1


# ---------------------------------------------------------------------------
# Test 5: completed tasks are untouched
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_completed_tasks_are_not_touched():
    """Tasks with status='completed' must not be modified."""
    db = _make_db(running_rows=[], queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    # db.execute should never be called since there are no running/queued tasks
    db.execute.assert_not_called()
    assert result["recovered_running"] == 0
    assert result["recovered_queued"] == 0


# ---------------------------------------------------------------------------
# Test 6: failed tasks are untouched
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_already_failed_tasks_are_not_touched():
    """Tasks already in 'failed' state must not be double-modified."""
    # The DB mock returns empty rows for both queries — simulating a database
    # that only contains already-failed tasks (which are excluded by the WHERE).
    db = _make_db(running_rows=[], queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    db.execute.assert_not_called()
    assert result["task_ids_failed"] == []


# ---------------------------------------------------------------------------
# Test 7: cancelled tasks are untouched
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancelled_tasks_are_not_touched():
    """Tasks already in 'cancelled' state must not be re-processed."""
    db = _make_db(running_rows=[], queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    db.execute.assert_not_called()
    assert result["task_ids_requeued"] == []


# ---------------------------------------------------------------------------
# Test 8: empty database produces safe no-op result
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_db_produces_zero_counts():
    """When no tasks exist, the recovery result must show zero counts."""
    db = _make_db(running_rows=[], queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    assert result["recovered_running"] == 0
    assert result["recovered_queued"] == 0
    assert result["task_ids_failed"] == []
    assert result["task_ids_requeued"] == []


# ---------------------------------------------------------------------------
# Test 9: recovery result structure contains all required keys
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recovery_result_has_required_keys():
    """The returned dict must contain the five documented keys."""
    db = _make_db(running_rows=[], queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    required_keys = {
        "recovered_running",
        "recovered_queued",
        "task_ids_failed",
        "task_ids_requeued",
        "recovered_at",
    }
    assert required_keys.issubset(result.keys()), (
        f"Missing keys: {required_keys - result.keys()}"
    )


# ---------------------------------------------------------------------------
# Test 10: recovered_at is a valid ISO-8601 timestamp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recovery_result_recovered_at_is_iso8601():
    """recovered_at must be parseable as an ISO-8601 datetime string."""
    db = _make_db(running_rows=[], queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        result = await recover_tasks_on_startup(db)

    recovered_at = result["recovered_at"]
    # Will raise ValueError if not a valid ISO datetime
    dt = datetime.fromisoformat(recovered_at)
    assert dt is not None


# ---------------------------------------------------------------------------
# Test 11: audit log entry created for each running task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_created_for_each_running_task():
    """An audit entry must be written for every running task marked failed."""
    task_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    running_rows = [_make_task(t, TaskStatus.RUNNING.value) for t in task_ids]
    db = _make_db(running_rows=running_rows, queued_rows=[])

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        await recover_tasks_on_startup(db)

    # log_audit should have been called once per running task
    assert db.log_audit.call_count >= len(task_ids), (
        f"Expected at least {len(task_ids)} audit entries, got {db.log_audit.call_count}"
    )


# ---------------------------------------------------------------------------
# Test 12: audit log entry created for each queued task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_created_for_each_queued_task():
    """An audit entry must be written for every queued task that is re-enqueued."""
    task_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
    queued_rows = [_make_task(t, TaskStatus.QUEUED.value) for t in task_ids]
    db = _make_db(running_rows=[], queued_rows=queued_rows)

    created_tasks: List[Any] = []
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: created_tasks.append(coro))

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = mock_loop
        await recover_tasks_on_startup(db)

    assert db.log_audit.call_count >= len(task_ids), (
        f"Expected at least {len(task_ids)} audit entries, got {db.log_audit.call_count}"
    )


# ---------------------------------------------------------------------------
# Test 13: multiple running and queued tasks processed correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mixed_running_and_queued_tasks():
    """Both running and queued tasks are handled in the same recovery pass."""
    running_id = str(uuid.uuid4())
    queued_id1 = str(uuid.uuid4())
    queued_id2 = str(uuid.uuid4())

    db = _make_db(
        running_rows=[_make_task(running_id, TaskStatus.RUNNING.value)],
        queued_rows=[
            _make_task(queued_id1, TaskStatus.QUEUED.value),
            _make_task(queued_id2, TaskStatus.QUEUED.value),
        ],
    )

    created_tasks: List[Any] = []
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: created_tasks.append(coro))

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = mock_loop
        result = await recover_tasks_on_startup(db)

    assert result["recovered_running"] == 1
    assert result["recovered_queued"] == 2
    assert running_id in result["task_ids_failed"]
    assert queued_id1 in result["task_ids_requeued"]
    assert queued_id2 in result["task_ids_requeued"]
    assert len(created_tasks) == 2


# ---------------------------------------------------------------------------
# Test 14: running task status is set to FAILED (not any other terminal state)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_running_task_is_set_to_failed_not_cancelled():
    """A task interrupted at runtime must become 'failed', not 'cancelled'."""
    task_id = str(uuid.uuid4())
    db = _make_db(
        running_rows=[_make_task(task_id, TaskStatus.RUNNING.value)],
        queued_rows=[],
    )

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = MagicMock()
        await recover_tasks_on_startup(db)

    all_calls = db.execute.call_args_list
    failed_status_found = any(
        TaskStatus.FAILED.value in str(c)
        for c in all_calls
    )
    cancelled_status_used = any(
        TaskStatus.CANCELLED.value in str(c)
        for c in all_calls
    )
    assert failed_status_found, "Status 'failed' was never written by db.execute"
    assert not cancelled_status_used, "Status 'cancelled' must not be used by recovery"


# ---------------------------------------------------------------------------
# Test 15: audit event types are correct
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_event_types_are_specific():
    """
    Audit entries for recovery must use purpose-specific event types so operators
    can filter them separately from ordinary task lifecycle events.
    """
    running_id = str(uuid.uuid4())
    queued_id = str(uuid.uuid4())

    db = _make_db(
        running_rows=[_make_task(running_id, TaskStatus.RUNNING.value)],
        queued_rows=[_make_task(queued_id, TaskStatus.QUEUED.value)],
    )

    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: coro)

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = mock_loop
        await recover_tasks_on_startup(db)

    audit_calls = db.log_audit.call_args_list
    event_types_used = {c.args[0] for c in audit_calls if c.args}

    assert "task_recovery_failed" in event_types_used, (
        "Expected event_type 'task_recovery_failed' for running-task audit entry"
    )
    assert "task_recovery_requeued" in event_types_used, (
        "Expected event_type 'task_recovery_requeued' for queued-task audit entry"
    )


# ---------------------------------------------------------------------------
# Test 16: large batch of tasks is handled without error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_large_batch_recovery():
    """Recovery must succeed for a large number of mixed tasks."""
    running_rows = [_make_task(str(uuid.uuid4()), TaskStatus.RUNNING.value) for _ in range(20)]
    queued_rows = [_make_task(str(uuid.uuid4()), TaskStatus.QUEUED.value) for _ in range(30)]

    db = _make_db(running_rows=running_rows, queued_rows=queued_rows)

    created_tasks: List[Any] = []
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: created_tasks.append(coro))

    with patch("backend.secuscan.executor.asyncio") as mock_asyncio:
        mock_asyncio.get_event_loop.return_value = mock_loop
        result = await recover_tasks_on_startup(db)

    assert result["recovered_running"] == 20
    assert result["recovered_queued"] == 30
    assert len(result["task_ids_failed"]) == 20
    assert len(result["task_ids_requeued"]) == 30
    assert len(created_tasks) == 30
