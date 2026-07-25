from __future__ import annotations

"""
Unit tests for validation pure helpers.

Covers _parse_url_hostname from backend.secuscan.validation.
Note: _net_within_allowed_networks uses module-level settings and is tested
via integration tests rather than unit tests here.
"""

import pytest


class TestParseUrlHostname:
    def test_extracts_hostname_from_http_url(self):
        """Hostname is extracted from http:// URLs."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://example.com/scan")
        assert result == "example.com"

    def test_extracts_hostname_from_https_url(self):
        """Hostname is extracted from https:// URLs."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("https://api.example.com/v1/endpoint")
        assert result == "api.example.com"

    def test_extracts_hostname_with_port(self):
        """Hostname with port is extracted correctly (port is stripped)."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://example.com:8080/scan")
        assert result == "example.com"

    def test_ipv4_literal_returns_ip(self):
        """An IPv4 literal is returned as-is."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://192.168.1.1/scan")
        assert result == "192.168.1.1"

    def test_empty_string_returns_none(self):
        """An empty string returns None."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("")
        assert result is None

    def test_subdomain_extraction(self):
        """Subdomains are extracted correctly."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("https://sub.domain.example.com/path")
        assert result == "sub.domain.example.com"

    def test_ipv6_address_returns_ip(self):
        """IPv6 addresses are handled correctly."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://[::1]/")
        assert result == "::1"
        result2 = _parse_url_hostname("https://[2001:db8::1]:8080/scan")
        assert result2 == "2001:db8::1"

    def test_url_with_username_password(self):
        """URLs with embedded credentials should strip to just the hostname."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://user:pass@example.com/scan")
        assert result == "example.com"

    def test_url_with_fragment_and_query(self):
        """Fragments and query strings should be stripped from hostname extraction."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://example.com/path?query=val#frag")
        assert result == "example.com"

    def test_url_with_encoded_characters(self):
        """Percent-encoded characters in the URL should not break hostname extraction."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://example%2Ecom/scan")
        assert result is not None

    # Additional edge cases added for genuine missing coverage

    def test_non_http_scheme_returns_none(self):
        """Non-http(s) schemes return None."""
        from backend.secuscan.validation import _parse_url_hostname
        assert _parse_url_hostname("ftp://example.com") is None
        assert _parse_url_hostname("file:///etc/passwd") is None
        assert _parse_url_hostname("ssh://host") is None

    def test_malformed_url_returns_none(self):
        """Malformed URLs that are not parseable return None."""
        from backend.secuscan.validation import _parse_url_hostname
        assert _parse_url_hostname("not a url") is None
        assert _parse_url_hostname("://missing-scheme.com") is None

    def test_url_without_scheme_returns_none(self):
        """A hostname without a scheme returns None."""
        from backend.secuscan.validation import _parse_url_hostname
        assert _parse_url_hostname("example.com") is None

    def test_case_insensitive_scheme(self):
        """URL scheme matching is case-insensitive."""
        from backend.secuscan.validation import _parse_url_hostname
        assert _parse_url_hostname("HTTPS://EXAMPLE.COM") == "example.com"
        assert _parse_url_hostname("HTTP://API.EXAMPLE.COM") == "api.example.com"


# ---------------------------------------------------------------------------
# _resolve_host_ips_uncached
# ---------------------------------------------------------------------------


import ipaddress
from unittest.mock import patch

from backend.secuscan.validation import _resolve_host_ips_uncached


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
