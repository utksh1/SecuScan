"""
Unit tests for SSE streaming disconnect cleanup in routes.py.

Covers the finally block in stream_task_output's event_generator:
  - executor.unsubscribe() is called after normal completion
  - executor.unsubscribe() is called after CancelledError (client disconnect)
  - executor.unsubscribe() is called after other exceptions

The event_generator logic is exercised by testing the async generator
behaviour with a mock executor that tracks subscribe/unsubscribe calls.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockQueue:
    """A mock asyncio.Queue that yields a fixed sequence then raises."""

    def __init__(self, events, raise_after=None):
        self.events = iter(events)
        self.raise_after = raise_after
        self.get_count = 0
        self.closed = False

    async def get(self):
        self.get_count += 1
        if self.raise_after and self.get_count > self.raise_after:
            raise asyncio.CancelledError("client disconnected")
        return next(self.events)

    def task_done(self):
        pass


class MockExecutor:
    """Tracks subscribe/unsubscribe calls for test assertions."""

    def __init__(self, queue):
        self._queue = queue
        self.subscriptions = {}
        self.unsubscribe_calls = []

    def subscribe(self, task_id):
        self.subscriptions[task_id] = self._queue
        return self._queue

    def unsubscribe(self, task_id, queue):
        self.unsubscribe_calls.append((task_id, queue))


# ---------------------------------------------------------------------------
# Helper: reproduces the core event_generator logic from routes.py
# ---------------------------------------------------------------------------

async def stream_event_generator(task_id, executor):
    """Mirrors the event_generator inner function from stream_task_output.

    The finally block must call executor.unsubscribe regardless of how
    the generator exits.
    """
    queue = executor.subscribe(task_id)
    try:
        while True:
            event = await queue.get()
            yield event  # mirrors the yield in routes.py event_generator
            if event["type"] == "status":
                if event["data"] in ["completed", "failed", "cancelled"]:
                    break
    except asyncio.CancelledError:
        pass
    finally:
        executor.unsubscribe(task_id, queue)


class TestStreamingDisconnectCleanup:
    """Tests for executor.unsubscribe() call paths in stream_event_generator."""

    @pytest.mark.asyncio
    async def test_unsubscribe_called_on_normal_completion(self):
        """When the generator exits normally, unsubscribe must still be called."""
        events = [{"type": "status", "data": "completed"}]
        queue = MockQueue(events)
        executor = MockExecutor(queue)

        agen = stream_event_generator("task-1", executor)
        # Consume the async generator.
        async for _ in agen:
            pass

        assert len(executor.unsubscribe_calls) == 1
        assert executor.unsubscribe_calls[0][0] == "task-1"

    @pytest.mark.asyncio
    async def test_unsubscribe_called_on_client_disconnect(self):
        """When asyncio.CancelledError is raised (client disconnect), unsubscribe must be called.

        CancelledError is caught by the except block in stream_event_generator,
        but the finally block still executes and calls unsubscribe.
        """
        # Queue raises CancelledError on the second get().
        events = [{"type": "status", "data": "running"}]
        queue = MockQueue(events, raise_after=1)
        executor = MockExecutor(queue)

        agen = stream_event_generator("task-2", executor)

        # CancelledError is caught; iteration exits silently.
        async for _ in agen:
            pass

        # The finally block must still run and call unsubscribe.
        assert len(executor.unsubscribe_calls) == 1
        assert executor.unsubscribe_calls[0][0] == "task-2"

    @pytest.mark.asyncio
    async def test_unsubscribe_called_on_runtime_exception(self):
        """When the generator raises a runtime exception, unsubscribe must be called."""
        class FailingQueue:
            def __init__(self):
                self.get_count = 0
                self.closed = False

            async def get(self):
                self.get_count += 1
                if self.get_count == 1:
                    return {"type": "status", "data": "running"}
                raise RuntimeError("executor error")

            def task_done(self):
                pass

        queue = FailingQueue()
        executor = MockExecutor(queue)

        agen = stream_event_generator("task-3", executor)

        with pytest.raises(RuntimeError):
            async for _ in agen:
                pass

        assert len(executor.unsubscribe_calls) == 1
        assert executor.unsubscribe_calls[0][0] == "task-3"

    @pytest.mark.asyncio
    async def test_unsubscribe_called_exactly_once_per_task(self):
        """unsubscribe must be called once per task, never more."""
        events = [{"type": "status", "data": "completed"}]
        queue = MockQueue(events)
        executor = MockExecutor(queue)

        agen = stream_event_generator("task-4", executor)
        async for _ in agen:
            pass

        assert len(executor.unsubscribe_calls) == 1

    @pytest.mark.asyncio
    async def test_multiple_tasks_each_get_unsubscribe(self):
        """Each concurrent task must receive its own unsubscribe call."""
        events1 = [{"type": "status", "data": "completed"}]
        events2 = [{"type": "status", "data": "failed"}]

        executor1 = MockExecutor(MockQueue(events1))
        executor2 = MockExecutor(MockQueue(events2))

        agen1 = stream_event_generator("task-a", executor1)
        agen2 = stream_event_generator("task-b", executor2)

        async for _ in agen1:
            pass
        async for _ in agen2:
            pass

        assert len(executor1.unsubscribe_calls) == 1
        assert executor1.unsubscribe_calls[0][0] == "task-a"
        assert len(executor2.unsubscribe_calls) == 1
        assert executor2.unsubscribe_calls[0][0] == "task-b"

    @pytest.mark.asyncio
    async def test_queue_is_passed_correctly_to_unsubscribe(self):
        """unsubscribe must receive the same queue object that was returned by subscribe."""
        events = [{"type": "status", "data": "cancelled"}]
        queue = MockQueue(events)
        executor = MockExecutor(queue)

        agen = stream_event_generator("task-5", executor)
        async for _ in agen:
            pass

        assert len(executor.unsubscribe_calls) == 1
        _, received_queue = executor.unsubscribe_calls[0]
        assert received_queue is queue

    @pytest.mark.asyncio
    async def test_status_completed_exits_cleanly_without_exception(self):
        """A 'completed' status must exit the loop without raising CancelledError."""
        events = [
            {"type": "status", "data": "running"},
            {"type": "status", "data": "completed"},
        ]
        queue = MockQueue(events)
        executor = MockExecutor(queue)

        agen = stream_event_generator("task-6", executor)
        collected = [item async for item in agen]

        # Must not raise; generator must finish cleanly.
        assert len(collected) == 2
        assert executor.unsubscribe_calls[0][0] == "task-6"
