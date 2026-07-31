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
