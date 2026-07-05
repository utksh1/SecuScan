"""
Unit tests for RateLimiterKeyBuilder.make_key in
backend.secuscan.ratelimit_helpers.

Tests the key-formatting logic for ScanRateLimiter Redis buckets.
"""

import pytest
from backend.secuscan.ratelimit_helpers import RateLimiterKeyBuilder


class TestRateLimiterKeyBuilderMakeKey:
    def test_standard_ipv4_minute_window(self):
        key = RateLimiterKeyBuilder.make_key("192.168.1.100", "minute", 1700000000)
        assert key == "rate_limit:scan:192.168.1.100:minute:1700000000"

    def test_standard_ipv4_hour_window(self):
        key = RateLimiterKeyBuilder.make_key("10.0.0.5", "hour", 1700000000)
        assert key == "rate_limit:scan:10.0.0.5:hour:1700000000"

    def test_localhost_minute_window(self):
        key = RateLimiterKeyBuilder.make_key("127.0.0.1", "minute", 1700003600)
        assert key == "rate_limit:scan:127.0.0.1:minute:1700003600"

    def test_ipv6_address(self):
        key = RateLimiterKeyBuilder.make_key("::1", "minute", 1700000000)
        assert key == "rate_limit:scan:::1:minute:1700000000"

    def test_window_value_zero(self):
        key = RateLimiterKeyBuilder.make_key("1.2.3.4", "minute", 0)
        assert key == "rate_limit:scan:1.2.3.4:minute:0"

    def test_window_value_large(self):
        key = RateLimiterKeyBuilder.make_key("8.8.8.8", "hour", 9999999999)
        assert key == "rate_limit:scan:8.8.8.8:hour:9999999999"

    def test_key_format_exactly_four_components(self):
        key = RateLimiterKeyBuilder.make_key("5.5.5.5", "minute", 123)
        parts = key.split(":")
        assert parts == ["rate_limit", "scan", "5.5.5.5", "minute", "123"]

    def test_empty_ip_produces_valid_key(self):
        key = RateLimiterKeyBuilder.make_key("", "minute", 100)
        assert key == "rate_limit:scan::minute:100"

    def test_unknown_window_type_produces_valid_key(self):
        key = RateLimiterKeyBuilder.make_key("1.1.1.1", "second", 60)
        assert key == "rate_limit:scan:1.1.1.1:second:60"
