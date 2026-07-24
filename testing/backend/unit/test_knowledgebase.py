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


# section _normalize_version


def test_normalize_version_empty_string():
    kb = KnowledgeBase()
    assert kb._normalize_version("") == ""


def test_normalize_version_with_prefix():
    kb = KnowledgeBase()
    assert kb._normalize_version("nginx-1.2.3") == "1.2.3"


def test_normalize_version_with_dots():
    kb = KnowledgeBase()
    assert kb._normalize_version("2.4.49") == "2.4.49"


def test_normalize_version_with_trailing_text():
    kb = KnowledgeBase()
    assert kb._normalize_version("1.0-beta") == "1.0"


def test_normalize_version_purely_numeric():
    kb = KnowledgeBase()
    assert kb._normalize_version("12345") == "12345"


def test_normalize_version_with_whitespace():
    kb = KnowledgeBase()
    assert kb._normalize_version("  1.2.3  ") == "1.2.3"


def test_normalize_version_no_digits():
    kb = KnowledgeBase()
    assert kb._normalize_version("latest") == "latest"


def test_normalize_version_three_part_version():
    kb = KnowledgeBase()
    assert kb._normalize_version("1.2.3") == "1.2.3"


def test_normalize_version_four_part_version():
    kb = KnowledgeBase()
    assert kb._normalize_version("1.2.3.4") == "1.2.3.4"


# section infer_cpe


def test_infer_cpe_exact_match():
    kb = KnowledgeBase()
    result = kb.infer_cpe(service="http", product="nginx", version="1.18.0")
    assert result == "cpe:/a:nginx:nginx:1.18.0"


def test_infer_cpe_family_match():
    kb = KnowledgeBase()
    result = kb.infer_cpe(service="http", product="nginx", version="9.9.9")
    assert result == "cpe:/a:nginx:nginx:1.18.0"


def test_infer_cpe_no_match():
    kb = KnowledgeBase()
    result = kb.infer_cpe(service="http", product="notaproduct", version="1.0.0")
    assert result is None


def test_infer_cpe_empty_inputs():
    kb = KnowledgeBase()
    assert kb.infer_cpe("", "", "") is None


def test_infer_cpe_only_service():
    kb = KnowledgeBase()
    result = kb.infer_cpe(service="nginx", product="", version="")
    assert result is not None


def test_infer_cpe_only_product():
    kb = KnowledgeBase()
    result = kb.infer_cpe(service="", product="nginx", version="")
    assert result is not None


# section _find_best_cpe_match


def test_find_best_cpe_match_exact():
    kb = KnowledgeBase()
    entries = {"cpe:/a:nginx:nginx:1.18.0": []}
    result = kb._find_best_cpe_match(
        entries, service="http", product="nginx", version="1.18.0"
    )
    assert result == {"cpe": "cpe:/a:nginx:nginx:1.18.0", "match_strength": "exact"}


def test_find_best_cpe_match_strong_fuzzy():
    kb = KnowledgeBase()
    entries = {"cpe:/a:nginx:nginx:1.18.0": []}
    result = kb._find_best_cpe_match(
        entries, service="http", product="nginx", version="1.18.1"
    )
    assert result["match_strength"] == "strong_fuzzy"


def test_find_best_cpe_match_fuzzy_major_only():
    kb = KnowledgeBase()
    entries = {"cpe:/a:nginx:nginx:1.18.0": []}
    result = kb._find_best_cpe_match(
        entries, service="http", product="nginx", version="1.99.0"
    )
    assert result["match_strength"] == "fuzzy"


def test_find_best_cpe_match_family():
    kb = KnowledgeBase()
    entries = {"cpe:/a:nginx:nginx:1.18.0": []}
    result = kb._find_best_cpe_match(
        entries, service="http", product="nginx", version=""
    )
    assert result["match_strength"] == "family"


def test_find_best_cpe_match_empty_service_product():
    kb = KnowledgeBase()
    entries = {"cpe:/a:nginx:nginx:1.18.0": []}
    result = kb._find_best_cpe_match(
        entries, service="", product="", version=""
    )
    assert result is None


def test_find_best_cpe_match_unknown_product():
    kb = KnowledgeBase()
    entries = {"cpe:/a:nginx:nginx:1.18.0": []}
    result = kb._find_best_cpe_match(
        entries, service="http", product="notaproduct", version="1.0.0"
    )
    assert result is None


# section _select_version_match


def test_select_version_match_exact():
    kb = KnowledgeBase()
    cpes = ["cpe:/a:nginx:nginx:1.18.0"]
    result = kb._select_version_match(cpes, "1.18.0", same_minor=True)
    assert result == "cpe:/a:nginx:nginx:1.18.0"


def test_select_version_match_same_minor():
    kb = KnowledgeBase()
    cpes = ["cpe:/a:nginx:nginx:1.18.0", "cpe:/a:nginx:nginx:1.19.0"]
    result = kb._select_version_match(cpes, "1.18.5", same_minor=True)
    assert result == "cpe:/a:nginx:nginx:1.18.0"


def test_select_version_match_same_major():
    kb = KnowledgeBase()
    cpes = ["cpe:/a:nginx:nginx:1.18.0", "cpe:/a:nginx:nginx:2.0.0"]
    result = kb._select_version_match(cpes, "1.99.0", same_minor=False)
    assert result == "cpe:/a:nginx:nginx:1.18.0"


def test_select_version_match_no_match():
    kb = KnowledgeBase()
    cpes = ["cpe:/a:nginx:nginx:1.18.0"]
    result = kb._select_version_match(cpes, "2.0.0", same_minor=True)
    assert result is None


def test_select_version_match_empty_cpe_list():
    kb = KnowledgeBase()
    result = kb._select_version_match([], "1.0.0", same_minor=True)
    assert result is None
