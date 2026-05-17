"""
Tests for ConcurrentTaskLimiter — verifies that concurrent task slots
are correctly acquired with real task IDs and released on completion.
"""

import asyncio
import pytest

from backend.secuscan.ratelimit import ConcurrentTaskLimiter


# ---------------------------------------------------------------------------
# Basic acquire / release behaviour
# ---------------------------------------------------------------------------

def test_acquire_succeeds_when_slots_available():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    ok, msg = asyncio.run(limiter.acquire("task-1"))
    assert ok is True
    assert msg == ""


def test_acquire_tracks_real_task_id():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    asyncio.run(limiter.acquire("task-abc"))
    assert "task-abc" in limiter.running_tasks


def test_acquire_fills_all_slots():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    ok1, _ = asyncio.run(limiter.acquire("task-1"))
    ok2, _ = asyncio.run(limiter.acquire("task-2"))
    assert ok1 is True
    assert ok2 is True
    assert len(limiter.running_tasks) == 2


def test_acquire_blocked_when_full():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    asyncio.run(limiter.acquire("task-1"))
    asyncio.run(limiter.acquire("task-2"))

    ok, msg = asyncio.run(limiter.acquire("task-3"))
    assert ok is False
    assert "2" in msg  # error message should mention the limit


def test_release_frees_slot_for_next_task():
    limiter = ConcurrentTaskLimiter(max_concurrent=1)
    asyncio.run(limiter.acquire("task-1"))

    # Full — next acquire must fail
    ok, _ = asyncio.run(limiter.acquire("task-2"))
    assert ok is False

    # Release task-1 → next acquire must succeed
    asyncio.run(limiter.release("task-1"))
    ok, _ = asyncio.run(limiter.acquire("task-2"))
    assert ok is True


def test_release_unknown_id_is_safe():
    """Releasing a task_id that was never acquired must not raise."""
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    asyncio.run(limiter.release("does-not-exist"))  # must not raise


# ---------------------------------------------------------------------------
# get_available_slots
# ---------------------------------------------------------------------------

def test_available_slots_full_capacity_when_empty():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    slots = asyncio.run(limiter.get_available_slots())
    assert slots == 3


def test_available_slots_decrements_on_acquire():
    limiter = ConcurrentTaskLimiter(max_concurrent=3)
    asyncio.run(limiter.acquire("task-1"))
    assert asyncio.run(limiter.get_available_slots()) == 2


def test_available_slots_zero_when_full():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    asyncio.run(limiter.acquire("task-1"))
    asyncio.run(limiter.acquire("task-2"))
    assert asyncio.run(limiter.get_available_slots()) == 0


def test_available_slots_recovers_after_release():
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    asyncio.run(limiter.acquire("task-1"))
    asyncio.run(limiter.acquire("task-2"))
    asyncio.run(limiter.release("task-1"))
    assert asyncio.run(limiter.get_available_slots()) == 1


# ---------------------------------------------------------------------------
# "temp" regression — the original broken pattern must no longer work
# ---------------------------------------------------------------------------

def test_temp_pattern_does_not_bypass_limit():
    """
    Regression: the old code did acquire('temp') then release('temp')
    immediately, leaving the limiter always empty.  Verify that after
    filling all slots with real IDs, get_available_slots() returns 0.
    """
    limiter = ConcurrentTaskLimiter(max_concurrent=2)
    asyncio.run(limiter.acquire("real-task-1"))
    asyncio.run(limiter.acquire("real-task-2"))

    # Slots are full — a capacity check must see 0
    assert asyncio.run(limiter.get_available_slots()) == 0

    # Simulating the old broken pattern on top of a full limiter
    # acquire+release of a third id should NOT free any real slot
    asyncio.run(limiter.acquire("temp"))   # this itself fails silently (full)
    asyncio.run(limiter.release("temp"))   # no-op since "temp" was never added
    assert asyncio.run(limiter.get_available_slots()) == 0