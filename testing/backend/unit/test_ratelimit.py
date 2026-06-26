"""
Unit tests for RateLimiter and WorkflowRateLimiter helpers in
backend.secuscan.ratelimit.

Covers (separately from test_endpoint_rate_limiter.py which covers
EndpointRateLimiter and resolve_client_identity):
- RateLimiter.can_execute: quota enforcement, cleanup, independent buckets
- RateLimiter.reset: per-plugin and global reset
- WorkflowRateLimiter.check_workflow_rate_limit: interval enforcement
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from backend.secuscan.ratelimit import RateLimiter, WorkflowRateLimiter


# ---------------------------------------------------------------------------
# RateLimiter.can_execute
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_can_execute_allows_under_quota():
    """When below max_per_hour, can_execute returns (True, '')."""
    limiter = RateLimiter()
    allowed, msg = await limiter.can_execute("plugin1", max_per_hour=10, client_id="alice")
    assert allowed is True
    assert msg == ""


@pytest.mark.asyncio
async def test_can_execute_denies_at_quota():
    """When at max_per_hour, can_execute returns (False, error_message)."""
    limiter = RateLimiter()
    for _ in range(5):
        await limiter.can_execute("plugin1", max_per_hour=5, client_id="alice")

    allowed, msg = await limiter.can_execute("plugin1", max_per_hour=5, client_id="alice")
    assert allowed is False
    assert "Rate limit exceeded" in msg
    assert "5/5" in msg


@pytest.mark.asyncio
async def test_can_execute_cleans_old_entries():
    """Entries older than 1 hour are removed so they no longer count toward quota."""
    limiter = RateLimiter()

    # Manually inject an old entry
    bucket = "alice:plugin1"
    old_time = datetime.now() - timedelta(hours=2)
    limiter.task_history[bucket].append(old_time)

    # Should allow since the old entry was cleaned up
    allowed, msg = await limiter.can_execute("plugin1", max_per_hour=5, client_id="alice")
    assert allowed is True
    assert len(limiter.task_history[bucket]) == 1  # old entry removed, new one added


@pytest.mark.asyncio
async def test_can_execute_independent_per_client():
    """Each client_id has an independent quota."""
    limiter = RateLimiter()

    for _ in range(3):
        await limiter.can_execute("plugin1", max_per_hour=3, client_id="alice")

    # Alice is at quota
    allowed_alice, _ = await limiter.can_execute("plugin1", max_per_hour=3, client_id="alice")
    assert allowed_alice is False

    # Bob has separate quota
    allowed_bob, _ = await limiter.can_execute("plugin1", max_per_hour=3, client_id="bob")
    assert allowed_bob is True


@pytest.mark.asyncio
async def test_can_execute_independent_per_plugin():
    """Each plugin_id has an independent quota within the same client."""
    limiter = RateLimiter()

    for _ in range(3):
        await limiter.can_execute("nmap", max_per_hour=3, client_id="alice")

    # nmap is at quota
    allowed_nmap, _ = await limiter.can_execute("nmap", max_per_hour=3, client_id="alice")
    assert allowed_nmap is False

    # http_inspector is independent
    allowed_http, _ = await limiter.can_execute("http_inspector", max_per_hour=3, client_id="alice")
    assert allowed_http is True


@pytest.mark.asyncio
async def test_can_execute_default_client_id_is_global():
    """When client_id is not supplied, defaults to 'global' bucket."""
    limiter = RateLimiter()

    for _ in range(3):
        await limiter.can_execute("nmap", max_per_hour=3)

    allowed, msg = await limiter.can_execute("nmap", max_per_hour=3)
    assert allowed is False
    # The bucket should be "global:nmap"
    assert "global:nmap" in limiter.task_history


# ---------------------------------------------------------------------------
# RateLimiter.reset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_clears_matching_plugin():
    """reset(plugin_id) clears all buckets for that plugin across all clients."""
    limiter = RateLimiter()

    await limiter.can_execute("nmap", max_per_hour=10, client_id="alice")
    await limiter.can_execute("nmap", max_per_hour=10, client_id="bob")
    await limiter.can_execute("http_inspector", max_per_hour=10, client_id="alice")

    assert len(limiter.task_history) > 0

    await limiter.reset("nmap")

    # nmap buckets should be cleared
    assert len(limiter.task_history["alice:nmap"]) == 0
    assert len(limiter.task_history["bob:nmap"]) == 0
    # http_inspector bucket should be untouched
    assert len(limiter.task_history["alice:http_inspector"]) > 0


@pytest.mark.asyncio
async def test_reset_clears_all_buckets():
    """reset() with no argument clears every bucket."""
    limiter = RateLimiter()

    await limiter.can_execute("nmap", max_per_hour=10, client_id="alice")
    await limiter.can_execute("nmap", max_per_hour=10, client_id="bob")

    assert len(limiter.task_history) > 0

    await limiter.reset()

    assert len(limiter.task_history) == 0


# ---------------------------------------------------------------------------
# WorkflowRateLimiter.check_workflow_rate_limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_rate_limiter_allows_first_run():
    """A workflow with no prior run should always be allowed."""
    limiter = WorkflowRateLimiter()
    allowed, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=300)
    assert allowed is True
    assert msg == ""


@pytest.mark.asyncio
async def test_workflow_rate_limiter_denies_within_interval():
    """A workflow run within the interval should be denied with a remaining-seconds message."""
    limiter = WorkflowRateLimiter()

    # First run
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=300)

    # Second run immediately after
    allowed, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=300)
    assert allowed is False
    assert "Workflow rate limited" in msg
    # remaining should be close to 300
    assert "300" in msg or "299" in msg


@pytest.mark.asyncio
async def test_workflow_rate_limiter_allows_after_interval():
    """A workflow run after the interval has passed should be allowed."""
    limiter = WorkflowRateLimiter()

    # Manually inject a past run
    limiter._last_run["wf-1"] = datetime.now() - timedelta(seconds=301)

    allowed, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=300)
    assert allowed is True
    assert msg == ""


@pytest.mark.asyncio
async def test_workflow_rate_limiter_each_workflow_independent():
    """Workflow rate limits are independent per workflow_id."""
    limiter = WorkflowRateLimiter()

    # Run wf-1
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=300)
    # wf-2 has never run
    allowed, msg = await limiter.check_workflow_rate_limit("wf-2", min_interval_seconds=300)
    assert allowed is True
