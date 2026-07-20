"""
Unit tests for _sanitize_title in backend/secuscan/ai_summary.py.

Sanitizes URLs, IP addresses, hostnames, and credentials from finding titles
before they are included in LLM prompts.
"""

import pytest

from backend.secuscan.ai_summary import _sanitize_title


class TestSanitizeTitle:
    def test_empty_string(self):
        """Empty string returns empty string."""
        assert _sanitize_title("") == ""

    def test_no_match_passthrough(self):
        """Strings without sensitive patterns pass through unchanged."""
        assert _sanitize_title("SQL Injection vulnerability") == "SQL Injection vulnerability"
        assert _sanitize_title("Cross-site scripting in search box") == "Cross-site scripting in search box"

    def test_url_http_redacted(self):
        """http:// URLs are replaced with [redacted]."""
        result = _sanitize_title("Issue at http://example.com/login")
        assert "http://example.com/login" not in result
        assert "[redacted]" in result

    def test_url_https_redacted(self):
        """https:// URLs are replaced with [redacted]."""
        result = _sanitize_title("Open redirect at https://secure.example.com/path")
        assert "https://secure.example.com/path" not in result
        assert "[redacted]" in result

    def test_ipv4_address_redacted(self):
        """IPv4 addresses are replaced with [redacted]."""
        assert _sanitize_title("SSRF at 10.0.0.1/admin") == "SSRF at [redacted]/admin"
        assert _sanitize_title("Issue on 192.168.1.100:8080") == "Issue on [redacted]:8080"
        assert _sanitize_title("DB at 172.16.0.5") == "DB at [redacted]"

    def test_hostname_redacted(self):
        """Hostnames (2+ label domain) are replaced with [redacted]."""
        result = _sanitize_title("Issue on internal-db.corp.local")
        assert "internal-db.corp.local" not in result
        assert "[redacted]" in result

    def test_credential_password_redacted(self):
        """password=VALUE credential patterns are redacted."""
        result = _sanitize_title("Default password=admin on service")
        assert "password=admin" not in result
        assert "[redacted]" in result

    def test_credential_token_redacted(self):
        """token=VALUE credential patterns are redacted."""
        result = _sanitize_title("Leaked token=abc123xyz")
        assert "token=abc123xyz" not in result
        assert "[redacted]" in result

    def test_credential_secret_redacted(self):
        """secret=VALUE credential patterns are redacted."""
        result = _sanitize_title("API secret=mysecretkey exposed")
        assert "secret=mysecretkey" not in result
        assert "[redacted]" in result

    def test_credential_key_redacted(self):
        """key=VALUE credential patterns are redacted."""
        result = _sanitize_title("API key=abcdef1234567890 leaked")
        assert "key=abcdef1234567890" not in result
        assert "[redacted]" in result

    def test_credential_auth_redacted(self):
        """auth=VALUE credential patterns are redacted."""
        result = _sanitize_title("Auth auth=BearerToken exposed")
        assert "auth=BearerToken" not in result
        assert "[redacted]" in result

    def test_credential_passwd_redacted(self):
        """passwd=VALUE credential patterns are redacted."""
        result = _sanitize_title("Default passwd=root configured")
        assert "passwd=root" not in result
        assert "[redacted]" in result

    def test_credential_credential_redacted(self):
        """credential=VALUE credential patterns are redacted."""
        result = _sanitize_title("Hardcoded credential=admin:pass found")
        assert "credential=admin:pass" not in result
        assert "[redacted]" in result

    def test_case_insensitive_password(self):
        """Credential matching is case-insensitive."""
        result = _sanitize_title("PASSWORD=secret123 exposed")
        assert "PASSWORD=secret123" not in result
        assert "[redacted]" in result

    def test_case_insensitive_token(self):
        """Token matching is case-insensitive."""
        result = _sanitize_title("TOKEN=Myt0k3n exposed")
        assert "TOKEN=Myt0k3n" not in result
        assert "[redacted]" in result

    def test_mixed_patterns_all_redacted(self):
        """Multiple pattern types in one string are all redacted."""
        result = _sanitize_title(
            "Issue at https://example.com on 10.0.0.1 with token=secret123"
        )
        assert "https://example.com" not in result
        assert "10.0.0.1" not in result
        assert "token=secret123" not in result
        assert "[redacted]" in result

    def test_strips_trailing_whitespace(self):
        """Trailing whitespace is stripped."""
        assert _sanitize_title("Title  ") == "Title"
        assert _sanitize_title("Issue http://x.com  ") == "Issue [redacted]"

    def test_consecutive_redactions_collapse(self):
        """Consecutive redactions do not produce multiple [redacted] tokens."""
        result = _sanitize_title("http://a.com http://b.com")
        # Should not have adjacent [redacted][redacted]
        assert "[redacted][redacted]" not in result
