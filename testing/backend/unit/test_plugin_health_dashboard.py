import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from scripts.plugin_health_dashboard import (
    safe_relative_path,
    discover_plugins,
    build_report,
    format_markdown,
)


def test_safe_relative_path_normal_case():
    base = Path("/a/b")
    path = Path("/a/b/c/d")
    assert safe_relative_path(path, base) == "c/d"


def test_safe_relative_path_exact_match():
    base = Path("/a/b")
    path = Path("/a/b")
    assert safe_relative_path(path, base) == "."


def test_safe_relative_path_outside_returns_absolute():
    base = Path("/a/b")
    path = Path("/a/x/y")
    result = safe_relative_path(path, base)
    assert result == str(path)


def test_safe_relative_path_deeply_nested():
    base = Path("/x")
    path = Path("/x/y/z/w/v")
    assert safe_relative_path(path, base) == "y/z/w/v"


def test_discover_plugins_returns_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        plugin_dir = root / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "parser.py").write_text("# parser")
        (plugin_dir / "metadata.json").write_text(
            '{"name": "My Plugin", "category": "recon"}'
        )

        result = discover_plugins(plugin_root=root)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "My Plugin"
        assert result[0]["category"] == "recon"
        assert result[0]["has_parser"] is True


def test_discover_plugins_detects_missing_parser():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        plugin_dir = root / "no_parser"
        plugin_dir.mkdir()
        (plugin_dir / "metadata.json").write_text('{"name": "No Parser"}')

        result = discover_plugins(plugin_root=root)
        assert len(result) == 1
        assert result[0]["has_parser"] is False


def test_discover_plugins_handles_invalid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        plugin_dir = root / "bad_json"
        plugin_dir.mkdir()
        (plugin_dir / "parser.py").write_text("# x")
        (plugin_dir / "metadata.json").write_text("not json{{{")

        result = discover_plugins(plugin_root=root)
        assert len(result) == 1
        assert result[0]["name"] == "bad_json"


def test_discover_plugins_sorts_by_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        z_dir = root / "zebra"
        z_dir.mkdir()
        (z_dir / "metadata.json").write_text('{"name": "Zebra"}')
        a_dir = root / "alpha"
        a_dir.mkdir()
        (a_dir / "metadata.json").write_text('{"name": "Alpha"}')

        result = discover_plugins(plugin_root=root)
        assert result[0]["name"] == "Alpha"
        assert result[1]["name"] == "Zebra"


def test_discover_plugins_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = discover_plugins(plugin_root=Path(tmpdir))
        assert result == []


def test_build_report_summary_counts():
    plugins = [
        {"name": "A", "category": "recon", "has_parser": True},
        {"name": "B", "category": "recon", "has_parser": False},
        {"name": "C", "category": "web", "has_parser": True},
    ]
    report = build_report(plugins)
    assert report["summary"]["total_plugins"] == 3
    assert report["summary"]["plugins_with_parser"] == 2
    assert report["summary"]["plugins_without_parser"] == 1
    assert report["categories"]["recon"] == 2
    assert report["categories"]["web"] == 1


def test_build_report_empty():
    report = build_report([])
    assert report["summary"]["total_plugins"] == 0
    assert report["summary"]["plugins_with_parser"] == 0
    assert report["summary"]["plugins_without_parser"] == 0
    assert report["categories"] == {}


def test_format_markdown_contains_summary():
    report = {
        "summary": {
            "total_plugins": 3,
            "plugins_with_parser": 2,
            "plugins_without_parser": 1,
        },
        "categories": {"recon": 2, "web": 1},
        "plugins": [
            {
                "name": "Plugin A",
                "category": "recon",
                "has_parser": True,
                "path": "recon/plugin_a",
            }
        ],
    }
    output = format_markdown(report)
    assert "Total plugins: 3" in output
    assert "Plugins with parser.py: 2" in output
    assert "Plugins without parser.py: 1" in output
    assert "recon: 2" in output
    assert "web: 1" in output
    assert "Plugin A" in output
    assert "| Plugin | Category | Parser | Path |" in output


def test_format_markdown_categories_sorted():
    report = {
        "summary": {"total_plugins": 2, "plugins_with_parser": 2, "plugins_without_parser": 0},
        "categories": {"z_cat": 1, "a_cat": 1},
        "plugins": [],
    }
    output = format_markdown(report)
    assert "- a_cat: 1" in output
    assert "- z_cat: 1" in output
    assert output.index("- a_cat: 1") < output.index("- z_cat: 1")


def test_format_markdown_plugin_table_shows_parser_status():
    plugins = [
        {
            "name": "With Parser",
            "category": "web",
            "has_parser": True,
            "path": "web/with_parser",
        },
        {
            "name": "No Parser",
            "category": "web",
            "has_parser": False,
            "path": "web/no_parser",
        },
    ]
    report = {
        "summary": {"total_plugins": 2, "plugins_with_parser": 1, "plugins_without_parser": 1},
        "categories": {"web": 2},
        "plugins": plugins,
    }
    output = format_markdown(report)
    assert "| With Parser | web | Yes | `web/with_parser` |" in output
    assert "| No Parser | web | No | `web/no_parser` |" in output
