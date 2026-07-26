
import json
import os
import time
from unittest.mock import patch
from backend.secuscan.knowledgebase import KnowledgeBase


def test_find_vulnerabilities_returns_exact_match_strength():
    kb = KnowledgeBase()

    result = kb.find_vulnerabilities(service="http", product="nginx", version="1.18.0")

    assert result["cpe"] == "cpe:/a:nginx:nginx:1.18.0"
    assert result["match_strength"] == "exact"
    assert result["cves"]


def test_find_vulnerabilities_returns_family_only_for_weak_match():
    kb = KnowledgeBase()

    result = kb.find_vulnerabilities(service="http", product="nginx", version="9.9.9")

    assert result["cpe"] == "cpe:/a:nginx:nginx:1.18.0"
    assert result["match_strength"] == "family"


def test_knowledgebase_caching_and_invalidation(tmp_path):
    # Ensure cache is initially clean
    import backend.secuscan.knowledgebase as kb_mod
    kb_mod._cached_entries = None
    kb_mod._cached_mtime = None

    # Create temporary knowledgebase directory
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    # Create a dummy json file
    feed_file = kb_dir / "feed1.json"
    dummy_data = {
        "cpe:/a:test:test:1.0": [
            {
                "cve": "CVE-2026-9999",
                "severity": "high",
                "cvss": 8.8,
                "title": "Test vulnerability",
                "description": "Test vulnerability desc"
            }
        ]
    }
    feed_file.write_text(json.dumps(dummy_data))

    # Initialize KnowledgeBase pointing to the temporary directory
    kb = KnowledgeBase(data_dir=kb_dir)

    # First load
    with patch("json.loads", wraps=json.loads) as mock_loads:
        entries = kb._load_entries()
        assert "cpe:/a:test:test:1.0" in entries
        assert mock_loads.call_count == 1

    # Second load without modifying files
    with patch("json.loads", wraps=json.loads) as mock_loads:
        entries2 = kb._load_entries()
        assert entries2 is entries  # Should be the same cached dict
        assert mock_loads.call_count == 0

    # Modify the feed file to change its mtime/content
    time.sleep(0.01)
    new_data = {
        "cpe:/a:test:test:1.0": [
            {
                "cve": "CVE-2026-9999",
                "severity": "high",
                "cvss": 8.8,
                "title": "Test vulnerability",
                "description": "Test vulnerability desc"
            }
        ],
        "cpe:/a:test:new:1.0": []
    }
    feed_file.write_text(json.dumps(new_data))

    current_mtime = feed_file.stat().st_mtime
    os.utime(feed_file, (current_mtime + 5.0, current_mtime + 5.0))

    # Load again
    with patch("json.loads", wraps=json.loads) as mock_loads:
        entries3 = kb._load_entries()
        assert "cpe:/a:test:new:1.0" in entries3
        assert mock_loads.call_count == 1


# ---------------------------------------------------------------------------
# infer_cpe
# ---------------------------------------------------------------------------


class TestInferCpe:
    def test_exact_match_nginx(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="http", product="nginx", version="1.18.0")
        assert result == "cpe:/a:nginx:nginx:1.18.0"

    def test_exact_match_apache(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="http", product="apache", version="2.4.49")
        assert result == "cpe:/a:apache:http_server:2.4.49"

    def test_returns_none_for_unknown_product(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="http", product="unknown-tool", version="1.0")
        assert result is None

    def test_returns_none_for_empty_product(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="http", product="", version="1.0")
        assert result is None

    def test_returns_none_for_empty_service_and_product(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="", product="", version="1.0")
        assert result is None

    def test_fuzzy_match_openssh(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="ssh", product="openssh", version="8.2")
        assert result is not None
        assert "openssh" in result

    def test_infer_cpe_uses_family_when_exact_version_not_in_entries(self):
        # 9.9.9 does not exist in seeded entries, should fall back to family
        kb = KnowledgeBase()
        result = kb.infer_cpe(service="http", product="nginx", version="9.9.9")
        assert result is not None
        assert "nginx" in result


# ---------------------------------------------------------------------------
# _normalize_version
# ---------------------------------------------------------------------------


class TestNormalizeVersion:
    def test_strips_leading_v_prefix(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("v1.2.3") == "1.2.3"
        assert kb._normalize_version("V2.0.0") == "2.0.0"

    def test_extracts_numeric_prefix(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("1.2.3-beta") == "1.2.3"
        assert kb._normalize_version("2.0.0-rc1") == "2.0.0"
        assert kb._normalize_version("3.1.4.5-alpha.1") == "3.1.4.5"

    def test_handles_empty_string(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("") == ""

    def test_handles_purely_alphabetic_string(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("abc") == "abc"

    def test_handles_string_with_no_digits(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("latest") == "latest"

    def test_preserves_version_without_prefix(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("1.2.3") == "1.2.3"

    def test_strips_whitespace(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("  1.2.3  ") == "1.2.3"

    def test_lowercases_result(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("V1.2.3") == "1.2.3"

    def test_version_four_part_is_truncated(self):
        # Regex only supports up to 4 parts (1 + 3 optional .digit groups)
        kb = KnowledgeBase()
        assert kb._normalize_version("1.2.3.4.5") == "1.2.3.4"

    def test_single_number(self):
        kb = KnowledgeBase()
        assert kb._normalize_version("5") == "5"
