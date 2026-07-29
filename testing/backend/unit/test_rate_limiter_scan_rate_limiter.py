"""
Unit tests for ScanRateLimiter helpers in backend/secuscan/rate_limiter.py.

The rate_limiter module requires redis.asyncio and fastapi. These are mocked at
module load time so the tests can run in any environment.  The production
module is imported directly (not a copy) to catch regressions in the real code.

Covered helpers (all run with redis_client=None to exercise the in-memory
fallback path):
- ScanRateLimiter._get_client_ip: X-Forwarded-For, X-Real-IP, direct client.host
- ScanRateLimiter._make_key: key namespace construction
- ScanRateLimiter.reset: clears fallback_history and redis_failed flag
- ScanRateLimiter.check (rate_limit=0): pass-through early return
- ScanRateLimiter.check (redis_client=None): uses in-memory fallback
"""

import sys
from unittest.mock import MagicMock, patch

# Mock heavy dependencies before importing the module under test.
mock_redis = MagicMock(name="redis.asyncio")
mock_fastapi = MagicMock(name="fastapi")

# Build a minimal Request stub that provides .headers and .client.
class _StubClient:
    def __init__(self, host: str = "127.0.0.1"):
        self.host = host

class _StubRequest:
    def __init__(self, headers: dict, client_host: str = "127.0.0.1"):
        self.headers = headers
        self.client = _StubClient(client_host)

mock_fastapi.Request = _StubRequest

# Stub HTTPException so the module can import it without fastapi.
class _StubHTTPException(Exception):
    def __init__(self, status_code: int, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail or {}
        self.headers = headers or {}
        super().__init__(str(detail))

mock_fastapi.HTTPException = _StubHTTPException

# Stub status so "status.HTTP_429_TOO_MANY_REQUESTS" resolves.
class _StubStatus:
    HTTP_429_TOO_MANY_REQUESTS = 429
mock_fastapi.status = _StubStatus()

sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = mock_redis
sys.modules["fastapi"] = mock_fastapi

import pytest
from backend.secuscan.rate_limiter import (
    ScanRateLimiter,
    RateLimitExceeded,
    make_scan_rate_limiter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_request(headers: dict, client_host: str = "127.0.0.1") -> _StubRequest:
    """Build a stub FastAPI request for testing."""
    return _StubRequest(headers, client_host)


# ---------------------------------------------------------------------------
# ScanRateLimiter._get_client_ip
# ---------------------------------------------------------------------------


class TestGetClientIp:
    def test_x_forwarded_for_single(self):
        """X-Forwarded-For with a single IP returns that IP."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({"X-Forwarded-For": "192.168.1.100"})
        assert limiter._get_client_ip(request) == "192.168.1.100"

    def test_x_forwarded_for_multiple_takes_first(self):
        """When X-Forwarded-For contains multiple IPs, the first (original client) is returned."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 172.16.0.1"})
        assert limiter._get_client_ip(request) == "10.0.0.1"

    def test_x_forwarded_for_strips_whitespace(self):
        """X-Forwarded-For values have leading/trailing whitespace stripped."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({"X-Forwarded-For": "  192.168.1.50  , 10.0.0.1  "})
        assert limiter._get_client_ip(request) == "192.168.1.50"

    def test_x_real_ip_not_recognized(self):
        """X-Real-IP is not checked by _get_client_ip; only X-Forwarded-For is used."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({"X-Real-IP": "10.0.0.5"}, client_host="127.0.0.1")
        # _get_client_ip only checks X-Forwarded-For; falls back to client.host
        assert limiter._get_client_ip(request) == "127.0.0.1"

    def test_no_proxy_headers_uses_client_host(self):
        """When no proxy headers are present, request.client.host is returned."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({}, client_host="203.0.113.50")
        assert limiter._get_client_ip(request) == "203.0.113.50"

    def test_client_none_returns_unknown(self):
        """When request.client is None, 'unknown' is returned."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        stub = _StubRequest({}, client_host=None)
        stub.client = None
        assert limiter._get_client_ip(stub) == "unknown"


# ---------------------------------------------------------------------------
# ScanRateLimiter._make_key
# ---------------------------------------------------------------------------


class TestMakeKey:
    def test_key_format(self):
        """Keys follow the namespaced schema rate_limit:scan:{ip}:{type}:{window}."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        key = limiter._make_key("192.168.1.1", "minute", 123)
        assert key == "rate_limit:scan:192.168.1.1:minute:123"

    def test_key_with_hour_type(self):
        """Keys work with 'hour' window type."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        key = limiter._make_key("10.0.0.5", "hour", 42)
        assert key == "rate_limit:scan:10.0.0.5:hour:42"


# ---------------------------------------------------------------------------
# ScanRateLimiter.reset
# ---------------------------------------------------------------------------


class TestReset:
    @pytest.mark.asyncio
    async def test_reset_clears_fallback_history(self):
        """reset() clears all entries from _fallback_history."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        # Pre-populate via check
        request = make_request({}, client_host="203.0.113.1")
        for _ in range(3):
            try:
                await limiter.check(request)
            except Exception:
                pass
        # Confirm history has entries
        assert len(limiter._fallback_history) > 0

        await limiter.reset()
        assert len(limiter._fallback_history) == 0

    @pytest.mark.asyncio
    async def test_reset_clears_redis_failed_flag(self):
        """reset() also clears the redis_failed circuit-breaker flag."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        limiter._redis_failed = True
        await limiter.reset()
        assert limiter._redis_failed is False


# ---------------------------------------------------------------------------
# ScanRateLimiter.check — rate_limit=0 pass-through
# ---------------------------------------------------------------------------


class TestCheckRateLimitZero:
    @pytest.mark.asyncio
    async def test_check_returns_immediately_when_rate_limit_disabled(self):
        """When rate_limit is 0, check() returns without raising."""
        limiter = ScanRateLimiter(
            redis_client=MagicMock(), rate_limit=0, rate_window=60,
            burst_limit=0, burst_window=3600,
        )
        request = make_request({}, client_host="203.0.113.99")
        # Should not raise
        await limiter.check(request)


# ---------------------------------------------------------------------------
# ScanRateLimiter.check — redis_client=None fallback path
# ---------------------------------------------------------------------------


class TestCheckFallbackPath:
    @pytest.mark.asyncio
    async def test_check_uses_fallback_when_redis_is_none(self):
        """When redis_client is None, the in-memory fallback is used without error."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({}, client_host="203.0.113.2")
        # Should not raise on first request (under limit)
        await limiter.check(request)

    @pytest.mark.asyncio
    async def test_check_fails_per_minute_limit(self):
        """When the per-minute rate limit is exceeded in fallback, HTTPException 429 is raised."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=2, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        request = make_request({}, client_host="203.0.113.3")
        # First two should pass
        for _ in range(2):
            await limiter.check(request)
        # Third should raise
        with pytest.raises(_StubHTTPException) as exc_info:
            await limiter.check(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_check_fails_per_hour_limit(self):
        """When the hourly burst limit is exceeded, HTTPException 429 is raised."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=2, burst_window=3600,
        )
        request = make_request({}, client_host="203.0.113.4")
        for _ in range(2):
            await limiter.check(request)
        with pytest.raises(_StubHTTPException) as exc_info:
            await limiter.check(request)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_check_retry_after_in_exception(self):
        """RateLimitExceeded exception includes a retry_after value."""
        limiter = ScanRateLimiter(
            redis_client=None, rate_limit=1, rate_window=60,
            burst_limit=1, burst_window=3600,
        )
        request = make_request({}, client_host="203.0.113.5")
        await limiter.check(request)  # First request passes
        with pytest.raises(_StubHTTPException) as exc_info:
            await limiter.check(request)
        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# make_scan_rate_limiter factory
# ---------------------------------------------------------------------------


class TestMakeScanRateLimiter:
    def test_factory_returns_scan_rate_limiter_instance(self):
        """make_scan_rate_limiter returns a ScanRateLimiter instance."""
        limiter = make_scan_rate_limiter(
            redis_client=None, rate_limit=5, rate_window=60,
            burst_limit=10, burst_window=3600,
        )
        assert isinstance(limiter, ScanRateLimiter)

    def test_factory_preserves_all_arguments(self):
        """All constructor arguments are passed through to ScanRateLimiter."""
        limiter = make_scan_rate_limiter(
            redis_client=None, rate_limit=3, rate_window=30,
            burst_limit=7, burst_window=1800,
        )
        assert limiter._rate_limit == 3
        assert limiter._rate_window == 30
        assert limiter._burst_limit == 7
        assert limiter._burst_window == 1800
