"""
Unit tests for backend.secuscan.config Settings properties and methods.
"""

import sys
import os
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.config import Settings


class TestParseCsvOrList:
    def test_comma_separated_string(self):
        result = Settings.parse_csv_or_list("127.0.0.1,192.168.1.1,10.0.0.1")
        assert result == ["127.0.0.1", "192.168.1.1", "10.0.0.1"]

    def test_comma_separated_with_spaces(self):
        result = Settings.parse_csv_or_list("a, b, c")
        assert result == ["a", "b", "c"]

    def test_strips_whitespace(self):
        result = Settings.parse_csv_or_list(" alpha , beta ")
        assert result == ["alpha", "beta"]

    def test_passthrough_list(self):
        original = ["a", "b", "c"]
        result = Settings.parse_csv_or_list(original)
        assert result == ["a", "b", "c"]

    def test_empty_string(self):
        result = Settings.parse_csv_or_list("")
        assert result == []

    def test_list_with_whitespace_strings(self):
        result = Settings.parse_csv_or_list([" x ", " y "])
        assert result == [" x ", " y "]


class TestResolvedVaultKey:
    def test_returns_bytes_for_vault_key(self):
        # Must set env BEFORE instantiating Settings
        os.environ["SECUSCAN_VAULT_KEY"] = "test_seed_value_for_key_derivation"
        try:
            settings = Settings()
            key = settings.resolved_vault_key
            assert isinstance(key, bytes)
            # 32-byte SHA256 digest -> base64url encode gives 44 chars
            assert len(key) == 44
        finally:
            os.environ.pop("SECUSCAN_VAULT_KEY", None)

    def test_raises_runtime_error_when_unset(self):
        # Ensure env vars are NOT set
        os.environ.pop("SECUSCAN_VAULT_KEY", None)
        os.environ.pop("SECUSCAN_PLUGIN_SIGNATURE_KEY", None)
        settings = Settings()
        try:
            settings.resolved_vault_key
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "VAULT_KEY" in str(e)

    def test_consistent_output_for_same_seed(self):
        os.environ["SECUSCAN_VAULT_KEY"] = "consistent_seed_123"
        try:
            settings1 = Settings()
            settings2 = Settings()
            key1 = settings1.resolved_vault_key
            key2 = settings2.resolved_vault_key
            assert key1 == key2
        finally:
            os.environ.pop("SECUSCAN_VAULT_KEY", None)


class TestBaseUrl:
    def test_returns_correct_url_format(self):
        settings = Settings()
        settings.bind_address = "127.0.0.1"
        settings.bind_port = 8000
        assert settings.base_url == "http://127.0.0.1:8000"


class TestEnsureDirectories:
    def test_creates_directories(self, tmp_path):
        raw_dir = tmp_path / "raw"
        reports_dir = tmp_path / "reports"
        wordlists_dir = tmp_path / "wordlists"
        kb_dir = tmp_path / "knowledgebase"
        log_file = tmp_path / "logs" / "secuscan.log"

        settings = Settings()
        settings.raw_output_dir = str(raw_dir)
        settings.reports_dir = str(reports_dir)
        settings.wordlists_dir = str(wordlists_dir)
        settings.knowledgebase_dir = str(kb_dir)
        settings.log_file = str(log_file)

        settings.ensure_directories()

        assert raw_dir.exists()
        assert reports_dir.exists()
        assert wordlists_dir.exists()
        assert kb_dir.exists()
        assert log_file.parent.exists()

    def test_creates_gitkeep_files(self, tmp_path):
        raw_dir = tmp_path / "raw"
        reports_dir = tmp_path / "reports"

        settings = Settings()
        settings.raw_output_dir = str(raw_dir)
        settings.reports_dir = str(reports_dir)
        settings.wordlists_dir = str(tmp_path / "wordlists")
        settings.knowledgebase_dir = str(tmp_path / "knowledgebase")
        settings.log_file = str(tmp_path / "logs" / "secuscan.log")

        settings.ensure_directories()

        assert (raw_dir / ".gitkeep").exists()
        assert (reports_dir / ".gitkeep").exists()
