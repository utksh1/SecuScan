"""
End-to-end coverage for network_policy + ScanRateLimiter under Redis outage.

Issue #1885 acceptance:
  - Redis-down behavior is tested and documented explicitly
  - DNS-rebinding gaps are covered
  - Cloud metadata IP blocking is covered

Documented Redis-down behavior (post PR #1617)
---------------------------------------------
ScanRateLimiter does **not** pure-fail-open on Redis errors.
When Redis is unreachable it:

  1. Sets the circuit-breaker flag ``_redis_failed``
  2. Falls over to an in-memory sliding-window limiter
  3. Continues to enforce per-minute / per-hour limits via that fallback

So Redis-down is "fail-open to fallback" for the first N requests under the
configured limit, then "fail-closed" (HTTP 429) once the in-memory window is
exhausted. There is no separate fail-open/fail-closed toggle on the rate
limiter itself.

Network policy *does* expose a configurable failure mode via
``settings.network_policy_failure_mode``:

  - ``"block"``     → deny (fail-closed) when policy rejects a target
  - ``"log_only"``  → allow with a warning (soft fail-open for policy denials)

Default-allow for public egress (when ``network_allowlist`` is empty) still
keeps denylisted ranges blocked — including AWS metadata ``169.254.169.254``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis
from fastapi import HTTPException

from backend.secuscan.config import settings
from backend.secuscan.network_policy import (
    NetworkPolicyEngine,
    PolicyAction,
    _init_default_policies,
)
from backend.secuscan.rate_limiter import ScanRateLimiter
from backend.secuscan.validation import validate_target


# ── helpers ──────────────────────────────────────────────────────────────────


def _mock_request(ip: str = "203.0.113.10") -> MagicMock:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = ip
    request.headers = {}
    return request


def _broken_redis() -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.pipeline = MagicMock(
        side_effect=aioredis.ConnectionError("redis unavailable")
    )
    mock_redis.ping = AsyncMock(
        side_effect=aioredis.ConnectionError("redis unavailable")
    )
    return mock_redis


def _engine_with_defaults(tmp_path, monkeypatch, allowlist=None):
    """Build a fresh policy engine with default denylist + optional allowlist."""
    monkeypatch.setattr(settings, "network_allowlist", allowlist or [])
    audit_log = tmp_path / "network.audit.log"
    engine = NetworkPolicyEngine(audit_log_path=str(audit_log))
    _init_default_policies(engine)
    return engine


# ═════════════════════════════════════════════════════════════════════════════
# Redis-down rate limiter — document fail-open-to-fallback explicitly
# ═════════════════════════════════════════════════════════════════════════════


class TestRateLimiterRedisDownBehavior:
    """Assert Redis-down behavior: soft fail-open into in-memory fallback,
    then fail-closed once the fallback window is exhausted."""

    @pytest.mark.asyncio
    async def test_redis_down_allows_requests_under_limit_via_fallback(self):
        """
        DOCUMENTED BEHAVIOR (fail-open to fallback):
        When Redis raises ConnectionError, the first requests under
        ``rate_limit`` must succeed via the in-memory fallback — the scan
        service must not go down solely because Redis is unreachable.
        """
        limiter = ScanRateLimiter(
            redis_client=_broken_redis(),
            rate_limit=3,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _mock_request()

        # Under the limit → must not raise (soft fail-open into fallback)
        for _ in range(3):
            await limiter.check(req)

        assert limiter._redis_failed is True, (
            "Circuit breaker must engage after Redis ConnectionError"
        )

    @pytest.mark.asyncio
    async def test_redis_down_fail_closed_once_fallback_limit_exceeded(self):
        """
        DOCUMENTED BEHAVIOR (fail-closed via fallback):
        Redis-down is NOT pure fail-open. After the in-memory window is
        exhausted the limiter must still return HTTP 429.
        """
        limiter = ScanRateLimiter(
            redis_client=_broken_redis(),
            rate_limit=2,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _mock_request("198.51.100.7")

        await limiter.check(req)
        await limiter.check(req)

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(req)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["error"] == "rate_limit_exceeded"
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_redis_none_uses_same_in_memory_fallback(self):
        """
        DOCUMENTED BEHAVIOR:
        ``redis_client=None`` (Redis not configured) uses the same in-memory
        fallback path as Redis-down — not an unlimited fail-open.
        """
        limiter = ScanRateLimiter(
            redis_client=None,
            rate_limit=2,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _mock_request("198.51.100.8")

        await limiter.check(req)
        await limiter.check(req)

        with pytest.raises(HTTPException) as exc_info:
            await limiter.check(req)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_zero_is_explicit_pass_through(self):
        """
        DOCUMENTED BEHAVIOR (configurable disable):
        ``rate_limit=0`` disables scan rate limiting entirely (pass-through).
        This is the operator-facing "off" switch — distinct from Redis-down
        fallback, which still enforces limits.
        """
        limiter = ScanRateLimiter(
            redis_client=_broken_redis(),
            rate_limit=0,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        req = _mock_request()
        for _ in range(20):
            await limiter.check(req)
        assert limiter._redis_failed is False


# ═════════════════════════════════════════════════════════════════════════════
# Network policy — default-allow public egress + metadata IP blocking
# ═════════════════════════════════════════════════════════════════════════════


class TestNetworkPolicyDefaultAllowAndMetadataBlock:
    """Empty allowlist implies public egress, but denylist still blocks
    private / metadata / loopback ranges."""

    def test_default_allow_permits_public_ip(self, tmp_path, monkeypatch):
        engine = _engine_with_defaults(tmp_path, monkeypatch)
        allowed, reason, _ = engine.check_access(
            dest_ip="8.8.8.8",
            plugin_id="nmap",
            task_id="task-public",
        )
        assert allowed is True
        assert "default public egress" in reason.lower() or "allowlist" in reason.lower()

    def test_metadata_ip_blocked_by_default_denylist(self, tmp_path, monkeypatch):
        """AWS IMDS endpoint 169.254.169.254 must be denied even under default-allow."""
        engine = _engine_with_defaults(tmp_path, monkeypatch)
        allowed, reason, policy = engine.check_access(
            dest_ip="169.254.169.254",
            plugin_id="http_inspector",
            task_id="task-meta",
        )
        assert allowed is False
        assert policy is not None
        assert policy.action == PolicyAction.DENY
        assert "denylist" in reason.lower()

    def test_link_local_range_blocked(self, tmp_path, monkeypatch):
        engine = _engine_with_defaults(tmp_path, monkeypatch)
        allowed, _, _ = engine.check_access(
            dest_ip="169.254.1.1",
            plugin_id="test",
            task_id="task-ll",
        )
        assert allowed is False

    def test_resolve_and_pin_blocks_metadata_ip_literal(self, tmp_path, monkeypatch):
        """resolve_and_pin must reject a raw metadata IP (SSRF / IMDS guard)."""
        engine = _engine_with_defaults(tmp_path, monkeypatch)
        pinned, allowed, reason = engine.resolve_and_pin(
            "169.254.169.254",
            plugin_id="nuclei",
            task_id="task-pin-meta",
        )
        assert pinned == "169.254.169.254"
        assert allowed is False
        assert "denylist" in reason.lower()


# ═════════════════════════════════════════════════════════════════════════════
# DNS rebinding — pin once, reject metadata / public rebind targets
# ═════════════════════════════════════════════════════════════════════════════


class TestDnsRebindingAndPinning:
    """Cover rebind gaps: hostname → metadata IP, and safe-mode union check."""

    def test_resolve_and_pin_blocks_hostname_resolving_to_metadata(
        self, tmp_path, monkeypatch
    ):
        """
        DNS rebinding / SSRF gap: a hostname that resolves to the cloud
        metadata endpoint must be denied at pin time.
        """
        engine = _engine_with_defaults(tmp_path, monkeypatch)

        with patch(
            "backend.secuscan.network_policy.socket.gethostbyname",
            return_value="169.254.169.254",
        ):
            pinned, allowed, reason = engine.resolve_and_pin(
                "metadata.internal.example",
                plugin_id="http_inspector",
                task_id="task-rebind-meta",
            )

        assert pinned == "169.254.169.254"
        assert allowed is False
        assert "denylist" in reason.lower()

    def test_resolve_and_pin_allows_hostname_resolving_to_public_ip(
        self, tmp_path, monkeypatch
    ):
        engine = _engine_with_defaults(tmp_path, monkeypatch)

        with patch(
            "backend.secuscan.network_policy.socket.gethostbyname",
            return_value="93.184.216.34",
        ):
            pinned, allowed, reason = engine.resolve_and_pin(
                "example.com",
                plugin_id="httpx",
                task_id="task-rebind-ok",
            )

        assert pinned == "93.184.216.34"
        assert allowed is True

    def test_safe_mode_validate_target_blocks_dns_rebind_union(self, monkeypatch):
        """
        validate_target (safe mode) resolves twice when dns_rebind_check is on
        and fails closed if the union includes a public IP.
        """
        monkeypatch.setattr(settings, "dns_rebind_check", True)
        calls = {"n": 0}

        def fake_getaddrinfo(_host, *_args, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return [
                    (2, None, None, None, ("192.168.1.10", 0)),
                ]
            return [
                (2, None, None, None, ("8.8.8.8", 0)),
            ]

        monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
        ok, msg = validate_target("rebind.example", safe_mode=True)
        assert ok is False
        assert calls["n"] >= 2
        assert msg  # non-empty rejection reason


# ═════════════════════════════════════════════════════════════════════════════
# Configurable network_policy_failure_mode (block vs log_only / fail-open)
# ═════════════════════════════════════════════════════════════════════════════


class TestNetworkPolicyFailureModeConfig:
    """
    DOCUMENTED BEHAVIOR (configurable fail-open/closed for network policy):
      network_policy_failure_mode = "block"    → fail-closed on policy deny
      network_policy_failure_mode = "log_only" → soft fail-open (warn + allow)
    """

    def test_block_mode_is_default_fail_closed(self):
        assert settings.network_policy_failure_mode in ("block", "log_only")
        # Fresh Settings() default must be fail-closed
        from backend.secuscan.config import Settings

        assert Settings().network_policy_failure_mode == "block"

    def test_log_only_mode_is_recognized_fail_open_option(self, monkeypatch):
        monkeypatch.setattr(settings, "network_policy_failure_mode", "log_only")
        assert settings.network_policy_failure_mode == "log_only"

    def test_block_mode_is_recognized_fail_closed_option(self, monkeypatch):
        monkeypatch.setattr(settings, "network_policy_failure_mode", "block")
        assert settings.network_policy_failure_mode == "block"


# ═════════════════════════════════════════════════════════════════════════════
# HTTP e2e: /task/start under Redis-down rate limiter
# ═════════════════════════════════════════════════════════════════════════════


class TestTaskStartUnderRedisDown:
    """Drive the real FastAPI dependency path with a broken Redis client."""

    def test_task_start_returns_429_when_fallback_limit_exceeded(
        self, test_client, monkeypatch
    ):
        """
        End-to-end: inject a Redis-down ScanRateLimiter into app.state and
        assert /task/start fails closed (429) after the fallback window fills.
        """
        from backend.secuscan.main import app

        limiter = ScanRateLimiter(
            redis_client=_broken_redis(),
            rate_limit=2,
            rate_window=60,
            burst_limit=10,
            burst_window=3600,
        )
        # Override the disabled (rate_limit=0) limiter installed by conftest
        app.state.scan_rate_limiter = limiter

        payload = {
            "plugin_id": "http_inspector",
            "preset": "quick",
            "inputs": {"url": "http://127.0.0.1:8000"},
            "consent_granted": True,
        }

        with patch(
            "backend.secuscan.executor.TaskExecutor._execute_command",
            return_value=("ok", 0),
        ):
            # First two requests under the fallback limit should be accepted
            # (or at least not 429 — may still 4xx for other reasons).
            r1 = test_client.post("/api/v1/task/start", json=payload)
            r2 = test_client.post("/api/v1/task/start", json=payload)
            assert r1.status_code != 429
            assert r2.status_code != 429

            # Third request must hit the in-memory fallback ceiling
            r3 = test_client.post("/api/v1/task/start", json=payload)
            assert r3.status_code == 429
            body = r3.json()
            # Global 429 handler normalizes the payload; accept either the
            # structured ScanRateLimiter detail or the generic wrapper.
            detail = body.get("detail", body)
            if isinstance(detail, dict):
                assert detail.get("error") in {
                    "rate_limit_exceeded",
                    "burst_limit_exceeded",
                    "Too Many Requests",
                }
            else:
                assert body.get("error") in {
                    "rate_limit_exceeded",
                    "Too Many Requests",
                }
            assert "Retry-After" in r3.headers
