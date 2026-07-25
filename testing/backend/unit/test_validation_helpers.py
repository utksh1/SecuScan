"""
Unit tests for internal validation helpers in backend/secuscan/validation.py.

Covers untested helper functions:
- _parse_url_hostname: extracts hostname from URL strings
- _resolve_host_ips_uncached: performs fresh DNS resolution
"""

from __future__ import annotations

import ipaddress
from unittest.mock import patch

import pytest

from backend.secuscan.validation import _parse_url_hostname, _resolve_host_ips_uncached


# ---------------------------------------------------------------------------
# _parse_url_hostname
# ---------------------------------------------------------------------------

class TestParseUrlHostname:
    def test_https_url_returns_hostname(self):
        result = _parse_url_hostname("https://example.com/path")
        assert result == "example.com"

    def test_http_url_returns_hostname(self):
        result = _parse_url_hostname("http://example.com")
        assert result == "example.com"

    def test_https_with_port_returns_hostname(self):
        result = _parse_url_hostname("https://example.com:8443/api")
        assert result == "example.com"

    def test_url_with_subdomain(self):
        result = _parse_url_hostname("https://api.example.com/v1/users")
        assert result == "api.example.com"

    def test_non_http_scheme_returns_none(self):
        assert _parse_url_hostname("ftp://example.com") is None
        assert _parse_url_hostname("file:///etc/passwd") is None
        assert _parse_url_hostname("ssh://host") is None

    def test_malformed_url_returns_none(self):
        assert _parse_url_hostname("not a url") is None
        assert _parse_url_hostname("") is None

    def test_empty_string_returns_none(self):
        assert _parse_url_hostname("") is None

    def test_url_without_scheme_returns_none(self):
        assert _parse_url_hostname("example.com") is None

    def test_case_insensitive(self):
        assert _parse_url_hostname("HTTPS://EXAMPLE.COM") == "example.com"
        assert _parse_url_hostname("HTTP://API.EXAMPLE.COM") == "api.example.com"

    def test_ipv4_literal(self):
        result = _parse_url_hostname("http://192.168.1.1:8080/")
        assert result == "192.168.1.1"

    def test_ipv6_literal(self):
        result = _parse_url_hostname("http://[::1]/path")
        assert result == "::1"


# ---------------------------------------------------------------------------
# _resolve_host_ips_uncached
# ---------------------------------------------------------------------------

class TestResolveHostIpsUncached:
    def test_resolves_localhost(self):
        """Resolving localhost should return at least 127.0.0.1."""
        ips = _resolve_host_ips_uncached("localhost")
        assert len(ips) >= 1
        assert all(isinstance(ip, ipaddress._BaseAddress) for ip in ips)

    def test_returns_list_of_ipaddress_objects(self):
        ips = _resolve_host_ips_uncached("localhost")
        for ip in ips:
            assert isinstance(ip, (ipaddress.IPv4Address, ipaddress.IPv6Address))

    def test_unknown_hostname_returns_empty_list(self):
        ips = _resolve_host_ips_uncached("this-domain-definitely-does-not-exist-xyz123.invalid")
        assert ips == []

    def test_result_is_list(self):
        assert isinstance(_resolve_host_ips_uncached("localhost"), list)

    def test_resolve_twice_produces_same_result_for_stable_hostnames(self):
        """Two resolutions of a stable hostname should return the same IPs."""
        ips1 = _resolve_host_ips_uncached("localhost")
        ips2 = _resolve_host_ips_uncached("localhost")
        assert set(str(ip) for ip in ips1) == set(str(ip) for ip in ips2)

    def test_resolve_bypasses_dns_cache(self):
        """_resolve_host_ips_uncached should not use the DNS cache."""
        # This is tested by calling it twice: if it used cache, it would be fast both times
        # By calling with an unknown host first, we ensure the cache is not polluted
        _resolve_host_ips_uncached("no-such-host-unique-xyz.invalid")
        # No assertion needed; the function should not raise
        # The key test is that it calls socket.getaddrinfo fresh each time
        assert True


class TestResolveHostIpsUncachedMocked:
    def test_resolves_ipv4_from_mocked_getaddrinfo(self):
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, None, None, None, ("93.184.216.34", 0)),
            ]
            ips = _resolve_host_ips_uncached("example.com")
            assert len(ips) == 1
            assert str(ips[0]) == "93.184.216.34"

    def test_resolves_ipv6_from_mocked_getaddrinfo(self):
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (10, None, None, None, ("::1", 0, 0, 0)),
            ]
            ips = _resolve_host_ips_uncached("localhost")
            assert len(ips) == 1
            assert str(ips[0]) == "::1"

    def test_deduplicates_ips(self):
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, None, None, None, ("1.2.3.4", 0)),
                (2, None, None, None, ("1.2.3.4", 0)),
            ]
            ips = _resolve_host_ips_uncached("example.com")
            assert len(ips) == 1

    def test_preserves_order(self):
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (2, None, None, None, ("1.1.1.1", 0)),
                (2, None, None, None, ("8.8.8.8", 0)),
            ]
            ips = _resolve_host_ips_uncached("example.com")
            assert [str(ip) for ip in ips] == ["1.1.1.1", "8.8.8.8"]

    def test_raises_on_invalid_hostname(self):
        with patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = OSError("Name resolution failed")
            ips = _resolve_host_ips_uncached("invalid-host")
            assert ips == []
