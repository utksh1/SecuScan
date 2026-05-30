import asyncio
from datetime import datetime, timedelta
import pytest
from fastapi import Request, Response, HTTPException
from fastapi.testclient import TestClient

from backend.secuscan.config import settings
from backend.secuscan.ratelimit import (
    EndpointRateLimiter,
    RateLimiter,
    resolve_client_identity,
    reset_all_endpoint_limiters,
    task_start_limiter,
    vault_limiter,
    report_download_limiter,
    read_heavy_limiter
)
from backend.secuscan.main import app


@pytest.mark.asyncio
async def test_sliding_window_limiting_logic():
    """
    Directly test the EndpointRateLimiter sliding window logic.
    """
    limiter = EndpointRateLimiter("test_bucket", limit=2, window_seconds=5)
    await limiter.reset()

    # Create dummy request and response
    class MockRequest:
        def __init__(self, host="127.0.0.1", headers=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = headers or {}
            self.state = type("State", (), {})()

    class MockResponse:
        def __init__(self):
            self.headers = {}

    req = MockRequest()
    res = MockResponse()

    # First request: should pass
    await limiter(req, res)
    assert res.headers["X-RateLimit-Limit"] == "2"
    assert res.headers["X-RateLimit-Remaining"] == "1"
    assert int(res.headers["X-RateLimit-Reset"]) > 0

    # Second request: should pass
    await limiter(req, res)
    assert res.headers["X-RateLimit-Limit"] == "2"
    assert res.headers["X-RateLimit-Remaining"] == "0"

    # Third request: should fail with 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter(req, res)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["X-RateLimit-Limit"] == "2"
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_sliding_window_reset():
    """
    Directly test that old entries fall out of the sliding window.
    """
    limiter = EndpointRateLimiter("test_bucket", limit=2, window_seconds=2)
    await limiter.reset()

    class MockRequest:
        def __init__(self):
            self.client = type("Client", (), {"host": "127.0.0.1"})()
            self.headers = {}
            self.state = type("State", (), {})()

    class MockResponse:
        def __init__(self):
            self.headers = {}

    req = MockRequest()
    res = MockResponse()

    # 1. Fill the bucket
    await limiter(req, res)
    await limiter(req, res)

    # 2. Third request immediately fails
    with pytest.raises(HTTPException):
        await limiter(req, res)

    # 3. Simulate time pass: manually backdate the timestamps
    async with limiter.lock:
        identity = "ip:127.0.0.1"
        limiter.history[identity] = [ts - timedelta(seconds=3) for ts in limiter.history[identity]]

    # 4. Now the request should succeed since window elapsed
    await limiter(req, res)
    assert res.headers["X-RateLimit-Remaining"] == "1"


def test_priority_client_identity_resolution():
    """
    Verify client identity resolves correctly in priority order:
    API Key -> Authenticated User -> Client IP
    """
    class MockRequest:
        def __init__(self, host="127.0.0.1", headers=None, user_id=None, user=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = headers or {}
            self.state = type("State", (), {})()
            if user_id is not None:
                self.state.user_id = user_id
            if user is not None:
                self.state.user = user

    # Scenario A: Just IP
    req_ip = MockRequest(host="192.168.1.50")
    assert resolve_client_identity(req_ip) == "ip:192.168.1.50"

    # Scenario B: User ID header present (takes precedence over IP)
    req_user = MockRequest(host="192.168.1.50", headers={"x-user-id": "usr_999"})
    assert resolve_client_identity(req_user) == "user:usr_999"

    # Scenario C: State user_id present (takes precedence over IP)
    req_state_user = MockRequest(host="192.168.1.50", user_id="usr_888")
    assert resolve_client_identity(req_state_user) == "user:usr_888"

    # Scenario D: API Key header present (takes precedence over User ID and IP)
    req_apikey = MockRequest(
        host="192.168.1.50",
        headers={"x-user-id": "usr_999", "x-api-key": "secret_key_123"}
    )
    assert resolve_client_identity(req_apikey) == "apikey:secret_key_123"

    # Scenario E: Authorization bearer header present (takes precedence over User ID and IP)
    req_auth = MockRequest(
        host="192.168.1.50",
        headers={"x-user-id": "usr_999", "authorization": "Bearer token_xyz"}
    )
    assert resolve_client_identity(req_auth) == "apikey:token_xyz"


def test_proxy_ip_trust_validation(monkeypatch):
    """
    Test X-Forwarded-For handling:
    - Trusted proxy: extract first IP from X-Forwarded-For
    - Untrusted proxy: ignore X-Forwarded-For and fall back to request client host (spoofing prevention)
    """
    monkeypatch.setattr(settings, "trusted_proxies", ["127.0.0.1", "10.0.0.1"])

    class MockRequest:
        def __init__(self, host, xff=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = {}
            if xff:
                self.headers["x-forwarded-for"] = xff

    # A: Client IP is in trusted proxies -> trust XFF
    req_trusted = MockRequest(host="10.0.0.1", xff="203.0.113.5, 10.0.0.1")
    assert resolve_client_identity(req_trusted) == "ip:203.0.113.5"

    # B: Client IP is NOT in trusted proxies -> ignore XFF (spoofing negative test case)
    req_untrusted = MockRequest(host="198.51.100.2", xff="203.0.113.5, 10.0.0.1")
    assert resolve_client_identity(req_untrusted) == "ip:198.51.100.2"


def test_route_level_integration_and_independent_buckets(test_client, monkeypatch):
    """
    Integration test asserting:
    1. Routes return appropriate X-RateLimit headers.
    2. Read-heavy and Vault endpoints maintain completely independent buckets (no bleeding).
    """
    # Override settings for fast testing
    monkeypatch.setattr(settings, "rate_limit_read_heavy_limit", 2)
    monkeypatch.setattr(settings, "rate_limit_read_heavy_window", 10)
    monkeypatch.setattr(settings, "rate_limit_vault_limit", 2)
    monkeypatch.setattr(settings, "rate_limit_vault_window", 10)

    # Re-initialize limiters to pick up modified settings
    read_heavy_limiter.limit = 2
    read_heavy_limiter.window_seconds = 10
    vault_limiter.limit = 2
    vault_limiter.window_seconds = 10

    # Ensure clean limiters
    asyncio.run(reset_all_endpoint_limiters())

    # --- 1. Exercise Read-Heavy Bucket ---
    # Request 1 (Read-heavy route: /findings)
    resp1 = test_client.get("/api/v1/findings")
    assert resp1.status_code == 200
    assert resp1.headers["X-RateLimit-Limit"] == "2"
    assert resp1.headers["X-RateLimit-Remaining"] == "1"

    # Request 2 (Read-heavy route: /reports)
    resp2 = test_client.get("/api/v1/reports")
    assert resp2.status_code == 200
    assert resp2.headers["X-RateLimit-Limit"] == "2"
    assert resp2.headers["X-RateLimit-Remaining"] == "0"

    # Request 3 (Read-heavy route: /tasks) -> Should hit rate limit (429)
    resp3 = test_client.get("/api/v1/tasks")
    assert resp3.status_code == 429
    assert resp3.headers["X-RateLimit-Limit"] == "2"
    assert resp3.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in resp3.headers

    # --- 2. Exercise Vault Bucket (Confirming Independence) ---
    # Even though Read-Heavy is rate-limited, Vault routes (independent bucket) must succeed!
    resp_vault1 = test_client.get("/api/v1/vault")
    assert resp_vault1.status_code == 200
    assert resp_vault1.headers["X-RateLimit-Limit"] == "2"
    assert resp_vault1.headers["X-RateLimit-Remaining"] == "1"


# ── RateLimiter per-client keying tests ───────────────────────────────────────


class TestRateLimiterClientKeying:
    """Tests for the task-execution RateLimiter with per-(client_id, plugin_id) buckets."""

    @pytest.mark.asyncio
    async def test_independent_client_buckets(self):
        """Two different clients sharing the same plugin have independent quotas.

        Exhausting client_A's allowance must not prevent client_B from executing
        the same plugin.
        """
        limiter = RateLimiter()
        plugin_id = "nmap"
        max_per_hour = 2

        # Drain client_A's quota entirely
        for _ in range(max_per_hour):
            allowed, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_A")
            assert allowed

        # client_A is now blocked
        allowed_a, msg_a = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_A")
        assert not allowed_a
        assert "Rate limit exceeded" in msg_a

        # client_B must still be allowed despite client_A being blocked
        allowed_b, msg_b = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_B")
        assert allowed_b, f"client_B was blocked unexpectedly: {msg_b}"

    @pytest.mark.asyncio
    async def test_reset_plugin_clears_all_client_buckets(self):
        """reset(plugin_id) must clear the history for every client that used that plugin."""
        limiter = RateLimiter()
        plugin_id = "nmap"
        max_per_hour = 1

        # Exhaust both clients for the same plugin
        await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_A")
        await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_B")

        # Confirm both are blocked before reset
        allowed_a, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_A")
        allowed_b, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_B")
        assert not allowed_a
        assert not allowed_b

        # Reset quota for the plugin (all clients)
        await limiter.reset(plugin_id)

        # Both clients must be allowed again after reset
        allowed_a_after, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_A")
        allowed_b_after, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour, client_id="client_B")
        assert allowed_a_after, "client_A should be allowed after reset"
        assert allowed_b_after, "client_B should be allowed after reset"

    @pytest.mark.asyncio
    async def test_reset_plugin_does_not_affect_other_plugins(self):
        """reset(plugin_id) must only clear buckets for that specific plugin."""
        limiter = RateLimiter()
        max_per_hour = 1

        # Exhaust quotas for two different plugins under the same client
        await limiter.can_execute("nmap", max_per_hour=max_per_hour, client_id="client_A")
        await limiter.can_execute("gobuster", max_per_hour=max_per_hour, client_id="client_A")

        # Reset only nmap
        await limiter.reset("nmap")

        # nmap bucket cleared: request should be allowed
        allowed_nmap, _ = await limiter.can_execute("nmap", max_per_hour=max_per_hour, client_id="client_A")
        assert allowed_nmap, "nmap bucket should be cleared after reset"

        # gobuster bucket untouched: request should still be blocked
        allowed_gobuster, _ = await limiter.can_execute("gobuster", max_per_hour=max_per_hour, client_id="client_A")
        assert not allowed_gobuster, "gobuster bucket should remain exhausted"

    @pytest.mark.asyncio
    async def test_backward_compatible_global_bucket(self):
        """Callers that omit client_id default to the 'global' bucket.

        This ensures no regression for existing call sites that do not pass a
        client identity.
        """
        limiter = RateLimiter()
        plugin_id = "nikto"
        max_per_hour = 2

        # Call without explicit client_id (uses default "global")
        allowed_1, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour)
        allowed_2, _ = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour)
        allowed_3, msg = await limiter.can_execute(plugin_id, max_per_hour=max_per_hour)

        assert allowed_1
        assert allowed_2
        assert not allowed_3, "Global bucket should be rate-limited after quota is exhausted"
        assert "Rate limit exceeded" in msg

        # Verify the key in task_history is the expected global bucket format
        async with limiter.lock:
            assert f"global:{plugin_id}" in limiter.task_history
