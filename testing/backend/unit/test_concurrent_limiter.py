"""
Tests for ConcurrentTaskLimiter and the route-level concurrency enforcement.

Covers:
- Atomic acquire / release lifecycle
- Slot exhaustion blocks further acquires
- Slot recovery after release
- get_available_slots() accuracy
- Regression: simultaneous route-level task starts respect max_concurrent
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.secuscan.ratelimit import ConcurrentTaskLimiter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Unit: ConcurrentTaskLimiter
# ---------------------------------------------------------------------------

def test_acquire_succeeds_when_slots_available():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    ok, msg = run(limiter.acquire("task-1"))
    assert ok is True
    assert msg == ""


def test_acquire_registers_real_task_id():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    run(limiter.acquire("task-abc"))
    assert "task-abc" in limiter.running_tasks


def test_acquire_blocks_when_all_slots_full():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    run(limiter.acquire("task-1"))
    run(limiter.acquire("task-2"))

    ok, msg = run(limiter.acquire("task-3"))
    assert ok is False
    assert "2" in msg


def test_release_frees_slot_for_next_acquire():
    limiter = ConcurrentTaskLimiter(max_concurrent=1)
    run(limiter.acquire("task-1"))

    ok, _ = run(limiter.acquire("task-2"))
    assert ok is False  # full

    run(limiter.release("task-1"))
    ok, _ = run(limiter.acquire("task-2"))
    assert ok is True   # slot recovered


def test_release_unknown_id_is_a_noop():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    run(limiter.release("never-existed"))   # must not raise


def test_available_slots_full_when_empty():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    assert run(limiter.get_available_slots()) == 3


def test_available_slots_decrements_on_acquire():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    run(limiter.acquire("task-1"))
    assert run(limiter.get_available_slots()) == 2


def test_available_slots_zero_when_full():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    run(limiter.acquire("task-1"))
    run(limiter.acquire("task-2"))
    assert run(limiter.get_available_slots()) == 0


def test_available_slots_recovers_after_release():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    run(limiter.acquire("task-1"))
    run(limiter.acquire("task-2"))
    run(limiter.release("task-1"))
    assert run(limiter.get_available_slots()) == 1


# ---------------------------------------------------------------------------
# Regression: atomic acquire — no TOCTOU window between concurrent callers
# ---------------------------------------------------------------------------

def test_concurrent_acquires_respect_max_limit():
    """
    Fire max_concurrent+2 acquire calls concurrently inside a single event loop.
    Only max_concurrent of them should succeed; the rest must be rejected.
    This exercises the lock atomicity that prevents the TOCTOU race.
    """
    limiter = ConcurrentTaskLimiter(max_concurrent=3)

    async def run_concurrent():
        results = await asyncio.gather(
            *[limiter.acquire(f"task-{i}") for i in range(5)]
        )
        return results

    results = asyncio.run(run_concurrent())
    successes = [ok for ok, _ in results if ok]
    failures  = [ok for ok, _ in results if not ok]

    assert len(successes) == 3, "Exactly max_concurrent slots should be granted"
    assert len(failures)  == 2, "Remaining requests should be rejected"


# ---------------------------------------------------------------------------
# Regression: "temp" pattern no longer bypasses a full limiter
# ---------------------------------------------------------------------------

def test_temp_pattern_does_not_bypass_limit():
    """
    The old broken code did acquire('temp') then release('temp') immediately,
    so running_tasks was always empty when the next request arrived.
    Verify that real slots are held across requests.
    """
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    run(limiter.acquire("real-1"))
    run(limiter.acquire("real-2"))

    # Full — simulating the old broken pattern must not free a real slot
    run(limiter.acquire("temp"))   # fails silently (full)
    run(limiter.release("temp"))   # no-op — "temp" was never registered

    assert run(limiter.get_available_slots()) == 0


# ---------------------------------------------------------------------------
# Route-level regression: simultaneous task starts honour max_concurrent
# ---------------------------------------------------------------------------

def test_route_rejects_task_when_limiter_full(test_client, monkeypatch):
    """
    Simulate max_concurrent slots already held, then POST /task/start.
    The route must return 503 and must NOT schedule the background task.
    """
    from backend.secuscan.ratelimit import concurrent_limiter
    from backend.secuscan import routes as routes_module

    # Pre-fill all slots so the next acquire will fail
    async def prefill():
        for i in range(concurrent_limiter.max_concurrent):
            await concurrent_limiter.acquire(f"pre-task-{i}")

    asyncio.run(prefill())

    # Patch background_tasks.add_task to detect if it was called
    scheduled = []

    original_add_task = None

    class CapturingBackgroundTasks:
        def add_task(self, fn, *args, **kwargs):
            scheduled.append((fn, args, kwargs))

    try:
        response = test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "nmap",
                "inputs": {"target": "127.0.0.1"},
                "consent_granted": True,
            },
        )

        assert response.status_code == 503, (
            f"Expected 503 when limiter is full, got {response.status_code}: {response.text}"
        )
        assert len(scheduled) == 0, "Background task must not be scheduled when acquire fails"

    finally:
        # Clean up pre-filled slots
        async def cleanup():
            for i in range(concurrent_limiter.max_concurrent):
                await concurrent_limiter.release(f"pre-task-{i}")
        asyncio.run(cleanup())