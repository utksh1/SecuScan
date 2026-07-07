"""
testing/backend/test_rate_limiter_fallback.py

Tests for the in-memory fallback rate limiting in ScanRateLimiter (PR #1617).

Run with: pytest testing/backend/test_rate_limiter_fallback.py -v
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.secuscan.rate_limiter import ScanRateLimiter


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_mock_request(ip: str = "127.0.0.1") -> MagicMock:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = ip
    request.headers = {}
    return request


# ─── Fallback behaviour tests (PR #1617) ──────────────────────────────────────

class TestRedisFailureFallbackEnforcesLimits:
    """When Redis is unavailable the in-memory fallback must still enforce 429s."""

    @pytest.mark.asyncio
    async def test_allows_requests_under_fallback_limit(self):
        """Requests below the per-minute limit must pass."""
        import redis.asyncio as aioredis
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=aioredis.ConnectionError("down"))

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        # First request — must pass (count=1, limit=5)
        await limiter.check(_make_mock_request("1.2.3.4"))
        assert limiter._redis_failed is True

    @pytest.mark.asyncio
    async def test_rejects_request_when_fallback_minute_limit_exceeded(self):
        """When in-memory count exceeds the per-minute window, raise 429."""
        import redis.asyncio as aioredis
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=aioredis.ConnectionError("down"))

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _make_mock_request("1.2.3.4")

        # Send 5 requests (at limit)
        for _ in range(5):
            await limiter.check(req)

        # 6th request should be rejected (over minute limit)
        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(req)
        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["error"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    async def test_fallback_rejects_when_burst_limit_exceeded(self):
        """When in-memory count exceeds the per-hour window, raise burst 429."""
        import redis.asyncio as aioredis
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=aioredis.ConnectionError("down"))

        # Use small burst window so we can hit it quickly
        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=100,   # minute limit high enough not to interfere
            rate_window=60,
            burst_limit=3,    # only 3 per hour
            burst_window=3600,
        )
        req = _make_mock_request("1.2.3.4")

        for _ in range(3):
            await limiter.check(req)

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(req)
        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["error"] == "burst_limit_exceeded"


class TestRedisRecoveryCircuitBreaker:
    """When Redis comes back the circuit breaker must disengage."""

    @pytest.mark.asyncio
    async def test_redis_recovery_resets_failed_flag(self):
        """After a Redis failure, a successful ping must reset _redis_failed."""
        mock_redis = AsyncMock()
        # Fail once, then recover
        mock_redis.pipeline = MagicMock(side_effect=[
            ConnectionError("down"),
        ])
        mock_redis.ping = AsyncMock(return_value=True)

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _make_mock_request("1.2.3.4")

        # First request — Redis fails, fallback engages
        await limiter.check(req)
        assert limiter._redis_failed is True

        # Now mark Redis as working again (simulate what happens after ping succeeds)
        # Replace pipeline so it works next time
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[1, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        # Second request — should try ping, succeed, reset flag, and use Redis
        await limiter.check(req)
        assert limiter._redis_failed is False

    @pytest.mark.asyncio
    async def test_stays_in_fallback_when_redis_still_down(self):
        """When Redis stays down after recovery attempt, must stay in fallback."""
        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=ConnectionError("down"))
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("still down"))

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _make_mock_request("1.2.3.4")

        await limiter.check(req)
        assert limiter._redis_failed is True

        # Second request — ping fails, should stay in fallback
        await limiter.check(req)
        assert limiter._redis_failed is True


class TestFallbackMemoryCleanup:
    """The in-memory fallback must purge stale entries to prevent unbounded growth."""

    @pytest.mark.asyncio
    async def test_cleans_stale_entries_on_check(self):
        """Entries older than the max window must be removed during fallback check."""
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        now = time.time()

        # Manually inject some stale entries (older than 3600s)
        bucket_key = "1.2.3.4:minute:0"
        limiter._fallback_history[bucket_key] = [
            now - 7200,  # 2 hours old → stale
            now - 5400,  # 1.5 hours old → stale
            now - 100,   # within window → fresh
        ]

        # Trigger cleanup via _check_fallback
        with patch.object(limiter, "_get_client_ip", return_value="1.2.3.4"):
            try:
                await limiter._check_fallback(_make_mock_request("1.2.3.4"))
            except HTTPException:
                pass

        remaining = limiter._fallback_history.get(bucket_key, [])
        # Stale entries should be gone; only the fresh one (+ the new request) remain
        assert len(remaining) >= 1
        assert all(ts > now - 3600 for ts in remaining)

    @pytest.mark.asyncio
    async def test_deletes_empty_keys(self):
        """After removing all stale entries, the key itself must be deleted."""
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        now = time.time()

        # Key with only stale entries
        bucket_key = "1.2.3.4:minute:0"
        limiter._fallback_history[bucket_key] = [now - 7200, now - 5400]

        with patch.object(limiter, "_get_client_ip", return_value="1.2.3.4"):
            try:
                await limiter._check_fallback(_make_mock_request("1.2.3.4"))
            except HTTPException:
                pass

        # Empty key should be deleted
        assert bucket_key not in limiter._fallback_history


class TestFallbackSlidingWindow:
    """The sliding window algorithm must work correctly in fallback mode."""

    @pytest.mark.asyncio
    async def test_sliding_window_counts_requests_correctly(self):
        """Requests within the window should be counted correctly."""
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=3,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _make_mock_request("1.2.3.4")

        with patch("backend.secuscan.rate_limiter.time.time", return_value=1000.0):
            await limiter.check(req)  # count=1
            await limiter.check(req)  # count=2
            await limiter.check(req)  # count=3 (at limit)

        # Count must be exactly 3
        now = 1000.0
        minute_window = int(now // 60)
        bucket = f"1.2.3.4:minute:{minute_window}"
        assert len(limiter._fallback_history[bucket]) == 3

    @pytest.mark.asyncio
    async def test_sliding_window_expires_old_entries(self):
        """Requests outside the sliding window should not count toward the limit."""
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=3,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _make_mock_request("1.2.3.4")

        # Request at t=0
        with patch("backend.secuscan.rate_limiter.time.time", return_value=0.0):
            await limiter.check(req)

        # Request at t=120 (2 minutes later — new window)
        with patch("backend.secuscan.rate_limiter.time.time", return_value=120.0):
            await limiter.check(req)

        # Minute buckets: t=0 → window 0, t=120 → window 2 (120//60=2)
        # Old bucket (window 0) should still exist but not affect new window
        minute_window_old = int(0 // 60)
        minute_window_new = int(120 // 60)
        old_bucket = f"1.2.3.4:minute:{minute_window_old}"
        new_bucket = f"1.2.3.4:minute:{minute_window_new}"

        assert len(limiter._fallback_history[old_bucket]) == 1
        assert len(limiter._fallback_history[new_bucket]) == 1

        # Now the old bucket should be cleaned up when we check
        with patch("backend.secuscan.rate_limiter.time.time", return_value=4000.0):
            try:
                await limiter.check(req)
            except HTTPException:
                pass

        # Old bucket should be deleted (stale)
        assert old_bucket not in limiter._fallback_history
