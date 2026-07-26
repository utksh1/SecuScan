"""
Unit tests for backend/secuscan/finding_intelligence generate_finding_key.

generate_finding_key produces a stable deduplication key for a finding,
enabling consistent identification of the same vulnerability across different
scan tasks. This test file directly tests the function's contract.

Run with:
    python3 -m pytest testing/backend/unit/test_finding_intelligence_key.py -v --noconftest
"""

from __future__ import annotations

import re

from backend.secuscan.finding_intelligence import generate_finding_key


class TestGenerateFindingKeyFormat:
    """Tests for the format of the returned key."""

    def test_returns_string(self):
        """generate_finding_key must return a string."""
        finding = {"title": "SQL Injection", "severity": "high"}
        result = generate_finding_key(finding, "sqlmap", "http://example.com", "user-1")
        assert isinstance(result, str)

    def test_starts_with_group_prefix(self):
        """The returned key must start with 'group:'."""
        finding = {"title": "XSS", "severity": "medium"}
        result = generate_finding_key(finding, "nuclei", "http://example.com", "user-1")
        assert result.startswith("group:")

    def test_format_is_group_colon_16_hex_chars(self):
        """The key must match the pattern 'group:<16-hex-char>'."""
        finding = {"title": "Open Port", "severity": "info"}
        result = generate_finding_key(finding, "nmap", "http://example.com", "user-1")
        # Format: group:XXXXXXXXXXXXXXXX (prefix + : + 16 hex chars)
        suffix = result[len("group:"):]
        assert len(suffix) == 16
        int(suffix, 16)  # Must be valid hex


class TestGenerateFindingKeyDeterminism:
    """Tests that generate_finding_key is deterministic."""

    def test_same_inputs_produce_same_key(self):
        """Identical inputs must always produce the same key."""
        finding = {"title": "SQL Injection", "severity": "high", "cve": "CVE-2024-0001"}
        kwargs = dict(finding=finding, plugin_id="sqlmap", target="http://example.com", owner_id="user-1")
        key1 = generate_finding_key(**kwargs)
        key2 = generate_finding_key(**kwargs)
        assert key1 == key2

    def test_deterministic_across_multiple_calls(self):
        """Multiple calls with the same inputs produce identical keys."""
        finding = {"title": "XSS", "severity": "medium"}
        keys = [
            generate_finding_key(finding, "nuclei", "http://example.com", "user-1")
            for _ in range(5)
        ]
        assert len(set(keys)) == 1, "Keys must be identical across calls"


class TestGenerateFindingKeyUniqueness:
    """Tests that different inputs produce different keys."""

    def test_different_plugin_id_produces_different_key(self):
        """Different plugin_id values must produce different keys."""
        finding = {"title": "SQL Injection", "severity": "high"}
        key1 = generate_finding_key(finding, "sqlmap", "http://example.com", "user-1")
        key2 = generate_finding_key(finding, "sqli_exploiter", "http://example.com", "user-1")
        assert key1 != key2

    def test_different_target_produces_different_key(self):
        """Different target values must produce different keys."""
        finding = {"title": "SQL Injection", "severity": "high"}
        key1 = generate_finding_key(finding, "sqlmap", "http://example.com", "user-1")
        key2 = generate_finding_key(finding, "sqlmap", "http://test.com", "user-1")
        assert key1 != key2

    def test_different_owner_id_produces_different_key(self):
        """Different owner_id values must produce different keys."""
        finding = {"title": "SQL Injection", "severity": "high"}
        key1 = generate_finding_key(finding, "sqlmap", "http://example.com", "user-1")
        key2 = generate_finding_key(finding, "sqlmap", "http://example.com", "user-2")
        assert key1 != key2

    def test_different_finding_produces_different_key(self):
        """Different finding dicts must produce different keys."""
        key1 = generate_finding_key({"title": "SQL Injection"}, "sqlmap", "http://example.com", "user-1")
        key2 = generate_finding_key({"title": "XSS"}, "sqlmap", "http://example.com", "user-1")
        assert key1 != key2


class TestGenerateFindingKeyEdgeCases:
    """Tests for edge cases and missing fields."""

    def test_none_values_in_finding_dict(self):
        """None values in the finding dict must not raise."""
        finding = {"title": None, "severity": None, "cve": None}
        result = generate_finding_key(finding, "sqlmap", "http://example.com", "user-1")
        assert isinstance(result, str)
        assert result.startswith("group:")

    def test_empty_finding_dict(self):
        """An empty finding dict must not raise."""
        finding = {}
        result = generate_finding_key(finding, "sqlmap", "http://example.com", "user-1")
        assert isinstance(result, str)
        assert result.startswith("group:")

    def test_empty_plugin_id(self):
        """An empty plugin_id must not raise."""
        finding = {"title": "Test"}
        result = generate_finding_key(finding, "", "http://example.com", "user-1")
        assert isinstance(result, str)
        assert result.startswith("group:")

    def test_empty_target(self):
        """An empty target must not raise."""
        finding = {"title": "Test"}
        result = generate_finding_key(finding, "nmap", "", "user-1")
        assert isinstance(result, str)
        assert result.startswith("group:")

    def test_empty_owner_id(self):
        """An empty owner_id must not raise."""
        finding = {"title": "Test"}
        result = generate_finding_key(finding, "nmap", "http://example.com", "")
        assert isinstance(result, str)
        assert result.startswith("group:")

    def test_target_with_port_included(self):
        """A target with a port number included must be handled."""
        finding = {"title": "Test"}
        key1 = generate_finding_key(finding, "nmap", "http://example.com:8080", "user-1")
        key2 = generate_finding_key(finding, "nmap", "http://example.com", "user-1")
        # Different targets should produce different keys
        assert key1 != key2

    def test_key_length_consistent(self):
        """All keys must have the same length regardless of input size."""
        finding_small = {"title": "A"}
        finding_large = {"title": "A" * 1000, "description": "X" * 1000}
        key1 = generate_finding_key(finding_small, "nmap", "http://example.com", "user-1")
        key2 = generate_finding_key(finding_large, "nmap", "http://example.com", "user-1")
        assert len(key1) == len(key2)

