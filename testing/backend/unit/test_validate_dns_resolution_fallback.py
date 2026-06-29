"""
Unit tests for DNS resolution exception handling in validation.py.

Covers:
  - _resolve_host_ips: OSError (socket.gaierror) returns [] gracefully
  - _resolve_host_ips_uncached: same graceful handling
  - validate_target: hostname resolution failures are handled safely in safe_mode

These are not happy-path tests (those are in test_validation.py); these
verify that the module degrades gracefully when DNS is unavailable or
returns errors, without crashing the parent process.
"""

from __future__ import annotations

import socket
import pytest


class TestResolveHostIpsOSError:
    """Coverage for _resolve_host_ips OSError path."""

    def test_getaddrinfo_raises_oserror_returns_empty_list(self, monkeypatch):
        """socket.getaddrinfo raising OSError must return [] so callers do not crash."""
        import sys
        from backend.secuscan import validation

        # Discard any cached entry first
        validation._DNS_CACHE.pop("unresolvable.invalid", None)

        def fake_getaddrinfo(*args, **kwargs):
            raise OSError("Name or service not known")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        # The function must not raise; it must return an empty list.
        result = validation._resolve_host_ips("unresolvable.invalid")
        assert result == []

    def test_getaddrinfo_raises_gaierror_returns_empty_list(self, monkeypatch):
        """socket.herror (subclass of OSError) is also handled gracefully."""
        import sys
        from backend.secuscan import validation

        validation._DNS_CACHE.pop("nodns.example", None)

        def fake_getaddrinfo(*args, **kwargs):
            raise socket.gaierror("No address associated with hostname")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        result = validation._resolve_host_ips("nodns.example")
        assert result == []

    def test_cached_entry_served_despite_concurrent_getaddrinfo_failure(self, monkeypatch):
        """A pre-populated cache entry must be returned even if a fresh call fails."""
        from backend.secuscan import validation
        import time

        # Pre-populate the cache with a real-looking entry.
        validation._DNS_CACHE["already-cached.example"] = (
            time.time() + 300,
            [],
        )

        def fake_getaddrinfo(*args, **kwargs):
            raise OSError("should not reach here")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        result = validation._resolve_host_ips("already-cached.example")
        # Must return the cached empty list, not raise.
        assert result == []


class TestResolveHostIpsUncached:
    """Coverage for _resolve_host_ips_uncached exception path."""

    def test_uncached_failure_returns_empty_and_does_not_raise(self, monkeypatch):
        """_resolve_host_ips_uncached propagates _resolve_host_ips behavior."""
        from backend.secuscan import validation

        validation._DNS_CACHE.pop("fresh.fail.example", None)

        def fake_getaddrinfo(*args, **kwargs):
            raise OSError("Temporary failure in name resolution")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        result = validation._resolve_host_ips_uncached("fresh.fail.example")
        assert result == []


class TestValidateTargetDNSFailure:
    """Coverage for validate_target when DNS resolution fails in safe_mode."""

    def test_hostname_unresolvable_in_safe_mode_returns_error(self, monkeypatch):
        """A hostname that cannot be resolved must return (False, error) in safe_mode."""
        from backend.secuscan import validation

        validation._DNS_CACHE.pop("unresolvable.invalid", None)

        def fake_getaddrinfo(*args, **kwargs):
            raise OSError("Name does not resolve")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        # In safe_mode, the function must attempt resolution and return an error.
        ok, msg = validation.validate_target("unresolvable.invalid", safe_mode=True)
        assert ok is False
        assert "resolve" in msg.lower() or "safe mode" in msg.lower()

    def test_hostname_unresolvable_in_unsafe_mode_is_allowed(self, monkeypatch):
        """In non-safe_mode, DNS resolution is skipped, so unresolvable names are allowed."""
        from backend.secuscan import validation

        validation._DNS_CACHE.pop("unresolvable.invalid", None)

        def fake_getaddrinfo(*args, **kwargs):
            raise OSError("Name does not resolve")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        # Without safe_mode, the hostname format check passes and resolution is skipped.
        ok, msg = validation.validate_target("unresolvable.invalid", safe_mode=False)
        assert ok is True
        assert msg == ""

    def test_dns_error_does_not_corrupt_dns_cache(self, monkeypatch):
        """A failed resolution must record an empty entry in the cache."""
        from backend.secuscan import validation
        import time

        validation._DNS_CACHE.pop("cache-test.invalid", None)

        def fake_getaddrinfo(*args, **kwargs):
            raise OSError("Simulated DNS failure")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

        validation._resolve_host_ips("cache-test.invalid")

        # After a failure the cache must contain an entry (even if empty).
        cached = validation._DNS_CACHE.get("cache-test.invalid")
        assert cached is not None
        expiry, ips = cached
        assert expiry > time.time()
        assert ips == []
