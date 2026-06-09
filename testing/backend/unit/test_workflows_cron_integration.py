"""Integration-style tests for cron workflow scheduling inside WorkflowScheduler."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.secuscan.workflows import WorkflowScheduler


UTC = timezone.utc


@pytest.mark.asyncio
async def test_tick_runs_cron_workflow_when_due():
    fixed_now = datetime(2026, 6, 3, 3, 0, tzinfo=UTC)
    scheduler = WorkflowScheduler(clock=lambda: fixed_now)

    row = {
        "id": "wf-1",
        "name": "Nightly",
        "schedule_seconds": None,
        "cron_expression": "0 2 * * *",
        "timezone": "UTC",
        "blackout_start": None,
        "blackout_end": None,
        "last_run_at": None,
        "steps_json": '[{"plugin_id": "http_inspector", "inputs": {"url": "http://127.0.0.1"}}]',
    }

    mock_db = AsyncMock()
    mock_db.fetchall.return_value = [row]

    with (
        patch("backend.secuscan.workflows.get_db", new=AsyncMock(return_value=mock_db)),
        patch("backend.secuscan.workflows.executor.create_task", new=AsyncMock(return_value="task-1")),
        patch("backend.secuscan.workflows.concurrent_limiter.acquire", new=AsyncMock(return_value=(True, None))),
        patch("backend.secuscan.workflows.asyncio.create_task") as create_task_mock,
    ):
        await scheduler.tick()

    mock_db.execute.assert_awaited()
    create_task_mock.assert_called()


@pytest.mark.asyncio
async def test_tick_skips_cron_workflow_in_blackout():
    fixed_now = datetime(2026, 6, 3, 15, 0, tzinfo=UTC)
    scheduler = WorkflowScheduler(clock=lambda: fixed_now)

    row = {
        "id": "wf-2",
        "name": "Blocked",
        "schedule_seconds": None,
        "cron_expression": "0 */6 * * *",
        "timezone": "UTC",
        "blackout_start": "14:00",
        "blackout_end": "18:00",
        "last_run_at": "2026-06-03 10:00:00",
        "steps_json": "[]",
    }

    mock_db = AsyncMock()
    mock_db.fetchall.return_value = [row]

    with patch("backend.secuscan.workflows.get_db", new=AsyncMock(return_value=mock_db)):
        await scheduler.tick()

    mock_db.execute.assert_not_awaited()
