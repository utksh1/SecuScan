"""
Tests for queue_position and pending_count in get_task_status().
Covers: queued tasks get position, non-queued tasks get None.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.secuscan.executor import TaskExecutor
from backend.secuscan.models import TaskStatus


def make_task_row(task_id: str, status: str, created_at: str = "2026-01-01T00:00:00"):
    return {
        "id": task_id,
        "plugin_id": "nmap",
        "tool_name": "Nmap",
        "target": "127.0.0.1",
        "status": status,
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "exit_code": None,
        "error_message": None,
        "preset": None,
        "inputs_json": "{}",
    }


@pytest.mark.asyncio
async def test_queued_task_gets_correct_position():
    executor = TaskExecutor()
    task_ids = ["aaa", "bbb", "ccc"]

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("bbb", TaskStatus.QUEUED.value)
    mock_db.fetchall.return_value = [
        {"id": "aaa"},
        {"id": "bbb"},
        {"id": "ccc"},
    ]

    with patch(
        "backend.secuscan.executor.get_db", return_value=AsyncMock(return_value=mock_db)
    ):
        with patch(
            "backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)
        ):
            result = (
                await executor.get_task_status.__wrapped__(executor, "bbb")
                if hasattr(executor.get_task_status, "__wrapped__")
                else await _call_with_mock_db(executor, "bbb", mock_db)
            )

    assert result["queue_position"] == 2
    assert result["pending_count"] == 3


@pytest.mark.asyncio
async def test_completed_task_has_no_queue_metadata():
    executor = TaskExecutor()

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.COMPLETED.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["queue_position"] is None
    assert result["pending_count"] is None


@pytest.mark.asyncio
async def test_running_task_has_no_queue_metadata():
    executor = TaskExecutor()

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.RUNNING.value)

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["queue_position"] is None
    assert result["pending_count"] is None


@pytest.mark.asyncio
async def test_first_queued_task_is_position_one():
    executor = TaskExecutor()

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = make_task_row("aaa", TaskStatus.QUEUED.value)
    mock_db.fetchall.return_value = [{"id": "aaa"}]

    with patch("backend.secuscan.executor.get_db", new=AsyncMock(return_value=mock_db)):
        result = await _call_with_mock_db(executor, "aaa", mock_db)

    assert result["queue_position"] == 1
    assert result["pending_count"] == 1


async def _call_with_mock_db(executor, task_id, mock_db):
    """Helper to call get_task_status with a mocked db."""
    import backend.secuscan.executor as executor_module

    original = executor_module.get_db

    async def mock_get_db():
        return mock_db

    executor_module.get_db = mock_get_db
    try:
        return await executor.get_task_status(task_id)
    finally:
        executor_module.get_db = original
