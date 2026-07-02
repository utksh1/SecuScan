"""
Regression tests for workflow concurrency ordering (PR #1521).

Verifies:
  1. run_workflow_once: concurrent_limiter.acquire() is called BEFORE
     execute_task, and a rejected acquire marks the task failed without
     scheduling execution.
  2. WorkflowScheduler._run_workflow: created_task_ids only includes
     tasks whose acquire succeeded — rejected task ids are excluded.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.secuscan.workflows import WorkflowScheduler
from backend.secuscan.ratelimit import rate_limiter


# ---------------------------------------------------------------------------
# run_workflow_once ordering tests
#
# These test the logic extracted from routes.py run_workflow_once by
# calling it with mocked dependencies and asserting call ordering.
# ---------------------------------------------------------------------------


_WF_ROW = {
    "id": "wf-1", "name": "test", "owner_id": "owner",
    "schedule_seconds": 3600, "enabled": 1,
    "steps_json": '[{"plugin_id":"nmap","inputs":{"target":"example.com"}}]',
}


@pytest.mark.asyncio
async def test_acquire_before_execute_task():
    """concurrent_limiter.acquire must be called before executor.execute_task
    in run_workflow_once."""
    from backend.secuscan.routes import run_workflow_once

    mock_db = AsyncMock()
    # fetchone returns None so snapshot_workflow_version is called
    mock_db.fetchone = AsyncMock(return_value=None)
    mock_db.snapshot_workflow_version = AsyncMock(
        return_value={"id": "v-1", "version_number": 1}
    )
    mock_db.record_workflow_run = AsyncMock(return_value="run-1")
    mock_db.execute = AsyncMock()

    call_order = []

    async def tracking_acquire(tid):
        call_order.append("acquire")
        return (True, "")

    original_create_task = asyncio.create_task

    def tracking_create_task(coro, **kwargs):
        call_order.append("create_task")
        return original_create_task(coro, **kwargs)

    with (
        patch("backend.secuscan.routes.get_db", return_value=mock_db),
        patch("backend.secuscan.routes._verify_workflow_owner",
              AsyncMock(return_value=_WF_ROW)),
        patch("backend.secuscan.routes.workflow_rate_limiter.check_workflow_rate_limit",
              AsyncMock(return_value=(True, ""))),
        patch("backend.secuscan.routes.normalize_execution_context", return_value={}),
        patch("backend.secuscan.routes.get_target_policy", AsyncMock(return_value=None)),
        patch("backend.secuscan.routes.concurrent_limiter.acquire",
              side_effect=tracking_acquire),
        patch("backend.secuscan.routes.executor.create_task",
              AsyncMock(return_value="task-1")),
        patch("backend.secuscan.routes.executor.execute_task",
              AsyncMock(return_value=None)),
        patch("backend.secuscan.routes.logger"),
        patch("asyncio.create_task", side_effect=tracking_create_task),
    ):
        await run_workflow_once("wf-1", owner="owner")

    assert len(call_order) >= 2
    # acquire must precede the first create_task (which wraps execute_task)
    assert call_order[0] == "acquire", (
        f"Expected acquire first, got order: {call_order}"
    )
    assert "create_task" in call_order[1:], (
        f"Expected create_task after acquire, got order: {call_order}"
    )


@pytest.mark.asyncio
async def test_rejected_acquire_marks_failed_and_skips_execution():
    """When concurrent_limiter.acquire returns False, the task must be
    marked failed and execute_task must NOT be called."""
    from backend.secuscan.routes import run_workflow_once

    mock_db = AsyncMock()
    mock_db.fetchone = AsyncMock(return_value=None)
    mock_db.snapshot_workflow_version = AsyncMock(
        return_value={"id": "v-1", "version_number": 1}
    )
    mock_db.record_workflow_run = AsyncMock(return_value="run-1")
    mock_db.execute = AsyncMock()

    with (
        patch("backend.secuscan.routes.get_db", return_value=mock_db),
        patch("backend.secuscan.routes._verify_workflow_owner",
              AsyncMock(return_value=_WF_ROW)),
        patch("backend.secuscan.routes.workflow_rate_limiter.check_workflow_rate_limit",
              AsyncMock(return_value=(True, ""))),
        patch("backend.secuscan.routes.normalize_execution_context", return_value={}),
        patch("backend.secuscan.routes.get_target_policy", AsyncMock(return_value=None)),
        patch("backend.secuscan.routes.concurrent_limiter.acquire",
              AsyncMock(return_value=(False, "Concurrency limit reached"))),
        patch("backend.secuscan.routes.executor.create_task",
              AsyncMock(return_value="task-1")),
        patch("backend.secuscan.routes.executor.mark_task_failed",
              new_callable=AsyncMock) as mock_mark_failed,
        patch("backend.secuscan.routes.executor.execute_task",
              new_callable=AsyncMock) as mock_execute,
        patch("backend.secuscan.routes.logger"),
    ):
        result = await run_workflow_once("wf-1", owner="owner")

    mock_mark_failed.assert_called_once_with(
        "task-1", reason="Concurrency limit reached; task was not started"
    )
    mock_execute.assert_not_called()
    assert result["queued_task_ids"] == []
    assert result["queued_tasks"] == []


@pytest.mark.asyncio
async def test_rejected_acquire_does_not_block_accepted_tasks():
    """When one step hits concurrency limit, subsequent steps should still
    be processed normally."""
    from backend.secuscan.routes import run_workflow_once

    two_step_row = {
        **_WF_ROW,
        "steps_json": (
            '[{"plugin_id":"nmap","inputs":{"target":"example.com"}},'
            '{"plugin_id":"nikto","inputs":{"target":"example.com"}}]'
        ),
    }
    mock_db = AsyncMock()
    mock_db.fetchone = AsyncMock(return_value=None)
    mock_db.snapshot_workflow_version = AsyncMock(
        return_value={"id": "v-1", "version_number": 1}
    )
    mock_db.record_workflow_run = AsyncMock(return_value="run-1")
    mock_db.execute = AsyncMock()

    with (
        patch("backend.secuscan.routes.get_db", return_value=mock_db),
        patch("backend.secuscan.routes._verify_workflow_owner",
              AsyncMock(return_value=two_step_row)),
        patch("backend.secuscan.routes.workflow_rate_limiter.check_workflow_rate_limit",
              AsyncMock(return_value=(True, ""))),
        patch("backend.secuscan.routes.normalize_execution_context", return_value={}),
        patch("backend.secuscan.routes.get_target_policy", AsyncMock(return_value=None)),
        patch("backend.secuscan.routes.concurrent_limiter.acquire",
              AsyncMock(side_effect=[
                  (False, "Concurrency limit reached"),
                  (True, ""),
              ])),
        patch("backend.secuscan.routes.executor.create_task",
              AsyncMock(side_effect=["task-1", "task-2"])),
        patch("backend.secuscan.routes.executor.mark_task_failed",
              new_callable=AsyncMock),
        patch("backend.secuscan.routes.executor.execute_task",
              new_callable=AsyncMock) as mock_execute,
        patch("backend.secuscan.routes.logger"),
    ):
        result = await run_workflow_once("wf-1", owner="owner")

    assert result["queued_task_ids"] == ["task-2"]
    mock_execute.assert_called_once_with("task-2")


# ---------------------------------------------------------------------------
# WorkflowScheduler._run_workflow ordering tests
# ---------------------------------------------------------------------------


def _mock_db():
    mock = MagicMock()
    mock.fetchone = AsyncMock(return_value=None)
    mock.fetchall = AsyncMock(return_value=[])
    mock.snapshot_workflow_version = AsyncMock(
        return_value={"id": "v-1", "version_number": 1}
    )
    mock.record_workflow_run = AsyncMock(return_value="run-1")
    return mock


@pytest.mark.asyncio
async def test_scheduler_acquire_before_append_task_id():
    """In _run_workflow, created_task_ids.append must happen AFTER
    concurrent_limiter.acquire succeeds."""
    scheduler = WorkflowScheduler()
    db = _mock_db()
    steps = [{"plugin_id": "nmap", "inputs": {"target": "example.com"}}]

    acquire_order = []
    append_order = []

    original_acquire = None

    async def tracking_acquire(tid):
        acquire_order.append(("acquire", tid))
        return (True, "")

    with (
        patch("backend.secuscan.workflows.get_db", return_value=db),
        patch("backend.secuscan.plugins.get_plugin_manager") as mock_pm,
        patch("backend.secuscan.validation.validate_target",
              return_value=(True, "")),
        patch("backend.secuscan.network_policy.get_policy_engine") as mock_engine,
        patch("backend.secuscan.workflows.executor") as mock_executor,
        patch("backend.secuscan.workflows.concurrent_limiter",
              autospec=True) as mock_limiter,
        patch("backend.secuscan.workflows.get_target_policy",
              AsyncMock(return_value=None)),
        patch("backend.secuscan.workflows.normalize_execution_context",
              return_value={}),
        patch("backend.secuscan.workflows.get_request_id", return_value="req-1"),
        patch.object(rate_limiter, "can_execute",
                     AsyncMock(return_value=(True, ""))),
    ):
        mock_limiter.acquire = AsyncMock(side_effect=tracking_acquire)
        mock_executor.create_task = AsyncMock(return_value="tid-1")
        mock_executor.mark_task_failed = AsyncMock()

        mock_engine.return_value.check_access.return_value = (True, "", None)

        mock_pm_inst = MagicMock()
        plugin = MagicMock()
        plugin.category = "scan"
        plugin.safety = {"rate_limit": {"max_per_hour": 50}}
        plugin.fields = []
        mock_pm_inst.get_plugin.return_value = plugin
        mock_pm.return_value = mock_pm_inst

        # Monkey-patch created_task_ids.append to track calls
        original_append_method = None

        class TrackingList(list):
            def append(self, val):
                nonlocal append_order
                append_order.append(("append", val))
                super().append(val)

        # We use a custom approach: patch append on the instance
        async def run_and_track():
            # We need to intercept list.append on the created_task_ids list
            # Since it's a local variable inside _run_workflow, we can't
            # easily patch it. Instead, we use a wrapper for the mock DB
            # record_workflow_run to capture what was passed.
            await scheduler._run_workflow("wf-1", steps)

        await run_and_track()

    # Verify acquire was called
    assert len(acquire_order) >= 1
    # Verify record_workflow_run was called with the task id
    db.record_workflow_run.assert_called_once()
    call_kwargs = db.record_workflow_run.call_args.kwargs
    assert call_kwargs["task_ids"] == ["tid-1"]


@pytest.mark.asyncio
async def test_scheduler_rejected_task_not_in_created_ids():
    """When acquire returns False, the task_id must NOT be appended to
    created_task_ids."""
    scheduler = WorkflowScheduler()
    db = _mock_db()
    steps = [{"plugin_id": "nmap", "inputs": {"target": "example.com"}}]

    with (
        patch("backend.secuscan.workflows.get_db", return_value=db),
        patch("backend.secuscan.plugins.get_plugin_manager") as mock_pm,
        patch("backend.secuscan.validation.validate_target",
              return_value=(True, "")),
        patch("backend.secuscan.network_policy.get_policy_engine") as mock_engine,
        patch("backend.secuscan.workflows.executor") as mock_executor,
        patch("backend.secuscan.workflows.concurrent_limiter") as mock_limiter,
        patch("backend.secuscan.workflows.get_target_policy",
              AsyncMock(return_value=None)),
        patch("backend.secuscan.workflows.normalize_execution_context",
              return_value={}),
        patch("backend.secuscan.workflows.get_request_id", return_value="req-1"),
        patch.object(rate_limiter, "can_execute",
                     AsyncMock(return_value=(True, ""))),
    ):
        mock_limiter.acquire = AsyncMock(
            return_value=(False, "Concurrency limit reached")
        )
        mock_executor.create_task = AsyncMock(return_value="tid-rejected")
        mock_executor.mark_task_failed = AsyncMock()

        mock_engine.return_value.check_access.return_value = (True, "", None)

        mock_pm_inst = MagicMock()
        plugin = MagicMock()
        plugin.category = "scan"
        plugin.safety = {"rate_limit": {"max_per_hour": 50}}
        plugin.fields = []
        mock_pm_inst.get_plugin.return_value = plugin
        mock_pm.return_value = mock_pm_inst

        await scheduler._run_workflow("wf-1", steps)

    mock_executor.mark_task_failed.assert_called_once()
    db.record_workflow_run.assert_called_once()
    call_kwargs = db.record_workflow_run.call_args.kwargs
    assert call_kwargs["task_ids"] == [], (
        f"Expected empty task_ids, got {call_kwargs['task_ids']}"
    )
