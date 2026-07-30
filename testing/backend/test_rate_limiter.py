"""
testing/backend/test_rate_limiter.py

Tests for backend/secuscan/rate_limiter.py

Run with: ./testing/test_python.sh
or:        pytest testing/backend/test_rate_limiter.py -v
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.secuscan.rate_limiter import ScanRateLimiter, make_scan_rate_limiter


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_mock_request(ip: str = "127.0.0.1") -> MagicMock:
    """Build a minimal mock FastAPI Request with a controllable client IP."""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = ip
    request.headers = {}  # No X-Forwarded-For by default
    return request


def _make_mock_request_forwarded(ip: str) -> MagicMock:
    """Build a mock request with X-Forwarded-For header."""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "10.0.0.1"  # internal proxy IP
    request.headers = {"X-Forwarded-For": ip}
    return request


async def _make_redis_pipe_side_effect(count: int):
    """Helper: returns a pipeline mock that produces the given count on execute()."""
    pipe = AsyncMock()
    pipe.incr = AsyncMock()
    pipe.expire = AsyncMock()
    pipe.execute = AsyncMock(return_value=[count, True])
    return pipe


# ─── Unit Tests: ScanRateLimiter ──────────────────────────────────────────────

class TestScanRateLimiterDisabled:
    """Rate limiting should be a no-op when rate_limit=0."""

    @pytest.mark.asyncio
    async def test_disabled_when_limit_zero(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=0,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()
        # Must not raise anything
        await limiter.check(request)

    @pytest.mark.asyncio
    async def test_disabled_does_not_touch_redis(self):
        mock_redis = AsyncMock()
        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=0,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()
        await limiter.check(request)
        # Redis pipeline should never be called
        mock_redis.pipeline.assert_not_called()


class TestScanRateLimiterNoRedis:
    """Should fail open when Redis is None."""

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_none(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()
        # Must not raise — fail open
        await limiter.check(request)


class TestScanRateLimiterMinuteWindow:
    """Per-minute rate limit enforcement."""

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self):
        mock_redis = AsyncMock()
        # Simulate count=3, limit=5 → allowed
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[3, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()
        # Must not raise
        await limiter.check(request)

    @pytest.mark.asyncio
    async def test_rejects_request_over_minute_limit(self):
        mock_redis = AsyncMock()
        # Simulate count=6, limit=5 → rejected
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[6, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(request)

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers
        assert exc_info.value.detail["error"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    async def test_rejects_request_over_burst_limit(self):
        mock_redis = AsyncMock()
        call_count = 0

        def make_pipe():
            nonlocal call_count
            pipe = AsyncMock()
            if call_count == 0:
                # First pipeline call: minute window, count=3 (under minute limit)
                pipe.execute = AsyncMock(return_value=[3, True])
            else:
                # Second pipeline call: hour window, count=11 (over burst limit)
                pipe.execute = AsyncMock(return_value=[11, True])
            call_count += 1
            return pipe

        mock_redis.pipeline = MagicMock(side_effect=make_pipe)

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["error"] == "burst_limit_exceeded"


class TestScanRateLimiterIPExtraction:
    """IP extraction from headers."""

    @pytest.mark.asyncio
    async def test_uses_direct_ip_when_no_forwarded_header(self):
        mock_redis = AsyncMock()
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[1, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request(ip="192.168.1.1")
        await limiter.check(request)

        # Redis key should contain the direct IP
        calls = str(mock_redis.pipeline.call_args_list)
        incr_calls = str(pipe.incr.call_args_list)
        assert "192.168.1.1" in incr_calls

    @pytest.mark.asyncio
    async def test_uses_first_ip_from_forwarded_for_header(self):
        mock_redis = AsyncMock()
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[1, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        # Simulate multi-hop X-Forwarded-For
        request = _make_mock_request_forwarded("203.0.113.5, 10.0.0.1, 172.16.0.1")
        await limiter.check(request)

        incr_calls = str(pipe.incr.call_args_list)
        assert "203.0.113.5" in incr_calls


class TestScanRateLimiterRedisError:
    """Should fail open on Redis errors."""

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_connection_error(self):
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
        request = _make_mock_request()
        # Must not raise — fail open
        await limiter.check(request)

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_timeout(self):
        import redis.asyncio as aioredis

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=aioredis.TimeoutError("timeout"))

        limiter = ScanRateLimiter(
            redis_client=mock_redis,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _make_mock_request()
        await limiter.check(request)


class TestMakeScanRateLimiter:
    """Factory function tests."""

    def test_factory_creates_limiter_with_correct_settings(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert isinstance(limiter, ScanRateLimiter)
        assert limiter._rate_limit == 5
        assert limiter._rate_window == 60
        assert limiter._burst_limit == 10
        assert limiter._burst_window == 3600

    def test_factory_accepts_none_redis(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._redis is None