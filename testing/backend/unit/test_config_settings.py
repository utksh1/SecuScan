"""
Unit tests for config.py Settings and parse_csv_or_list validator.

Covers: Settings, parse_csv_or_list, resolved_vault_key, ensure_directories
"""

import os
import tempfile
from pathlib import Path
from backend.secuscan.config import Settings, settings as global_settings


# ── parse_csv_or_list ─────────────────────────────────────────────────────────


def test_parse_csv_or_list_string():
    """Comma-separated string is split into a list."""
    result = Settings.parse_csv_or_list("1.1.1.1,2.2.2.2, 3.3.3.3 ")
    assert result == ["1.1.1.1", "2.2.2.2", "3.3.3.3"]


def test_parse_csv_or_list_list_passthrough():
    """Already-a-list passes through unchanged."""
    original = ["a", "b", "c"]
    result = Settings.parse_csv_or_list(original)
    assert result == original


def test_parse_csv_or_list_whitespace():
    """Items with surrounding whitespace are stripped."""
    result = Settings.parse_csv_or_list(" alpha ,  beta  ,gamma")
    assert result == ["alpha", "beta", "gamma"]


def test_parse_csv_or_list_empty_string():
    """Empty string returns empty list."""
    result = Settings.parse_csv_or_list("")
    assert result == []


def test_parse_csv_or_list_single_item():
    """Single item without comma is returned as a single-element list."""
    result = Settings.parse_csv_or_list("only-one")
    assert result == ["only-one"]


# ── Settings instantiation ─────────────────────────────────────────────────────


def test_settings_default_bind_address():
    """Default bind address is 127.0.0.1."""
    s = Settings()
    assert s.bind_address == "127.0.0.1"


def test_settings_default_debug():
    """Debug defaults to True."""
    s = Settings()
    assert s.debug is True


def test_settings_default_sandbox_disabled():
    """Docker sandbox is disabled by default."""
    s = Settings()
    assert s.docker_enabled is False


def test_settings_env_override():
    """Field kwargs override defaults (SECUSCAN_ prefix used for env vars, not kwarg names)."""
    s = Settings(bind_port=9999, debug=False)
    assert s.bind_port == 9999
    assert s.debug is False


# ── resolved_vault_key ────────────────────────────────────────────────────────


def test_resolved_vault_key_raises_without_key():
    """resolved_vault_key raises RuntimeError when neither vault_key nor plugin_signature_key is set."""
    s = Settings()
    # Both vault_key and plugin_signature_key default to None
    try:
        s.resolved_vault_key
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "SECUSCAN_VAULT_KEY" in str(exc)


def test_resolved_vault_key_uses_vault_key():
    """resolved_vault_key returns bytes derived from vault_key when set."""
    s = Settings(vault_key="my-secret-key")
    key = s.resolved_vault_key
    assert isinstance(key, bytes)
    assert len(key) > 0


def test_resolved_vault_key_uses_plugin_signature_key():
    """resolved_vault_key falls back to plugin_signature_key when vault_key is not set."""
    s = Settings(plugin_signature_key="another-secret")
    key = s.resolved_vault_key
    assert isinstance(key, bytes)
    assert len(key) > 0


# ── ensure_directories ────────────────────────────────────────────────────────


def test_ensure_directories_creates_dirs(tmp_path):
    """ensure_directories creates raw/reports/wordlists/knowledgebase dirs and log parent."""
    raw_dir = tmp_path / "raw"
    reports_dir = tmp_path / "reports"
    log_file = tmp_path / "logs" / "app.log"

    s = Settings(
        raw_output_dir=str(raw_dir),
        reports_dir=str(reports_dir),
        log_file=str(log_file),
        wordlists_dir=str(tmp_path / "wordlists"),
        knowledgebase_dir=str(tmp_path / "kb"),
    )
    s.ensure_directories()

    assert raw_dir.is_dir()
    assert reports_dir.is_dir()
    assert log_file.parent.is_dir()


def test_ensure_directories_creates_gitkeeps(tmp_path):
    """ensure_directories creates .gitkeep files in raw and reports dirs."""
    s = Settings(
        data_dir=str(tmp_path / "data"),
        raw_output_dir=str(tmp_path / "raw"),
        reports_dir=str(tmp_path / "reports"),
        log_file=str(tmp_path / "logs" / "app.log"),
    )
    s.ensure_directories()

    assert (tmp_path / "raw" / ".gitkeep").exists()
    assert (tmp_path / "reports" / ".gitkeep").exists()


def test_ensure_directories_idempotent(tmp_path):
    """ensure_directories is safe to call multiple times."""
    raw_dir = tmp_path / "raw"
    reports_dir = tmp_path / "reports"
    log_file = tmp_path / "logs" / "app.log"

    s = Settings(
        raw_output_dir=str(raw_dir),
        reports_dir=str(reports_dir),
        log_file=str(log_file),
        wordlists_dir=str(tmp_path / "wordlists"),
        knowledgebase_dir=str(tmp_path / "kb"),
    )
    s.ensure_directories()
    s.ensure_directories()  # must not raise
    assert raw_dir.is_dir()


# ── base_url property ─────────────────────────────────────────────────────────


def test_base_url_property():
    """base_url returns the expected http://host:port string."""
    s = Settings(bind_address="0.0.0.0", bind_port=8080)
    assert s.base_url == "http://0.0.0.0:8080"
