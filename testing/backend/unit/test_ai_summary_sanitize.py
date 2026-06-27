"""
Unit tests for backend.secuscan.ai_summary._sanitize_title.

Covers:
- Removes HTTP and HTTPS URLs
- Removes IPv4 addresses
- Removes hostnames (two-or-more label domain names)
- Removes credential patterns (password=, token:, secret=, etc.)
- Case-insensitive matching for credential patterns
- Returns stripped string
- Handles empty input gracefully
- Handles strings with no sensitive content
"""

import pytest

from backend.secuscan.ai_summary import _sanitize_title


class TestSanitizeTitle:
    def test_removes_http_url(self):
        result = _sanitize_title("SQL Injection https://internal.corp/db.php?q=1 found")
        assert "https://internal.corp" not in result
        assert "SQL Injection" in result

    def test_removes_http_url_no_scheme(self):
        result = _sanitize_title("Open redirect on http://evil.com/path")
        assert "http://evil.com" not in result
        assert "Open redirect on" in result

    def test_removes_ipv4_address(self):
        result = _sanitize_title("SSRF on 10.0.0.1:8080 internal service")
        assert "10.0.0.1" not in result
        assert "SSRF on" in result

    def test_removes_multiple_ipv4_addresses(self):
        result = _sanitize_title("Port open on 192.168.1.1 and 8.8.8.8")
        assert "192.168.1.1" not in result
        assert "8.8.8.8" not in result

    def test_removes_hostname(self):
        result = _sanitize_title("API key exposed on internal-db.corp.company")
        assert "internal-db.corp.company" not in result

    def test_removes_credential_pattern_password(self):
        result = _sanitize_title("Misconfigured auth: password=Secret123 on login")
        assert "password=Secret123" not in result
        assert "Misconfigured auth:" in result

    def test_removes_credential_pattern_token(self):
        result = _sanitize_title("Token leak in Authorization: token=abc123xyz789")
        assert "token=abc123xyz789" not in result
        assert "Token leak in" in result

    def test_removes_credential_pattern_secret(self):
        result = _sanitize_title("Secret exposed: secret=my-super-secret-value-123")
        assert "secret=my-super-secret" not in result

    def test_removes_credential_pattern_auth(self):
        result = _sanitize_title("Auth bypass auth=admin:password123 on /admin")
        assert "auth=admin:password123" not in result

    def test_removes_credential_pattern_case_insensitive(self):
        result = _sanitize_title("Exposed: PASSWORD=Admin123 and TOKEN=BearerXYZ")
        assert "PASSWORD=Admin123" not in result
        assert "TOKEN=BearerXYZ" not in result

    def test_returns_stripped_string(self):
        result = _sanitize_title("  SQL Injection  ")
        assert result == "SQL Injection"

    def test_handles_empty_string(self):
        result = _sanitize_title("")
        assert result == ""

    def test_handles_string_with_no_sensitive_content(self):
        result = _sanitize_title("Missing X-Frame-Options header")
        assert result == "Missing X-Frame-Options header"

    def test_handles_string_with_only_sensitive_content(self):
        result = _sanitize_title("https://10.0.0.1 secret=abc")
        assert "10.0.0.1" not in result
        assert "secret=abc" not in result
        assert "[redacted]" in result
