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
        result2 = _parse_url_hostname("https://admin:secret@api.example.com/v1/ping")
        assert result2 == "api.example.com"

    def test_url_with_fragment_and_query(self):
        """Fragments and query strings should be stripped from hostname extraction."""
        from backend.secuscan.validation import _parse_url_hostname
        result = _parse_url_hostname("http://example.com/path?query=val#frag")
        assert result == "example.com"
        result2 = _parse_url_hostname("https://api.example.com/#section")
        assert result2 == "api.example.com"

    def test_url_with_encoded_characters(self):
        """Percent-encoded characters in the URL should not break hostname extraction."""
        from backend.secuscan.validation import _parse_url_hostname
        # Encoded dot in hostname should be preserved as-is by urlparse
        result = _parse_url_hostname("http://example%2Ecom/scan")
        # urlparse preserves the encoded form in hostname
        assert result is not None
