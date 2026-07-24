"""
Unit tests for ScanRateLimiter helper methods in backend/secuscan/rate_limiter.py.

Tests the pure-logic helpers: _get_client_ip, _make_key, _check_fallback, reset.
Redis-backed check() is tested indirectly in integration tests; these tests
focus on the in-memory fallback path and IP extraction logic.
"""

import time
from unittest.mock import MagicMock

import pytest

from backend.secuscan.rate_limiter import ScanRateLimiter


def _mock_request(headers=None, client_host="1.2.3.4"):
    """Build a minimal mock FastAPI Request."""
    request = MagicMock()
    request.headers = headers or {}
    request.client.host = client_host
    return request


class TestGetClientIp:
    """Tests for ScanRateLimiter._get_client_ip()."""

    def test_returns_first_x_forwarded_for(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(
            headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 10.0.0.2"},
            client_host="1.2.3.4",
        )
        assert limiter._get_client_ip(request) == "10.0.0.1"

    def test_x_forwarded_for_strips_whitespace(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(
            headers={"X-Forwarded-For": "  10.0.0.1  , 192.168.1.1"},
            client_host="1.2.3.4",
        )
        assert limiter._get_client_ip(request) == "10.0.0.1"

    def test_falls_back_to_client_host_when_no_forwarded_header(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(headers={}, client_host="5.6.7.8")
        assert limiter._get_client_ip(request) == "5.6.7.8"

    def test_falls_back_to_unknown_when_client_is_none(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert limiter._get_client_ip(request) == "unknown"

    def test_single_ip_x_forwarded_for(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(
            headers={"X-Forwarded-For": "10.0.0.5"},
            client_host="1.2.3.4",
        )
        assert limiter._get_client_ip(request) == "10.0.0.5"


class TestMakeKey:
    """Tests for ScanRateLimiter._make_key()."""

    def test_key_format(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        key = limiter._make_key("1.2.3.4", "minute", 12345)
        assert key == "rate_limit:scan:1.2.3.4:minute:12345"

    def test_key_includes_hour_window(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        key = limiter._make_key("10.0.0.1", "hour", 100)
        assert key == "rate_limit:scan:10.0.0.1:hour:100"


class TestCheckFallback:
    """Tests for ScanRateLimiter._check_fallback() (in-memory rate limiting)."""

    @pytest.mark.asyncio
    async def test_allows_request_when_under_all_limits(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(headers={}, client_host="1.2.3.4")
        # Should not raise
        await limiter._check_fallback(request)

    @pytest.mark.asyncio
    async def test_blocks_per_minute_limit(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=2,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(headers={}, client_host="1.2.3.4")
        # First 2 requests should pass
        await limiter._check_fallback(request)
        await limiter._check_fallback(request)
        # 3rd request should raise 429
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await limiter._check_fallback(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_blocks_per_hour_limit(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=100,
            rate_window=60,
            burst_limit=2,
            burst_window=3600,
        )
        request = _mock_request(headers={}, client_host="1.2.3.4")
        # First 2 requests pass (within burst limit)
        await limiter._check_fallback(request)
        await limiter._check_fallback(request)
        # 3rd request exceeds burst limit -> 429
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await limiter._check_fallback(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_different_ips_are_independent(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=1,
            rate_window=60,
            burst_limit=1,
            burst_window=3600,
        )
        request_a = _mock_request(headers={}, client_host="1.1.1.1")
        request_b = _mock_request(headers={}, client_host="2.2.2.2")
        # Each IP gets its own limit
        await limiter._check_fallback(request_a)
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await limiter._check_fallback(request_a)
        # request_b should still pass
        await limiter._check_fallback(request_b)


class TestReset:
    """Tests for ScanRateLimiter.reset()."""

    @pytest.mark.asyncio
    async def test_reset_clears_fallback_history(self):
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=2,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        request = _mock_request(headers={}, client_host="1.2.3.4")
        # Exhaust the per-minute limit
        await limiter._check_fallback(request)
        await limiter._check_fallback(request)
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await limiter._check_fallback(request)

        # Reset clears history and circuit breaker
        await limiter.reset()

        # After reset, one request should pass (counter starts from 0 again)
        await limiter._check_fallback(request)

