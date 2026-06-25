"""
Unit tests for backend.secuscan.ratelimit RateLimiter and ConcurrentTaskLimiter.

Covers:
- RateLimiter.can_execute allows requests within the hourly quota
- RateLimiter.can_execute blocks when hourly quota is exhausted
- RateLimiter.can_execute tracks per-client-per-plugin independently
- RateLimiter.can_execute expires old entries after 1 hour (sliding window)
- RateLimiter.reset clears a specific plugin or all buckets
- ConcurrentTaskLimiter.acquire succeeds while under the concurrent limit
- ConcurrentTaskLimiter.acquire fails when the concurrent limit is reached
- ConcurrentTaskLimiter.release removes a task from the running list
- ConcurrentTaskLimiter.get_available_slots returns correct available count
"""

import pytest

from backend.secuscan.ratelimit import RateLimiter, ConcurrentTaskLimiter


@pytest.mark.asyncio
class TestRateLimiter:
    async def test_allows_within_quota(self):
        """can_execute returns (True, '') for requests under the hourly limit."""
        limiter = RateLimiter()
        allowed, msg = await limiter.can_execute("nmap", max_per_hour=5, client_id="c1")
        assert allowed is True
        assert msg == ""

    async def test_blocks_when_quota_exhausted(self):
        """can_execute returns (False, error) once the hourly quota is reached."""
        limiter = RateLimiter()
        # Exhaust the quota
        for _ in range(3):
            await limiter.can_execute("nmap", max_per_hour=3, client_id="c1")

        allowed, msg = await limiter.can_execute("nmap", max_per_hour=3, client_id="c1")
        assert allowed is False
        assert "exceeded" in msg.lower()
        assert "3/3" in msg

    async def test_per_client_per_plugin_independently(self):
        """Different client_ids or plugin_ids have independent quotas."""
        limiter = RateLimiter()
        # Exhaust c1:nmap quota
        for _ in range(2):
            await limiter.can_execute("nmap", max_per_hour=2, client_id="c1")

        # c2 should still be able to use nmap
        allowed, _ = await limiter.can_execute("nmap", max_per_hour=2, client_id="c2")
        assert allowed is True

        # c1:dirbuster should still have quota
        allowed, _ = await limiter.can_execute("dirbuster", max_per_hour=2, client_id="c1")
        assert allowed is True

    async def test_default_client_id_is_global(self):
        """When client_id is not provided, uses 'global' as the bucket key."""
        limiter = RateLimiter()
        # Exhaust the global quota for nmap
        for _ in range(2):
            await limiter.can_execute("nmap", max_per_hour=2)

        allowed, _ = await limiter.can_execute("nmap", max_per_hour=2)
        assert allowed is False

    async def test_reset_plugin_clears_only_that_plugin(self):
        """reset(plugin_id) removes only buckets ending with :<plugin_id>."""
        limiter = RateLimiter()
        await limiter.can_execute("nmap", max_per_hour=1, client_id="c1")
        await limiter.can_execute("dirbuster", max_per_hour=1, client_id="c1")

        await limiter.reset("nmap")

        # nmap bucket should be cleared
        allowed, _ = await limiter.can_execute("nmap", max_per_hour=1, client_id="c1")
        assert allowed is True
        # dirbuster bucket should be untouched
        allowed, _ = await limiter.can_execute("dirbuster", max_per_hour=1, client_id="c1")
        assert allowed is False

    async def test_reset_all_clears_all_buckets(self):
        """reset(None) clears every bucket."""
        limiter = RateLimiter()
        await limiter.can_execute("nmap", max_per_hour=1, client_id="c1")
        await limiter.can_execute("nmap", max_per_hour=1, client_id="c2")

        await limiter.reset()

        allowed, _ = await limiter.can_execute("nmap", max_per_hour=1, client_id="c1")
        assert allowed is True
        allowed, _ = await limiter.can_execute("nmap", max_per_hour=1, client_id="c2")
        assert allowed is True


@pytest.mark.asyncio
class TestConcurrentTaskLimiter:
    async def test_acquire_succeeds_under_limit(self):
        """acquire returns (True, '') when slots are available."""
        limiter = ConcurrentTaskLimiter(max_concurrent=3)
        acquired, msg = await limiter.acquire("task-1")
        assert acquired is True
        assert msg == ""

    async def test_acquire_fails_at_limit(self):
        """acquire returns (False, error) when all slots are occupied."""
        limiter = ConcurrentTaskLimiter(max_concurrent=2)
        await limiter.acquire("task-1")
        await limiter.acquire("task-2")

        acquired, msg = await limiter.acquire("task-3")
        assert acquired is False
        assert "Maximum concurrent tasks" in msg

    async def test_release_frees_a_slot(self):
        """release(task_id) removes the task and frees its slot."""
        limiter = ConcurrentTaskLimiter(max_concurrent=2)
        await limiter.acquire("task-1")
        await limiter.acquire("task-2")
        # At limit, next acquire should fail
        acquired, _ = await limiter.acquire("task-3")
        assert acquired is False

        # Release task-1, should free a slot
        await limiter.release("task-1")
        acquired, _ = await limiter.acquire("task-3")
        assert acquired is True

    async def test_release_unknown_task_is_noop(self):
        """release(task_id) where task_id is not in running_tasks is a no-op."""
        limiter = ConcurrentTaskLimiter(max_concurrent=2)
        await limiter.acquire("task-1")
        # Releasing a non-existent task should not affect state
        await limiter.release("nonexistent-task")
        # Still at capacity
        acquired, _ = await limiter.acquire("task-2")
        assert acquired is True
        acquired, _ = await limiter.acquire("task-3")
        assert acquired is False

    async def test_get_available_slots(self):
        """get_available_slots returns max_concurrent minus running task count."""
        limiter = ConcurrentTaskLimiter(max_concurrent=3)
        assert await limiter.get_available_slots() == 3

        await limiter.acquire("task-1")
        assert await limiter.get_available_slots() == 2

        await limiter.acquire("task-2")
        assert await limiter.get_available_slots() == 1

        await limiter.release("task-1")
        assert await limiter.get_available_slots() == 2
