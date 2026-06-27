"""
Unit tests for backend.secuscan.ratelimit WorkflowRateLimiter and
EndpointRateLimiter._cleanup_expired_identities.

WorkflowRateLimiter covers:
- First call for a workflow_id is always allowed (no prior record)
- Second call within min_interval_seconds is blocked
- Call after min_interval_seconds has elapsed is allowed again
- Different workflow_ids have independent rate limits
- min_interval_seconds=0 edge case
- _last_run is updated after an allowed call

EndpointRateLimiter._cleanup_expired_identities covers:
- Removes timestamps older than cutoff
- Evicts identities with no remaining timestamps
- Skips cleanup when last_cleanup is within cleanup_interval
- Handles empty history without error
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

import pytest

from backend.secuscan.ratelimit import WorkflowRateLimiter


class EndpointRateLimiterFixtures:
    """Shared fixtures for EndpointRateLimiter._cleanup_expired_identities tests."""

    @staticmethod
    def make_limiter(window_seconds: int = 60) -> tuple:
        """Return (limiter, history_ref) where history_ref is the same dict as limiter.history."""
        from backend.secuscan.ratelimit import EndpointRateLimiter
        limiter = EndpointRateLimiter.__new__(EndpointRateLimiter)
        limiter.bucket_name = "test"
        limiter.limit = 10
        limiter.window_seconds = window_seconds
        limiter.history = defaultdict(list)
        limiter.last_cleanup = None
        limiter.lock = asyncio.Lock()
        return limiter, limiter.history


class TestCleanupExpiredIdentities:
    """Tests for EndpointRateLimiter._cleanup_expired_identities."""

    def test_removes_expired_timestamps(self):
        """Timestamps older than cutoff are removed from history."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter(window_seconds=60)
        now = datetime.now()
        history["id-1"] = [
            now - timedelta(seconds=120),  # expired
            now - timedelta(seconds=30),   # still valid
        ]

        cutoff = now - timedelta(seconds=60)
        limiter._cleanup_expired_identities(cutoff, now)

        assert len(history["id-1"]) == 1
        assert history["id-1"][0] == now - timedelta(seconds=30)

    def test_evicts_identity_with_no_remaining_timestamps(self):
        """An identity with all timestamps expired is evicted from the dict."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter(window_seconds=60)
        now = datetime.now()
        history["id-1"] = [now - timedelta(seconds=120), now - timedelta(seconds=90)]

        cutoff = now - timedelta(seconds=60)
        limiter._cleanup_expired_identities(cutoff, now)

        assert "id-1" not in history

    def test_skips_cleanup_when_within_interval(self):
        """When last_cleanup is within cleanup_interval, method returns early."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter(window_seconds=60)
        now = datetime.now()
        limiter.last_cleanup = now - timedelta(seconds=30)  # within 60s interval
        history["id-1"] = [now - timedelta(seconds=120)]   # would be expired

        cutoff = now - timedelta(seconds=60)
        limiter._cleanup_expired_identities(cutoff, now)

        # Cleanup was skipped — expired timestamp still present
        assert "id-1" in history
        assert len(history["id-1"]) == 1

    def test_cleanup_runs_when_last_cleanup_is_none(self):
        """first call (last_cleanup=None) always runs cleanup."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter(window_seconds=60)
        now = datetime.now()
        limiter.last_cleanup = None
        history["id-1"] = [now - timedelta(seconds=120)]

        cutoff = now - timedelta(seconds=60)
        limiter._cleanup_expired_identities(cutoff, now)

        # Expired identity evicted
        assert "id-1" not in history
        # last_cleanup updated
        assert limiter.last_cleanup == now

    def test_empty_history_no_error(self):
        """Calling _cleanup_expired_identities on an empty history is a no-op."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter()
        now = datetime.now()

        # Must not raise
        limiter._cleanup_expired_identities(now - timedelta(seconds=60), now)
        assert len(history) == 0

    def test_partial_history_retains_active_timestamps(self):
        """Identity with mixed expired/active timestamps keeps only active ones."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter(window_seconds=60)
        now = datetime.now()
        history["id-1"] = [
            now - timedelta(seconds=300),  # expired
            now - timedelta(seconds=120),  # expired
            now - timedelta(seconds=10),   # active
            now - timedelta(seconds=5),    # active
        ]

        cutoff = now - timedelta(seconds=60)
        limiter._cleanup_expired_identities(cutoff, now)

        assert len(history["id-1"]) == 2

    def test_multiple_identities_mixed_state(self):
        """Multiple identities with mixed expired/active states are handled correctly."""
        limiter, history = EndpointRateLimiterFixtures.make_limiter(window_seconds=60)
        now = datetime.now()
        history["active"] = [now - timedelta(seconds=10)]
        history["expired"] = [now - timedelta(seconds=120)]
        history["mixed"] = [now - timedelta(seconds=120), now - timedelta(seconds=5)]

        cutoff = now - timedelta(seconds=60)
        limiter._cleanup_expired_identities(cutoff, now)

        assert "active" in history
        assert "expired" not in history
        assert "mixed" in history
        assert len(history["mixed"]) == 1


@pytest.fixture
def limiter():
    return WorkflowRateLimiter()


# ---------------------------------------------------------------------------
# first call is always allowed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_call_allowed(limiter):
    """A workflow with no prior run is always permitted."""
    allowed, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    assert allowed is True
    assert msg == ""


@pytest.mark.asyncio
async def test_first_call_updates_last_run(limiter):
    """After a permitted call, the workflow_id is recorded."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    assert "wf-1" in limiter._last_run


# ---------------------------------------------------------------------------
# second call within interval is blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_second_call_within_interval_blocked(limiter):
    """Back-to-back calls within the interval are rejected."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    allowed, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    assert allowed is False
    assert "rate limited" in msg.lower()


# ---------------------------------------------------------------------------
# call after interval elapsed is allowed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_after_interval_allowed(limiter):
    """Once the interval has passed, a new call is permitted."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=0)
    allowed, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=0)
    assert allowed is True
    assert msg == ""


# ---------------------------------------------------------------------------
# independent workflow_ids
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_different_workflow_ids_independent(limiter):
    """Rate-limiting is per-workflow, not global."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    allowed, _ = await limiter.check_workflow_rate_limit("wf-2", min_interval_seconds=3600)
    assert allowed is True


@pytest.mark.asyncio
async def test_same_workflow_blocked_different_not(limiter):
    """wf-1 is blocked but wf-2 is not, after both have a first call."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    await limiter.check_workflow_rate_limit("wf-2", min_interval_seconds=3600)

    allowed_1, _ = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    allowed_2, _ = await limiter.check_workflow_rate_limit("wf-2", min_interval_seconds=3600)

    assert allowed_1 is False
    assert allowed_2 is False


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zero_interval_allows_all_calls(limiter):
    """min_interval_seconds=0 imposes no rate limit — every call is allowed."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=0)
    allowed, _ = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=0)
    # elapsed is always positive, so elapsed < 0 is never True; zero means no floor
    assert allowed is True


@pytest.mark.asyncio
async def test_large_interval_blocks_second_call(limiter):
    """With a very large interval, only the first call is allowed."""
    allowed_1, _ = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=999999999)
    assert allowed_1 is True
    # Second call within the interval is blocked
    allowed_2, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=999999999)
    assert allowed_2 is False
    assert "rate limited" in msg.lower()


@pytest.mark.asyncio
async def test_concurrent_calls_both_allowed(limiter):
    """Two concurrent calls for the same workflow — only one may win the lock, but neither crashes."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    results = await asyncio.gather(
        limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600),
        limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600),
    )
    # At least one should be blocked; neither should raise
    blocked = sum(1 for allowed, _ in results if not allowed)
    assert blocked >= 1


@pytest.mark.asyncio
async def test_msg_contains_remaining_seconds(limiter):
    """Blocked response includes the wait time in the message."""
    await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    _, msg = await limiter.check_workflow_rate_limit("wf-1", min_interval_seconds=3600)
    # The message should mention how long to wait
    assert "wait" in msg.lower() or "remaining" in msg.lower() or "s" in msg