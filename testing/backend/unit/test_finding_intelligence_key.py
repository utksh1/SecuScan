"""
Unit tests for generate_finding_key in backend/secuscan/finding_intelligence.py

Covers:
- Same inputs produce the same key (deterministic)
- Different plugin_ids produce different keys
- Different targets produce different keys
- Different owner_ids produce different keys
- Different finding data (different issue signatures) produce different keys
- Empty/minimal finding dict does not raise
- Key has expected format (asset:... group:...)
"""

from __future__ import annotations

import pytest

from backend.secuscan.finding_intelligence import generate_finding_key


class TestDeterministic:
    def test_same_inputs_produce_same_key(self):
        """Identical arguments always produce the same key."""
        finding = {"host": "example.com", "url": "https://example.com"}
        key1 = generate_finding_key(finding, "nmap", "example.com", "user-1")
        key2 = generate_finding_key(finding, "nmap", "example.com", "user-1")
        assert key1 == key2

    def test_key_format_starts_with_group_prefix(self):
        """The key starts with the group: prefix (outer _stable_id call)."""
        finding = {"host": "example.com"}
        key = generate_finding_key(finding, "nmap", "example.com", "user-1")
        assert key.startswith("group:")
        assert len(key) > len("group:")


class TestPluginIdDifference:
    def test_different_plugin_ids_produce_different_keys(self):
        """Different plugin_id values produce different keys."""
        finding = {"host": "example.com"}
        key_nmap = generate_finding_key(finding, "nmap", "example.com", "user-1")
        key_nikto = generate_finding_key(finding, "nikto", "example.com", "user-1")
        assert key_nmap != key_nikto


class TestTargetDifference:
    def test_different_targets_produce_different_keys(self):
        """Different target values produce different keys."""
        finding = {"host": "example.com"}
        key_a = generate_finding_key(finding, "nmap", "example.com", "user-1")
        key_b = generate_finding_key(finding, "nmap", "other.com", "user-1")
        assert key_a != key_b


class TestOwnerIdDifference:
    def test_different_owner_ids_produce_different_keys(self):
        """Different owner_id values produce different keys."""
        finding = {"host": "example.com"}
        key_a = generate_finding_key(finding, "nmap", "example.com", "user-1")
        key_b = generate_finding_key(finding, "nmap", "example.com", "user-2")
        assert key_a != key_b


class TestFindingSignatureDifference:
    def test_different_finding_data_produces_different_key(self):
        """Different finding dictionaries produce different signatures and thus different keys."""
        # Use distinct titles since those are part of the signature
        finding_a = {"title": "Open Port 80", "host": "example.com"}
        finding_b = {"title": "Open Port 443", "host": "example.com"}
        key_a = generate_finding_key(finding_a, "nmap", "example.com", "user-1")
        key_b = generate_finding_key(finding_b, "nmap", "example.com", "user-1")
        assert key_a != key_b

    def test_same_host_different_category_produces_different_key(self):
        """Findings with same host but different category produce different keys."""
        finding_a = {"category": "vulnerability", "host": "example.com"}
        finding_b = {"category": "information", "host": "example.com"}
        key_a = generate_finding_key(finding_a, "nmap", "example.com", "user-1")
        key_b = generate_finding_key(finding_b, "nmap", "example.com", "user-1")
        assert key_a != key_b


class TestEdgeCases:
    def test_empty_finding_dict_does_not_raise(self):
        """An empty finding dict is handled without raising an exception."""
        key = generate_finding_key({}, "nmap", "example.com", "user-1")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_none_values_in_finding_do_not_raise(self):
        """Finding dicts with None values are handled gracefully."""
        finding = {"host": None, "url": None, "port": None}
        key = generate_finding_key(finding, "nmap", "example.com", "user-1")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_mixed_none_and_present_keys(self):
        """Finding with some present and some None keys produces a valid key."""
        finding = {"host": "example.com", "url": None}
        key = generate_finding_key(finding, "nmap", "example.com", "user-1")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_returns_string(self):
        """The return value is always a string."""
        for args in [
            ({"host": "a.com"}, "nmap", "a.com", "u1"),
            ({}, "nikto", "b.com", "u2"),
            ({"host": None}, "nmap", "c.com", "u3"),
        ]:
            result = generate_finding_key(*args)
            assert isinstance(result, str)


class TestKeyIsolation:
    def test_fully_identical_inputs_produce_identical_keys_across_calls(self):
        """Multiple calls with fully identical arguments produce identical keys."""
        finding = {"host": "example.com", "port": 443, "service": "https"}
        keys = [
            generate_finding_key(finding, "nmap", "example.com", "admin")
            for _ in range(5)
        ]
        assert len(set(keys)) == 1

    def test_plugin_id_isolation(self):
        """Only changing plugin_id changes the key; other fields stay stable."""
        finding = {"host": "example.com"}
        base = generate_finding_key(finding, "nmap", "example.com", "user-1")
        for plugin in ["nikto", "sslscan", "nuclei", "nmap"]:
            key = generate_finding_key(finding, plugin, "example.com", "user-1")
            assert key != base or plugin == "nmap"
