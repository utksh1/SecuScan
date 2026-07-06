"""
Unit tests for backend/secuscan/executor_target_helpers.py.

Tests the extract_target helper that was extracted from executor.py into
an import-safe module for isolated unit testing.
"""

import pytest

from backend.secuscan.executor_target_helpers import extract_target


class TestExtractTarget:
    def test_returns_target_when_present(self):
        """When 'target' key is present, its value is returned."""
        result = extract_target({"target": "192.168.1.1"})
        assert result == "192.168.1.1"

    def test_returns_url_when_target_absent(self):
        """When 'target' is absent but 'url' is present, url value is returned."""
        result = extract_target({"url": "https://example.com"})
        assert result == "https://example.com"

    def test_returns_host_when_target_and_url_absent(self):
        """When target and url are absent but host is present, host is returned."""
        result = extract_target({"host": "scanme.nmap.org"})
        assert result == "scanme.nmap.org"

    def test_returns_domain_when_only_domain_present(self):
        """When only domain is present, domain is returned."""
        result = extract_target({"domain": "example.com"})
        assert result == "example.com"

    def test_priority_target_over_url(self):
        """target takes priority over url."""
        result = extract_target({"target": "10.0.0.1", "url": "http://example.com"})
        assert result == "10.0.0.1"

    def test_priority_url_over_host(self):
        """url takes priority over host when target is absent."""
        result = extract_target({"url": "http://example.com", "host": "localhost"})
        assert result == "http://example.com"

    def test_priority_host_over_domain(self):
        """host takes priority over domain when target and url are absent."""
        result = extract_target({"host": "target.local", "domain": "example.com"})
        assert result == "target.local"

    def test_returns_empty_string_when_no_keys_present(self):
        """Empty dict returns empty string."""
        result = extract_target({})
        assert result == ""

    def test_returns_empty_string_when_all_values_none(self):
        """Dict with all None values returns empty string."""
        result = extract_target({"target": None, "url": None, "host": None, "domain": None})
        assert result == ""

    def test_returns_empty_string_when_all_values_empty_string(self):
        """Dict with all empty string values returns empty string."""
        result = extract_target({"target": "", "url": "", "host": "", "domain": ""})
        assert result == ""

    def test_mixed_present_and_absent_keys(self):
        """Only the first available key in priority order is returned."""
        result = extract_target({"domain": "fallback.com", "host": None, "url": None, "target": None})
        assert result == "fallback.com"

    def test_preserves_full_target_value(self):
        """Full URL string is preserved when passed as target."""
        result = extract_target({"target": "http://192.168.1.1:8080/admin"})
        assert result == "http://192.168.1.1:8080/admin"

    def test_handles_whitespace_in_value(self):
        """Whitespace in target value is preserved."""
        result = extract_target({"target": "  192.168.1.1  "})
        assert result == "  192.168.1.1  "
