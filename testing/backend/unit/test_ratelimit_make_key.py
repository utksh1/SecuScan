"""
Unit tests for ScanRateLimiter._make_key in backend/secuscan/rate_limiter.py.

Tests the pure Redis key-building method with no external dependencies.
The test imports from ratelimit_helpers which contains the extracted logic.
"""

from backend.secuscan.ratelimit_helpers import RateLimiterKeyBuilder


class TestMakeKey:
    def test_minute_window_format(self):
        key = RateLimiterKeyBuilder.make_key("192.168.1.1", "minute", 60)
        assert key == "rate_limit:scan:192.168.1.1:minute:60"

    def test_hour_window_format(self):
        key = RateLimiterKeyBuilder.make_key("10.0.0.1", "hour", 3600)
        assert key == "rate_limit:scan:10.0.0.1:hour:3600"

    def test_ipv4_address_in_key(self):
        key = RateLimiterKeyBuilder.make_key("8.8.8.8", "minute", 60)
        assert "8.8.8.8" in key
        assert key.startswith("rate_limit:scan:8.8.8.8")

    def test_ipv6_address_in_key(self):
        key = RateLimiterKeyBuilder.make_key("::1", "minute", 60)
        assert "::1" in key
        assert key.startswith("rate_limit:scan::::1")

    def test_different_window_values_different_keys(self):
        key1 = RateLimiterKeyBuilder.make_key("1.1.1.1", "minute", 30)
        key2 = RateLimiterKeyBuilder.make_key("1.1.1.1", "minute", 60)
        assert key1 != key2

    def test_same_inputs_idempotent(self):
        key1 = RateLimiterKeyBuilder.make_key("5.5.5.5", "hour", 3600)
        key2 = RateLimiterKeyBuilder.make_key("5.5.5.5", "hour", 3600)
        assert key1 == key2

    def test_key_is_always_string(self):
        key = RateLimiterKeyBuilder.make_key("127.0.0.1", "minute", 60)
        assert isinstance(key, str)
