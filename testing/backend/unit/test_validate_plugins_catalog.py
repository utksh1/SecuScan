"""
Unit tests for scripts/validate_plugins_catalog.py

Tests the pure helper functions: parse_plugins_md,
extract_counts_from_catalog, and validate_catalog.
"""

import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent / "scripts"))
import validate_plugins_catalog
from validate_plugins_catalog import (
    parse_plugins_md,
    extract_counts_from_catalog,
    validate_catalog,
)

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent


class TestParsePluginsMd:
    def test_parses_table_row(self, tmp_path):
        content = (
            "| Plugin | ID | Category | Safety |\n"
            "| --- | --- | --- | --- |\n"
            "| Nmap Scanner | `nmap` | `network` | `safe` |\n"
        )
        f = tmp_path / "PLUGINS.md"
        f.write_text(content)
        result = parse_plugins_md(f)
        assert "nmap" in result
        assert result["nmap"]["category"] == "network"
        assert result["nmap"]["safety"] == "safe"

    def test_missing_file_exits(self, tmp_path, capsys):
        with pytest.raises(SystemExit):
            parse_plugins_md(tmp_path / "nonexistent.md")

    def test_empty_file_returns_empty_dict(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        result = parse_plugins_md(f)
        assert result == {}

    def test_skips_header_row(self, tmp_path):
        content = (
            "| Plugin | ID | Category | Safety |\n"
            "| --- | --- | --- | --- |\n"
        )
        f = tmp_path / "PLUGINS.md"
        f.write_text(content)
        result = parse_plugins_md(f)
        assert result == {}

    def test_multiple_plugins_parsed(self, tmp_path):
        content = (
            "| Plugin | ID | Category | Safety |\n"
            "| --- | --- | --- | --- |\n"
            "| Nmap | `nmap` | `network` | `safe` |\n"
            "| Zap | `zap` | `web` | `intrusive` |\n"
        )
        f = tmp_path / "PLUGINS.md"
        f.write_text(content)
        result = parse_plugins_md(f)
        assert "nmap" in result
        assert "zap" in result


class TestExtractCountsFromCatalog:
    def test_counts_at_a_glance_section(self, tmp_path):
        # extract_counts_from_catalog parses the "At a Glance" section
        # Format: "- Total plugins: 60" -> key="total_plugins", value=60
        content = "- Total plugins: 50\n- Safe plugins: 30\n- Intrusive plugins: 15\n"
        f = tmp_path / "PLUGINS.md"
        f.write_text(content)
        counts = extract_counts_from_catalog(f)
        assert counts.get("total_plugins", 0) == 50
        assert counts.get("safe_plugins", 0) == 30

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_counts_from_catalog(tmp_path / "nonexistent.md")


class TestValidateCatalog:
    def test_missing_plugin_in_dir_reports_error(self, tmp_path):
        catalog = tmp_path / "PLUGINS.md"
        catalog.write_text(
            "| Plugin | ID | Category | Safety |\n"
            "| --- | --- | --- | --- |\n"
            "| Missing | `missing` | `web` | `safe` |\n"
        )
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        ok, errors = validate_catalog(catalog, plugins_dir)
        assert ok is False
        assert len(errors) >= 1

    def test_empty_catalog_and_dir_returns_clean(self, tmp_path):
        catalog = tmp_path / "PLUGINS.md"
        catalog.write_text("")
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        ok, errors = validate_catalog(catalog, plugins_dir)
        assert ok is True
        assert errors == []

    def test_extra_plugin_in_dir_reports_error(self, tmp_path):
        catalog = tmp_path / "PLUGINS.md"
        catalog.write_text(
            "| Plugin | ID | Category | Safety |\n"
            "| --- | --- | --- | --- |\n"
        )
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        extra = plugins_dir / "orphan"
        extra.mkdir()
        metadata = extra / "metadata.json"
        metadata.write_text('{"name": "orphan"}')
        ok, errors = validate_catalog(catalog, plugins_dir)
        assert ok is False
