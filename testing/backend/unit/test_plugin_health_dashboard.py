"""
Unit tests for scripts/plugin_health_dashboard.py

Tests the helper functions: safe_relative_path, discover_plugins,
build_report, and format_markdown.
"""

import json
import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent / "scripts"))
from plugin_health_dashboard import (
    safe_relative_path,
    discover_plugins,
    build_report,
    format_markdown,
)


class TestSafeRelativePath:
    def test_child_path_returns_relative(self, tmp_path):
        child = tmp_path / "subdir" / "file.txt"
        result = safe_relative_path(child, tmp_path)
        assert result == f"subdir{pathlib.os.sep}file.txt"

    def test_path_traversal_returns_absolute(self, tmp_path):
        sibling = tmp_path.parent / "outside.txt"
        result = safe_relative_path(sibling, tmp_path)
        assert "outside.txt" in result

    def test_same_path_returns_dot(self, tmp_path):
        result = safe_relative_path(tmp_path, tmp_path)
        assert result == "."

    def test_deep_traversal(self, tmp_path):
        deep = tmp_path.parent.parent / "even_deeper.txt"
        result = safe_relative_path(deep, tmp_path)
        assert "even_deeper.txt" in result


class TestDiscoverPlugins:
    def test_missing_dir_returns_empty(self, tmp_path):
        result = discover_plugins(tmp_path / "nonexistent")
        assert result == []

    def test_empty_dir_returns_empty(self, tmp_path):
        result = discover_plugins(tmp_path)
        assert result == []

    def test_discovers_metadata_json(self, tmp_path):
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        metadata = plugin_dir / "metadata.json"
        metadata.write_text(json.dumps({"name": "test", "category": "scanner"}))
        result = discover_plugins(tmp_path)
        assert len(result) == 1
        assert result[0]["name"] == "test"

    def test_parsers_detected(self, tmp_path):
        plugin_dir = tmp_path / "nmap"
        plugin_dir.mkdir()
        metadata = plugin_dir / "metadata.json"
        metadata.write_text(json.dumps({"name": "nmap", "category": "scanner"}))
        parser = plugin_dir / "parser.py"
        parser.write_text("")
        result = discover_plugins(tmp_path)
        assert result[0]["has_parser"] is True

    def test_missing_parser_flagged(self, tmp_path):
        plugin_dir = tmp_path / "orphan"
        plugin_dir.mkdir()
        metadata = plugin_dir / "metadata.json"
        metadata.write_text(json.dumps({"name": "orphan"}))
        result = discover_plugins(tmp_path)
        assert result[0]["has_parser"] is False

    def test_broken_json_defaults_to_empty(self, tmp_path):
        plugin_dir = tmp_path / "broken"
        plugin_dir.mkdir()
        metadata = plugin_dir / "metadata.json"
        metadata.write_text("{invalid json")
        result = discover_plugins(tmp_path)
        assert len(result) == 1
        assert result[0]["name"] == "broken"
        assert result[0]["category"] == "uncategorized"


class TestBuildReport:
    def test_summary_counts(self, tmp_path):
        plugins = [
            {"name": "p1", "has_parser": True, "category": "web"},
            {"name": "p2", "has_parser": False, "category": "web"},
            {"name": "p3", "has_parser": True, "category": "network"},
        ]
        report = build_report(plugins)
        assert report["summary"]["total_plugins"] == 3
        assert report["summary"]["plugins_with_parser"] == 2
        assert report["summary"]["plugins_without_parser"] == 1

    def test_categories_aggregated(self, tmp_path):
        plugins = [
            {"name": "p1", "has_parser": True, "category": "web"},
            {"name": "p2", "has_parser": True, "category": "web"},
            {"name": "p3", "has_parser": True, "category": "api"},
        ]
        report = build_report(plugins)
        assert report["categories"]["web"] == 2
        assert report["categories"]["api"] == 1

    def test_empty_plugins(self):
        report = build_report([])
        assert report["summary"]["total_plugins"] == 0
        assert report["plugins"] == []


class TestFormatMarkdown:
    def test_contains_summary(self):
        report = {
            "summary": {
                "total_plugins": 2,
                "plugins_with_parser": 1,
                "plugins_without_parser": 1,
            },
            "categories": {"web": 1, "api": 1},
            "plugins": [
                {"name": "p1", "has_parser": True, "category": "web", "path": "p1"},
                {"name": "p2", "has_parser": False, "category": "api", "path": "p2"},
            ],
        }
        md = format_markdown(report)
        assert "Total plugins: 2" in md
        assert "Plugins with parser.py: 1" in md

    def test_categories_section(self):
        report = {
            "summary": {"total_plugins": 1, "plugins_with_parser": 1, "plugins_without_parser": 0},
            "categories": {"scanner": 1},
            "plugins": [],
        }
        md = format_markdown(report)
        assert "scanner: 1" in md
