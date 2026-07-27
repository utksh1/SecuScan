"""Tests for rate_limiter.py factory function and exception class."""

import pytest

from backend.secuscan.rate_limiter import (
    RateLimitExceeded,
    ScanRateLimiter,
    make_scan_rate_limiter,
)


class TestRateLimitExceeded:
    """RateLimitExceeded must be a well-formed HTTPException subclass."""

    def test_is_subclass_of_httpexception(self):
        from fastapi import HTTPException
        assert issubclass(RateLimitExceeded, HTTPException)

    def test_can_be_instantiated_with_status_code_and_detail(self):
        exc = RateLimitExceeded(status_code=429, detail="rate limit exceeded")
        assert exc.status_code == 429
        assert exc.detail == "rate limit exceeded"

    def test_can_include_headers(self):
        headers = {"Retry-After": "60"}
        exc = RateLimitExceeded(
            status_code=429,
            detail="slow down",
            headers=headers,
        )
        assert exc.headers == headers

    def test_detail_defaults_to_httpexception_default(self):
        """HTTPException defaults detail to its class-level default, not None."""
        exc = RateLimitExceeded(status_code=429)
        # FastAPI/Starlette HTTPException defaults detail to the status text
        assert isinstance(exc.detail, str)
        assert len(exc.detail) > 0


class TestMakeScanRateLimiter:
    """make_scan_rate_limiter must produce a correctly-configured ScanRateLimiter."""

    def test_returns_scan_rate_limiter_instance(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert isinstance(limiter, ScanRateLimiter)

    def test_redis_client_none_sets_internal_redis_to_none(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._redis is None

    def test_rate_limit_matches_input(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._rate_limit == 5

    def test_rate_window_matches_input(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._rate_window == 60

    def test_burst_limit_matches_input(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._burst_limit == 10

    def test_burst_window_matches_input(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._burst_window == 3600

    def test_redis_failed_is_false_initially(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._redis_failed is False

    def test_fallback_history_is_empty_initially(self):
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=5,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        assert limiter._fallback_history == {}

    def test_zero_rate_limit_is_accepted(self):
        """Rate limit of 0 should be accepted (disables rate limiting)."""
        limiter = make_scan_rate_limiter(
            redis_client=None,
            rate_limit=0,
            rate_window=60,
            burst_limit=0,
            burst_window=3600,
        )
        assert limiter._rate_limit == 0
        assert limiter._burst_limit == 0
