"""
Unit tests for KnowledgeBase.infer_cpe and _normalize_version in
backend/secuscan/knowledgebase.py

Covers:
- _normalize_version: empty string, patch-level versions, extra text prefixes/suffixes,
  no-digit inputs, leading zeros, version truncation to 4 components
- infer_cpe: returns None when no match, returns CPE string on exact match,
  falls back to family match when exact version not found
"""

from __future__ import annotations

import json
import pytest

import backend.secuscan.knowledgebase as kb_mod
from backend.secuscan.knowledgebase import KnowledgeBase


@pytest.fixture(autouse=True)
def _clear_kb_cache():
    """Reset the module-level KB cache before and after each test."""
    kb_mod._cached_entries = None
    kb_mod._cached_mtime = None
    yield
    kb_mod._cached_entries = None
    kb_mod._cached_mtime = None


# ---------------------------------------------------------------------------
# _normalize_version
# ---------------------------------------------------------------------------


class TestNormalizeVersion:
    @pytest.fixture
    def _kb(self, tmp_path):
        """Create an isolated KnowledgeBase instance backed by tmp_path."""
        return KnowledgeBase(data_dir=str(tmp_path))

    def test_empty_string_returns_empty(self, _kb):
        """An empty string input returns an empty string."""
        assert _kb._normalize_version("") == ""

    def test_standard_version_with_patch(self, _kb):
        """A standard semver string is extracted unchanged."""
        assert _kb._normalize_version("1.2.3") == "1.2.3"

    def test_version_with_major_minor_only(self, _kb):
        """A version with only major.minor is extracted correctly."""
        assert _kb._normalize_version("apache2.4") == "2.4"
        assert _kb._normalize_version("nginx1.0") == "1.0"

    def test_version_prefixed_with_product_name(self, _kb):
        """A version prefixed by a product name is extracted correctly."""
        assert _kb._normalize_version("nginx-1.18.0") == "1.18.0"
        assert _kb._normalize_version("apache_2.4.55") == "2.4.55"
        assert _kb._normalize_version("node-v18.16.0") == "18.16.0"

    def test_version_with_four_components(self, _kb):
        """A 4-component version is extracted fully."""
        assert _kb._normalize_version("1.2.3.4") == "1.2.3.4"
        assert _kb._normalize_version("10.20.30.40") == "10.20.30.40"

    def test_version_with_five_components_stops_at_four(self, _kb):
        """A 5-component version is truncated to 4 components (regex max {0,3})."""
        assert _kb._normalize_version("1.2.3.4.5") == "1.2.3.4"

    def test_no_digits_returns_lowercased_stripped_input(self, _kb):
        """When no digits match, the lowercased and stripped input is returned."""
        assert _kb._normalize_version("latest") == "latest"
        assert _kb._normalize_version("  edge  ") == "edge"

    def test_leading_zeros_preserved(self, _kb):
        """Leading zeros in version components are preserved as-is."""
        result = _kb._normalize_version("v0001.002.003")
        assert result == "0001.002.003"

    def test_single_digit_version(self, _kb):
        """A single-digit version is extracted correctly."""
        assert _kb._normalize_version("nginx5") == "5"
        assert _kb._normalize_version("v9") == "9"

    def test_returns_string(self, _kb):
        """The return value is always a string."""
        for v in ["", "1.2.3", "no-digits", "apache-2.4.55", "1.2.3.4.5.6"]:
            assert isinstance(_kb._normalize_version(v), str)


# ---------------------------------------------------------------------------
# infer_cpe
# ---------------------------------------------------------------------------


class TestInferCpe:
    def _make_kb(self, tmp_path, feed_data):
        """Create a KnowledgeBase with a single feed file."""
        feed_file = tmp_path / "feed.json"
        feed_file.write_text(json.dumps(feed_data))
        return KnowledgeBase(data_dir=str(tmp_path))

    def test_returns_none_when_no_entries(self, tmp_path):
        """infer_cpe returns None when the knowledge base has no entries."""
        kb = KnowledgeBase(data_dir=str(tmp_path))
        # Use a product NOT in _SEEDED_CPE_INDEX (drupal, wordpress are not seeded)
        result = kb.infer_cpe("drupal", "drupal", "99.99.99")
        assert result is None

    def test_returns_none_when_service_not_found(self, tmp_path):
        """infer_cpe returns None when no matching service/product pattern exists."""
        kb = self._make_kb(tmp_path, {
            "cpe:/a:wordpress:wordpress:6.0.0": [
                {"cve": "CVE-2026-0001", "severity": "high", "cvss": 8.0,
                 "title": "WordPress flaw", "description": "Desc"}
            ]
        })
        # drupal does not match any _PRODUCT_PATTERNS entry
        result = kb.infer_cpe("drupal", "drupal", "1.0.0")
        assert result is None

    def test_returns_exact_cpe_on_version_match(self, tmp_path):
        """When an exact CPE version match exists, infer_cpe returns it."""
        kb = self._make_kb(tmp_path, {
            "cpe:/a:nginx:nginx:1.18.0": [
                {"cve": "CVE-2026-0001", "severity": "high", "cvss": 8.0,
                 "title": "Nginx flaw", "description": "Desc"}
            ]
        })
        result = kb.infer_cpe("nginx", "nginx", "1.18.0")
        assert result == "cpe:/a:nginx:nginx:1.18.0"

    def test_returns_family_cpe_when_exact_version_not_found(self, tmp_path):
        """When no exact version match exists, infer_cpe returns the family CPE."""
        kb = self._make_kb(tmp_path, {
            "cpe:/a:nginx:nginx:1.18.0": [
                {"cve": "CVE-2026-0001", "severity": "high", "cvss": 8.0,
                 "title": "Nginx flaw", "description": "Desc"}
            ]
        })
        result = kb.infer_cpe("nginx", "nginx", "9.9.9")
        assert result is not None
        assert result.startswith("cpe:/a:nginx:nginx:")

    def test_returns_family_cpe_when_version_is_unknown_product(self, tmp_path):
        """When the product/service is known but version normalization is tricky."""
        kb = self._make_kb(tmp_path, {
            "cpe:/a:apache:http_server:2.4.0": [
                {"cve": "CVE-2026-0001", "severity": "high", "cvss": 8.0,
                 "title": "Apache flaw", "description": "Desc"}
            ]
        })
        result = kb.infer_cpe("apache", "http_server", "2.4.0")
        assert result is not None

    def test_different_products_return_different_cpes(self, tmp_path):
        """Different service/product combinations return different CPE strings."""
        feed = {
            "cpe:/a:nginx:nginx:1.18.0": [
                {"cve": "CVE-2026-0001", "severity": "high", "cvss": 8.0,
                 "title": "Nginx flaw", "description": "Desc"}
            ],
            "cpe:/a:apache:http_server:2.4.0": [
                {"cve": "CVE-2026-0002", "severity": "high", "cvss": 8.0,
                 "title": "Apache flaw", "description": "Desc"}
            ],
        }
        kb = self._make_kb(tmp_path, feed)
        nginx_cpe = kb.infer_cpe("nginx", "nginx", "1.18.0")
        apache_cpe = kb.infer_cpe("apache", "http_server", "2.4.0")
        assert nginx_cpe != apache_cpe

    def test_returns_none_for_unknown_service_and_product(self, tmp_path):
        """When service and product don't match any known product pattern."""
        kb = self._make_kb(tmp_path, {
            "cpe:/a:nginx:nginx:1.18.0": [
                {"cve": "CVE-2026-0001", "severity": "high", "cvss": 8.0,
                 "title": "Nginx flaw", "description": "Desc"}
            ]
        })
        result = kb.infer_cpe("unknown_product", "unknown_product", "1.0.0")
        assert result is None
