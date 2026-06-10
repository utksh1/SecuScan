"""
Tests for scan_phase field in task status and phase transitions.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.secuscan.executor import TaskExecutor, ScanPhase
from backend.secuscan.models import TaskStatus


def make_task_row(task_id: str, status: str, scan_phase: str = None):
    return {
        "id": task_id,
        "plugin_id": "nmap",
        "tool_name": "Nmap",
        "target": "127.0.0.1",
        "status": status,
        "scan_phase": scan_phase,
        "created_at": "2026-01-01T00:00:00",
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "error_message": None,
        "preset": None,
        "inputs_json": "{}",
    }


async def _call_with_mock_db(executor, task_id, mock_db):
    import backend.secuscan.executor as executor_module
    original = executor_module.get_db

    async def mock_get_db():
        return mock_db

    executor_module.get_db = mock_get_db
    try:
        return await executor.get_task_status(task_id)
    finally:
        executor_module.get_db = original


@pytest.mark.asyncio
async def test_queued_task_has_scan_phase():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.QUEUED.value, ScanPhase.QUEUED.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] == ScanPhase.QUEUED.value


@pytest.mark.asyncio
async def test_running_task_has_running_command_phase():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.RUNNING.value, ScanPhase.RUNNING_COMMAND.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] == ScanPhase.RUNNING_COMMAND.value


@pytest.mark.asyncio
async def test_parsing_phase():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.RUNNING.value, ScanPhase.PARSING.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] == ScanPhase.PARSING.value


@pytest.mark.asyncio
async def test_reporting_phase():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.RUNNING.value, ScanPhase.REPORTING.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] == ScanPhase.REPORTING.value


@pytest.mark.asyncio
async def test_finished_phase():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.COMPLETED.value, ScanPhase.FINISHED.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] == ScanPhase.FINISHED.value


@pytest.mark.asyncio
async def test_failed_task_scan_phase():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.FAILED.value, ScanPhase.FINISHED.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] == ScanPhase.FINISHED.value


@pytest.mark.asyncio
async def test_unknown_scan_phase_is_null():
    executor = TaskExecutor()
    mock_db = AsyncMock()
    row = make_task_row("aaa", TaskStatus.QUEUED.value)
    row["scan_phase"] = None
    mock_db.fetchone.return_value = row

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["scan_phase"] is None


@pytest.mark.asyncio
async def test_broadcast_phase_persists_to_db():
    executor = TaskExecutor()
    mock_db = AsyncMock()

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        await executor._broadcast_phase("task-1", ScanPhase.PARSING.value)

    # Verify the DB was updated
    mock_db.execute.assert_called_once_with(
        "UPDATE tasks SET scan_phase = ? WHERE id = ?",
        (ScanPhase.PARSING.value, "task-1")
    )


@pytest.mark.asyncio
async def test_broadcast_phase_sends_event():
    executor = TaskExecutor()
    mock_db = AsyncMock()

    # Subscribe to the task
    queue = executor.subscribe("task-1")

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        await executor._broadcast_phase("task-1", ScanPhase.RUNNING_COMMAND.value)

    event = await queue.get()
    assert event["type"] == "phase"
    assert event["data"] == ScanPhase.RUNNING_COMMAND.value


@pytest.mark.asyncio
async def test_phase_broadcast_ordering():
    """
    Verify that _broadcast_phase broadcasts the expected phase sequence
    when called in correct order.
    """
    executor = TaskExecutor()
    mock_db = AsyncMock()

    queue = executor.subscribe("task-1")

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        await executor._broadcast_phase("task-1", ScanPhase.RUNNING_COMMAND.value)
        await executor._broadcast_phase("task-1", ScanPhase.PARSING.value)
        await executor._broadcast_phase("task-1", ScanPhase.REPORTING.value)
        await executor._broadcast_phase("task-1", ScanPhase.FINISHED.value)

    phase_events = []
    while not queue.empty():
        event = await queue.get()
        if event["type"] == "phase":
            phase_events.append(event["data"])

    expected_order = [
        ScanPhase.RUNNING_COMMAND.value,
        ScanPhase.PARSING.value,
        ScanPhase.REPORTING.value,
        ScanPhase.FINISHED.value,
    ]
    assert phase_events == expected_order, f"Phases out of order: {phase_events}"


@pytest.mark.asyncio
async def test_scan_phase_included_in_status_response():
    """
    Verify that the get_task_status response includes the scan_phase field
    via the route integration (mocked DB).
    """
    executor = TaskExecutor()
    mock_db = AsyncMock()
    mock_db.fetchone.return_value = {
        "id": "task-sse-1",
        "plugin_id": "nmap",
        "tool_name": "Nmap",
        "target": "127.0.0.1",
        "status": TaskStatus.RUNNING.value,
        "scan_phase": ScanPhase.RUNNING_COMMAND.value,
        "created_at": "2026-01-01T00:00:00",
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "error_message": None,
        "preset": None,
        "inputs_json": "{}",
    }

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "task-sse-1", mock_db)

    assert result["scan_phase"] == ScanPhase.RUNNING_COMMAND.value
