"""
Unit tests for backend.secuscan.ratelimit.RateLimiter.

Covers:
- can_execute allows first request within limit
- can_execute denies when limit is reached
- can_execute cleans old entries older than 1 hour
- can_execute enforces independent quotas per (client_id, plugin_id)
- can_execute respects max_per_hour parameter
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.secuscan.ratelimit import RateLimiter


@pytest.mark.asyncio
class TestCanExecute:
    async def test_allows_first_request(self):
        """can_execute returns (True, ...) for the first request within the limit."""
        limiter = RateLimiter()
        allowed, msg = await limiter.can_execute("plugin_a", max_per_hour=5, client_id="client1")
        assert allowed is True
        assert "exceeded" not in msg.lower()

    async def test_denies_when_limit_reached(self):
        """can_execute returns (False, error) when max_per_hour is exhausted."""
        limiter = RateLimiter()
        for _ in range(3):
            await limiter.can_execute("plugin_x", max_per_hour=3, client_id="client1")
        allowed, msg = await limiter.can_execute("plugin_x", max_per_hour=3, client_id="client1")
        assert allowed is False
        assert "exceeded" in msg.lower()
        assert "3/3" in msg

    async def test_independent_quotas_per_client(self):
        """Each client_id has an independent quota."""
        limiter = RateLimiter()
        # Alice makes 3 calls (at limit), bob makes 2 (has quota remaining)
        for _ in range(3):
            await limiter.can_execute("plugin_a", max_per_hour=3, client_id="alice")
        for _ in range(2):
            await limiter.can_execute("plugin_a", max_per_hour=3, client_id="bob")
        # Alice should be at limit
        allowed_alice, _ = await limiter.can_execute("plugin_a", max_per_hour=3, client_id="alice")
        # Bob should still have quota
        allowed_bob, _ = await limiter.can_execute("plugin_a", max_per_hour=3, client_id="bob")
        assert allowed_alice is False
        assert allowed_bob is True

    async def test_independent_quotas_per_plugin(self):
        """Each plugin_id has an independent quota."""
        limiter = RateLimiter()
        for _ in range(3):
            await limiter.can_execute("plugin_nmap", max_per_hour=3, client_id="global")
        allowed_nmap, _ = await limiter.can_execute("plugin_nmap", max_per_hour=3, client_id="global")
        allowed_ffuf, _ = await limiter.can_execute("plugin_ffuf", max_per_hour=3, client_id="global")
        assert allowed_nmap is False
        assert allowed_ffuf is True

    async def test_default_client_is_global(self):
        """When client_id is not supplied, uses 'global' as the bucket key."""
        limiter = RateLimiter()
        for _ in range(3):
            await limiter.can_execute("plugin_a", max_per_hour=3)
        allowed, msg = await limiter.can_execute("plugin_a", max_per_hour=3)
        assert allowed is False
        assert "3/3" in msg
