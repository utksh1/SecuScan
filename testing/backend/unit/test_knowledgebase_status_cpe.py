"""
Unit tests for KnowledgeBase.status() and KnowledgeBase.infer_cpe() methods.

These two public methods are currently untested. status() is used by the
knowledge-base health endpoint; infer_cpe() is used by the finding
intelligence pipeline.
"""

import tempfile
from pathlib import Path
from backend.secuscan.knowledgebase import KnowledgeBase


class TestKnowledgeBaseStatus:
    def test_returns_ready_status(self):
        kb = KnowledgeBase()
        result = kb.status()
        assert result["status"] == "ready"

    def test_returns_local_json_feeds_source(self):
        kb = KnowledgeBase()
        result = kb.status()
        assert result["source"] == "local-json-feeds"

    def test_returns_directory_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(tmpdir)
            result = kb.status()
            assert result["directory"] == tmpdir

    def test_feed_files_listed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "nvd.json").write_text('{"cves":[]}')
            (Path(tmpdir) / "exploit-db.json").write_text('{"exploits":[]}')
            kb = KnowledgeBase(tmpdir)
            result = kb.status()
            assert "nvd.json" in result["feed_files"]
            assert "exploit-db.json" in result["feed_files"]
            assert len(result["feed_files"]) == 2

    def test_empty_directory_no_sync_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(tmpdir)
            result = kb.status()
            assert result["synced_at"] is None

    def test_non_json_files_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "nvd.json").write_text('{"cves":[]}')
            (Path(tmpdir) / "readme.txt").write_text("readme")
            kb = KnowledgeBase(tmpdir)
            result = kb.status()
            assert "readme.txt" not in result["feed_files"]
            assert len(result["feed_files"]) == 1


class TestKnowledgeBaseInferCpe:
    def test_exact_version_known_product(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "nginx", "1.18.0")
        assert result == "cpe:/a:nginx:nginx:1.18.0"

    def test_family_cpe_for_unknown_version(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "nginx", "9.9.9")
        assert result == "cpe:/a:nginx:nginx:1.18.0"

    def test_none_for_unknown_product(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "totally-unknown-product", "1.0.0")
        assert result is None

    def test_none_when_service_and_product_empty(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("", "", "1.0.0")
        assert result is None

    def test_none_when_only_service_provided(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "", "1.0.0")
        assert result is None

    def test_apache_known_version(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "apache", "2.4.49")
        assert result == "cpe:/a:apache:http_server:2.4.49"

    def test_apache_httpd_alias(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "apache httpd", "2.4.49")
        assert result == "cpe:/a:apache:http_server:2.4.49"

    def test_openssh_known_version(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("ssh", "openssh", "8.2")
        assert result == "cpe:/a:openbsd:openssh:8.2"

    def test_version_normalization_strips_suffix(self):
        kb = KnowledgeBase()
        result = kb.infer_cpe("http", "nginx", "1.18.0p0")
        assert result == "cpe:/a:nginx:nginx:1.18.0"
