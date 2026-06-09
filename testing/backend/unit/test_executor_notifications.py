"""Executor integration with notification dispatch (PR 4 of #254)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.secuscan.config import settings
from backend.secuscan.database import get_db, init_db
from backend.secuscan.executor import TaskExecutor
from backend.secuscan.models import TaskStatus


@pytest.mark.asyncio
async def test_execute_task_dispatches_notifications_after_findings(setup_test_environment):
    """Successful task completion should trigger process_task_notifications."""
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            "nmap",
            "nmap",
            "127.0.0.1",
            '{"target":"127.0.0.1"}',
            TaskStatus.QUEUED.value,
            1,
            1,
        ),
    )

    executor = TaskExecutor()

    async def fake_command(*args, **kwargs):
        return "80/tcp open http", 0, None

    mock_dispatch = AsyncMock(return_value=[])

    with (
        patch.object(executor, "_execute_command", side_effect=fake_command),
        patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter,
        patch("backend.secuscan.executor.get_plugin_manager") as mock_pm,
        patch(
            "backend.secuscan.executor.process_task_notifications",
            mock_dispatch,
        ),
    ):

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "nmap"
        mock_plugin.capabilities = []
        mock_plugin.safety = {"level": "safe"}
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "127.0.0.1"]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task(task_id)

    mock_dispatch.assert_awaited_once()
    assert mock_dispatch.await_args.args[1] == task_id

    row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
    await db.disconnect()


@pytest.mark.asyncio
async def test_execute_task_survives_notification_dispatch_failure(setup_test_environment):
    """Notification errors must not prevent task completion."""
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            "nmap",
            "nmap",
            "127.0.0.1",
            '{"target":"127.0.0.1"}',
            TaskStatus.QUEUED.value,
            1,
            1,
        ),
    )

    executor = TaskExecutor()

    async def fake_command(*args, **kwargs):
        return "80/tcp open http", 0, None

    with (
        patch.object(executor, "_execute_command", side_effect=fake_command),
        patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter,
        patch("backend.secuscan.executor.get_plugin_manager") as mock_pm,
        patch(
            "backend.secuscan.executor.process_task_notifications",
            AsyncMock(side_effect=RuntimeError("webhook down")),
        ),
    ):
        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "nmap"
        mock_plugin.capabilities = []
        mock_plugin.safety = {"level": "safe"}
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "127.0.0.1"]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task(task_id)

    row = await db.fetchone(
        "SELECT status, completed_at FROM tasks WHERE id = ?", (task_id,)
    )
    assert row["completed_at"] is not None
    assert row["status"] in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
    await db.disconnect()
