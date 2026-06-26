"""
Unit tests for KnowledgeBase.status in backend/secuscan/knowledgebase.py.

Verifies the status() method returns correct metadata about the knowledge base
directory: readiness status, source type, file list, and CVE/CPE counts.
The knowledge base always includes a seeded CPE index (3 CPEs, 3 CVEs) in
addition to any loaded feed files.
"""

import json
from pathlib import Path

import pytest

from backend.secuscan.knowledgebase import KnowledgeBase


class TestKnowledgeBaseStatus:
    def test_status_returns_expected_keys(self, tmp_path):
        """status() returns all expected keys."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        expected_keys = {
            "status",
            "source",
            "directory",
            "feed_files",
            "total_cpes",
            "total_cves",
            "synced_at",
        }
        assert set(result.keys()) == expected_keys

    def test_status_is_ready(self, tmp_path):
        """status is 'ready' even when directory has no local feed files."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["status"] == "ready"

    def test_source_is_local_json_feeds(self, tmp_path):
        """source indicates local JSON feed files."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["source"] == "local-json-feeds"

    def test_directory_points_to_data_dir(self, tmp_path):
        """directory field points to the configured data directory."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["directory"] == str(tmp_path)

    def test_feed_files_empty_when_no_json(self, tmp_path):
        """feed_files is an empty list when directory has no .json files."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["feed_files"] == []
        assert isinstance(result["feed_files"], list)

    def test_total_cpes_at_least_seeded_count(self, tmp_path):
        """total_cpes is at least 3 due to the seeded CPE index."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["total_cpes"] >= 3

    def test_total_cves_at_least_seeded_count(self, tmp_path):
        """total_cves is at least 3 due to the seeded CPE index."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["total_cves"] >= 3

    def test_feed_files_lists_json_files(self, tmp_path):
        """feed_files lists the names of .json files in the directory."""
        feed_file = tmp_path / "test_feed.json"
        feed_file.write_text(json.dumps({
            "cpe:/a:custom:scanner:1.0": [
                {"cve": "CVE-2024-0001", "severity": "critical", "cvss": 9.8},
            ]
        }))
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert "test_feed.json" in result["feed_files"]
        assert isinstance(result["feed_files"], list)

    def test_feed_files_excludes_non_json(self, tmp_path):
        """Non-.json files in the data directory are not listed."""
        (tmp_path / "readme.txt").write_text("This is not a feed")
        (tmp_path / "data.csv").write_text("csv,data")
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert "readme.txt" not in result["feed_files"]
        assert "data.csv" not in result["feed_files"]

    def test_total_cves_increments_with_feed_cves(self, tmp_path):
        """total_cves increases when feed files add CVE entries."""
        empty_kb = KnowledgeBase(data_dir=tmp_path)
        baseline = empty_kb.status()["total_cves"]
        # Add a feed file with 2 CVEs
        feed_file = tmp_path / "feed.json"
        feed_file.write_text(json.dumps({
            "cpe:/a:custom:scanner:1.0": [
                {"cve": "CVE-2024-0001", "severity": "critical"},
                {"cve": "CVE-2024-0002", "severity": "high"},
            ]
        }))
        kb_with_feed = KnowledgeBase(data_dir=tmp_path)
        # Seeded has 3 CVEs; feed adds 2 more = 5 total
        assert kb_with_feed.status()["total_cves"] == baseline + 2

    def test_synced_at_none_when_no_files(self, tmp_path):
        """synced_at is None when the data directory has no .json files."""
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert result["synced_at"] is None

    def test_synced_at_is_float_when_files_exist(self, tmp_path):
        """synced_at is a numeric timestamp (float) when feed files exist."""
        feed_file = tmp_path / "feed.json"
        feed_file.write_text(json.dumps({
            "cpe:/a:custom:tool:1.0": [{"cve": "CVE-2024-X", "severity": "low"}]
        }))
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert isinstance(result["synced_at"], float)

    def test_multiple_feed_files_aggregated(self, tmp_path):
        """status correctly aggregates across multiple .json feed files."""
        (tmp_path / "feed_a.json").write_text(json.dumps({
            "cpe:/a:feed_a:tool:1.0": [{"cve": "CVE-2024-A", "severity": "high"}]
        }))
        (tmp_path / "feed_b.json").write_text(json.dumps({
            "cpe:/a:feed_b:scanner:2.0": [
                {"cve": "CVE-2024-B1", "severity": "critical"},
                {"cve": "CVE-2024-B2", "severity": "low"},
            ]
        }))
        kb = KnowledgeBase(data_dir=tmp_path)
        result = kb.status()
        assert len(result["feed_files"]) == 2
        # 3 seeded + 1 from feed_a + 2 from feed_b = 6 total
        assert result["total_cves"] == 6

    def test_status_is_deterministic(self, tmp_path):
        """status() returns the same result on repeated calls."""
        feed_file = tmp_path / "feed.json"
        feed_file.write_text(json.dumps({
            "cpe:/a:custom:scanner:1.0": [{"cve": "CVE-2024-X", "severity": "critical"}]
        }))
        kb = KnowledgeBase(data_dir=tmp_path)
        result1 = kb.status()
        result2 = kb.status()
        assert result1["total_cves"] == result2["total_cves"]
        assert result1["total_cpes"] == result2["total_cpes"]
        assert result1["feed_files"] == result2["feed_files"]
