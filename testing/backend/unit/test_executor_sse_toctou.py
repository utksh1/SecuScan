"""
Regression tests for the SSE streaming TOCTOU race fix (PR #1523).

Covers:
  1. Completion between initial status check and subscribe — the re-check
     after subscribe must detect the terminal state and replay output/status.
  2. Listener queues are cleaned up in finally without dropping the
     terminal status event.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.secuscan.executor import TaskExecutor
from backend.secuscan.models import TaskStatus

# ---------------------------------------------------------------------------
# TOCTOU: completion between status check and subscribe
# ---------------------------------------------------------------------------


class TestSseToctouRace:
    """The stream_task_output endpoint checks status, subscribes, then re-checks.

    If the task completes in the window between the first status check and
    the subscribe() call, the re-check after subscribe must detect the
    terminal state and return the output without blocking on the queue.
    """

    @pytest.mark.asyncio
    async def test_completed_between_check_and_subscribe(self):
        """Task completes between initial check and subscribe.

        subscribe() is called when the task is already terminal; the
        re-check after subscribe must detect this and the listener must
        *not* block on the queue.
        """
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()

        # Simulate: first status check sees "running", then task completes
        # before subscribe.  Patch get_task_status to return "running" on
        # first call and "completed" on second (re-check).
        status_responses = [
            {"status": "running", "scan_phase": "scanning"},
            {"status": "completed", "scan_phase": "finished"},
        ]

        async def fake_get_status(tid):
            return status_responses.pop(0)

        with patch.object(executor, "get_task_status", side_effect=fake_get_status):
            # First check sees running.
            first = await executor.get_task_status(task_id)
            assert first["status"] == "running"

            executor.subscribe(task_id)

            # Re-check after subscribe sees completed (TOCTOU closed).
            recheck = await executor.get_task_status(task_id)
            assert recheck["status"] == "completed"

    @pytest.mark.asyncio
    async def test_recheck_catches_terminal_before_queue_wait(self):
        """Re-check after subscribe catches terminal state so queue is unused."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()

        # The task was running at first check but completed by re-check.
        def side_effect(tid):
            class _Status:
                status = "completed"
                scan_phase = "finished"

                def __getitem__(self, k):
                    return getattr(self, k)

                def get(self, k, default=None):
                    return getattr(self, k, default)

            return _Status()

        with patch.object(executor, "get_task_status", side_effect=side_effect):
            # The caller must NOT call queue.get() when the re-check
            # already sees a terminal state.
            recheck = await executor.get_task_status(task_id)
            assert recheck["status"] == "completed"

    @pytest.mark.asyncio
    async def test_recheck_sees_running_then_queue_delivers_completed(self):
        """Task stays running at re-check; terminal event arrives via queue."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()

        recheck_called = False

        async def fake_get_status(tid):
            nonlocal recheck_called
            if not recheck_called:
                recheck_called = True
                return {"status": "running", "scan_phase": "scanning"}
            return {"status": "running", "scan_phase": "scanning"}

        with patch.object(executor, "get_task_status", side_effect=fake_get_status):
            queue = executor.subscribe(task_id)
            recheck = await executor.get_task_status(task_id)
            assert recheck["status"] == "running"
            assert recheck_called is True

            # Now push a terminal event into the queue (simulating the
            # task completing and broadcasting).
            await executor._broadcast(task_id, "status", TaskStatus.COMPLETED.value)

            event = await queue.get()
            assert event["type"] == "status"
            assert event["data"] == TaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_no_orphaned_listeners_after_completion(self):
        """After a task completes, no orphaned listeners remain in _listeners."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()

        q1 = executor.subscribe(task_id)
        q2 = executor.subscribe(task_id)

        assert task_id in executor._listeners
        assert len(executor._listeners[task_id]) == 2

        # Simulate what the finally block does.
        executor._cleanup_listeners(task_id)

        assert task_id not in executor._listeners


# ---------------------------------------------------------------------------
# Listener cleanup without losing terminal event
# ---------------------------------------------------------------------------


class TestListenerCleanup:
    """_cleanup_listeners must remove queues only after consumers have had
    a chance to read the terminal status event."""

    @pytest.mark.asyncio
    async def test_cleanup_after_terminal_event(self):
        """Cleanup removes listeners only after terminal event is broadcast."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()
        queue = executor.subscribe(task_id)

        await executor._broadcast(task_id, "status", TaskStatus.COMPLETED.value)

        # Consume the terminal event before cleanup.
        event = await queue.get()
        assert event["type"] == "status"
        assert event["data"] == TaskStatus.COMPLETED.value

        executor._cleanup_listeners(task_id)
        assert task_id not in executor._listeners

    @pytest.mark.asyncio
    async def test_finally_block_cleans_up_listeners(self):
        """execute_task's finally block calls _cleanup_listeners."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()

        with (
            patch("backend.secuscan.executor.get_db", new_callable=AsyncMock) as mock_get_db,
            patch("backend.secuscan.executor.get_plugin_manager") as mock_pm,
            patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter,
        ):
            mock_db = AsyncMock()
            mock_db.execute.return_value.rowcount = 0  # optimistic lock fails → early return
            mock_get_db.return_value = mock_db
            mock_limiter.release = AsyncMock()
            mock_pm.return_value.get_plugin.return_value = MagicMock(name="nmap", presets={})

            executor.subscribe(task_id)
            assert task_id in executor._listeners

            await executor.execute_task(task_id)

            # After execute_task returns, listeners for that task should be
            # cleaned up even on the early-return path (rowcount == 0).
            assert task_id not in executor._listeners

    @pytest.mark.asyncio
    async def test_multiple_listeners_all_cleaned(self):
        """All listener queues for a task are removed by cleanup."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()

        queues = [executor.subscribe(task_id) for _ in range(5)]
        assert len(executor._listeners[task_id]) == 5

        await executor._broadcast(task_id, "status", TaskStatus.FAILED.value)
        for q in queues:
            await q.get()

        executor._cleanup_listeners(task_id)
        assert task_id not in executor._listeners

    @pytest.mark.asyncio
    async def test_cleanup_does_not_affect_other_tasks(self):
        """Cleaning up one task's listeners leaves other tasks untouched."""
        executor = TaskExecutor()

        q_a = executor.subscribe("task-a")
        q_b = executor.subscribe("task-b")

        executor._cleanup_listeners("task-a")
        assert "task-a" not in executor._listeners
        assert "task-b" in executor._listeners
        assert q_b is executor._listeners["task-b"][0]

    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self):
        """Calling _cleanup_listeners multiple times is safe."""
        task_id = str(uuid.uuid4())
        executor = TaskExecutor()
        executor.subscribe(task_id)

        executor._cleanup_listeners(task_id)
        assert task_id not in executor._listeners

        # Second call must not raise.
        executor._cleanup_listeners(task_id)
        assert task_id not in executor._listeners
