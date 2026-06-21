"""
Unit tests for sequential workflow step execution and concurrency limiters.

Verifies:
1. Workflow steps execute sequentially in declaration order.
2. A downstream step only executes if the previous step completed successfully.
3. If any step fails, subsequent tasks are cancelled.
4. Concurrency slots are acquired for each step.
5. Upstream target validation or policy check failures abort downstream steps.
"""

import json
import uuid
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from backend.secuscan.database import Database
from backend.secuscan.workflows import (
    WorkflowScheduler,
    _execute_workflow_sequentially,
    _cancel_remaining_tasks,
    _finalize_workflow_run,
)


@pytest_asyncio.fixture
async def db(tmp_path):
    instance = Database(str(tmp_path / "test.db"))
    await instance.connect()
    # Mock global get_db to return this database instance
    with patch("backend.secuscan.workflows.get_db", return_value=instance), \
         patch("backend.secuscan.database.get_db", return_value=instance):
        yield instance
    await instance.disconnect()


def _make_mock_plugin(plugin_id="plugin_x", category="scan"):
    p = MagicMock()
    p.id = plugin_id
    p.category = category
    p.safety = {"rate_limit": {"max_per_hour": 50}}
    p.fields = []
    return p


class TestSequentialWorkflowExecution:

    @pytest.mark.asyncio
    async def test_successful_sequential_execution(self, db):
        """Verify that steps execute sequentially and complete successfully."""
        workflow_id = uuid.uuid4().hex
        steps = [
            {"plugin_id": "plugin_1", "inputs": {"target": "127.0.0.1"}},
            {"plugin_id": "plugin_2", "inputs": {"target": "127.0.0.1"}},
            {"plugin_id": "plugin_3", "inputs": {"target": "127.0.0.1"}},
        ]
        created_task_ids = ["t-1", "t-2", "t-3"]

        # Insert tasks into DB as queued
        for tid, step in zip(created_task_ids, steps):
            await db.execute(
                "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
                "VALUES (?, 'default', ?, ?, '127.0.0.1', 'queued', '{}')",
                (tid, step["plugin_id"], step["plugin_id"]),
            )

        run_id = await db.record_workflow_run(workflow_id, "v-1", 1, created_task_ids)

        # Track execution order
        execution_order = []

        async def mock_execute_task(task_id):
            # Check previous tasks are completed
            idx = created_task_ids.index(task_id)
            for prev_idx in range(idx):
                prev_tid = created_task_ids[prev_idx]
                row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (prev_tid,))
                assert row["status"] == "completed", f"Previous task {prev_tid} was not completed when {task_id} started!"

            execution_order.append(task_id)
            await db.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))

        mock_pm = MagicMock()
        mock_pm.get_plugin.side_effect = lambda pid: _make_mock_plugin(pid)

        mock_executor = MagicMock()
        mock_executor.execute_task = AsyncMock(side_effect=mock_execute_task)

        mock_concurrent = MagicMock()
        mock_concurrent.acquire = AsyncMock(return_value=(True, ""))

        with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm), \
             patch("backend.secuscan.workflows.executor", mock_executor), \
             patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent), \
             patch("backend.secuscan.workflows.get_target_policy", return_value=None), \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")):

            await _execute_workflow_sequentially(
                workflow_id=workflow_id,
                run_id=run_id,
                steps=steps,
                created_task_ids=created_task_ids,
                owner_id="default",
            )

        assert execution_order == created_task_ids
        assert mock_concurrent.acquire.call_count == 3
        mock_concurrent.acquire.assert_any_call("t-1")
        mock_concurrent.acquire.assert_any_call("t-2")
        mock_concurrent.acquire.assert_any_call("t-3")

        # Verify run finalizes successfully
        await _finalize_workflow_run(run_id, poll_interval=0.01, max_polls=5)
        run_row = await db.fetchone("SELECT status FROM workflow_runs WHERE id = ?", (run_id,))
        assert run_row["status"] == "completed"

    @pytest.mark.asyncio
    async def test_upstream_failure_cancels_downstream_tasks(self, db):
        """Verify that a task failure cancels all subsequent steps."""
        workflow_id = uuid.uuid4().hex
        steps = [
            {"plugin_id": "plugin_1", "inputs": {"target": "127.0.0.1"}},
            {"plugin_id": "plugin_2", "inputs": {"target": "127.0.0.1"}},
            {"plugin_id": "plugin_3", "inputs": {"target": "127.0.0.1"}},
        ]
        created_task_ids = ["t-1", "t-2", "t-3"]

        for tid, step in zip(created_task_ids, steps):
            await db.execute(
                "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
                "VALUES (?, 'default', ?, ?, '127.0.0.1', 'queued', '{}')",
                (tid, step["plugin_id"], step["plugin_id"]),
            )

        run_id = await db.record_workflow_run(workflow_id, "v-1", 1, created_task_ids)

        executed = []

        async def mock_execute_task(task_id):
            executed.append(task_id)
            if task_id == "t-2":
                await db.execute("UPDATE tasks SET status = 'failed', error_message = 'crashed' WHERE id = ?", (task_id,))
            else:
                await db.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))

        mock_pm = MagicMock()
        mock_pm.get_plugin.side_effect = lambda pid: _make_mock_plugin(pid)

        mock_executor = MagicMock()
        mock_executor.execute_task = AsyncMock(side_effect=mock_execute_task)

        mock_concurrent = MagicMock()
        mock_concurrent.acquire = AsyncMock(return_value=(True, ""))

        with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm), \
             patch("backend.secuscan.workflows.executor", mock_executor), \
             patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent), \
             patch("backend.secuscan.workflows.get_target_policy", return_value=None), \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")):

            await _execute_workflow_sequentially(
                workflow_id=workflow_id,
                run_id=run_id,
                steps=steps,
                created_task_ids=created_task_ids,
                owner_id="default",
            )

        # t-3 should not be executed because t-2 failed
        assert executed == ["t-1", "t-2"]
        mock_executor.execute_task.assert_any_call("t-1")
        mock_executor.execute_task.assert_any_call("t-2")
        with pytest.raises(AssertionError):
            mock_executor.execute_task.assert_any_call("t-3")

        # Verify t-3 is cancelled in db
        t3_row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = 't-3'")
        assert t3_row["status"] == "cancelled"
        assert "upstream step failure" in t3_row["error_message"].lower()

        # Verify run finalizes with cancelled status
        await _finalize_workflow_run(run_id, poll_interval=0.01, max_polls=5)
        run_row = await db.fetchone("SELECT status FROM workflow_runs WHERE id = ?", (run_id,))
        assert run_row["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_concurrency_limit_exhaustion_aborts_workflow(self, db):
        """Verify that failure to acquire concurrency slot aborts execution."""
        workflow_id = uuid.uuid4().hex
        steps = [
            {"plugin_id": "plugin_1", "inputs": {"target": "127.0.0.1"}},
            {"plugin_id": "plugin_2", "inputs": {"target": "127.0.0.1"}},
        ]
        created_task_ids = ["t-1", "t-2"]

        for tid, step in zip(created_task_ids, steps):
            await db.execute(
                "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
                "VALUES (?, 'default', ?, ?, '127.0.0.1', 'queued', '{}')",
                (tid, step["plugin_id"], step["plugin_id"]),
            )

        run_id = await db.record_workflow_run(workflow_id, "v-1", 1, created_task_ids)

        executed = []

        async def mock_execute_task(task_id):
            executed.append(task_id)
            await db.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))

        async def mock_mark_task_failed(task_id, reason=None):
            await db.execute("UPDATE tasks SET status = 'failed', error_message = ? WHERE id = ?", (reason, task_id))

        mock_pm = MagicMock()
        mock_pm.get_plugin.side_effect = lambda pid: _make_mock_plugin(pid)

        mock_executor = MagicMock()
        mock_executor.execute_task = AsyncMock(side_effect=mock_execute_task)
        mock_executor.mark_task_failed = AsyncMock(side_effect=mock_mark_task_failed)

        # Fail concurrency slot acquisition for the second task
        async def mock_acquire(task_id):
            if task_id == "t-2":
                return False, "Concurrency limit reached"
            return True, ""

        mock_concurrent = MagicMock()
        mock_concurrent.acquire = AsyncMock(side_effect=mock_acquire)

        with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm), \
             patch("backend.secuscan.workflows.executor", mock_executor), \
             patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent), \
             patch("backend.secuscan.workflows.get_target_policy", return_value=None), \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")):

            await _execute_workflow_sequentially(
                workflow_id=workflow_id,
                run_id=run_id,
                steps=steps,
                created_task_ids=created_task_ids,
                owner_id="default",
            )

        # t-2 should not execute
        assert executed == ["t-1"]
        mock_executor.mark_task_failed.assert_called_once_with("t-2", reason="Concurrency limit reached")

        # Verify downstream tasks cancelled/failed
        t2_row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = 't-2'")
        assert t2_row["status"] == "failed"
        assert "concurrency limit reached" in t2_row["error_message"].lower()

    @pytest.mark.asyncio
    async def test_validation_failure_aborts_workflow(self, db):
        """Verify that target validation failure aborts downstream steps."""
        workflow_id = uuid.uuid4().hex
        steps = [
            {"plugin_id": "plugin_1", "inputs": {"target": "invalid_target"}},
            {"plugin_id": "plugin_2", "inputs": {"target": "127.0.0.1"}},
        ]
        created_task_ids = ["t-1", "t-2"]

        for tid, step in zip(created_task_ids, steps):
            await db.execute(
                "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
                "VALUES (?, 'default', ?, ?, ?, 'queued', '{}')",
                (tid, step["plugin_id"], step["plugin_id"], step["inputs"]["target"]),
            )

        run_id = await db.record_workflow_run(workflow_id, "v-1", 1, created_task_ids)

        async def mock_mark_task_failed(task_id, reason=None):
            await db.execute("UPDATE tasks SET status = 'failed', error_message = ? WHERE id = ?", (reason, task_id))

        mock_pm = MagicMock()
        mock_pm.get_plugin.side_effect = lambda pid: _make_mock_plugin(pid)

        mock_executor = MagicMock()
        mock_executor.execute_task = AsyncMock()
        mock_executor.mark_task_failed = AsyncMock(side_effect=mock_mark_task_failed)

        mock_concurrent = MagicMock()

        with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm), \
             patch("backend.secuscan.workflows.executor", mock_executor), \
             patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent), \
             patch("backend.secuscan.workflows.get_target_policy", return_value=None), \
             patch("backend.secuscan.validation.validate_target", return_value=(False, "Target validation failed")):

            await _execute_workflow_sequentially(
                workflow_id=workflow_id,
                run_id=run_id,
                steps=steps,
                created_task_ids=created_task_ids,
                owner_id="default",
            )

        # t-1 should be marked failed, t-2 cancelled
        mock_executor.mark_task_failed.assert_called_once_with("t-1", reason="Target validation failed: Target validation failed")
        mock_executor.execute_task.assert_not_called()

        t1_row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = 't-1'")
        assert t1_row["status"] == "failed"
        assert "target validation failed" in t1_row["error_message"].lower()

        t2_row = await db.fetchone("SELECT status FROM tasks WHERE id = 't-2'")
        assert t2_row["status"] == "cancelled"

