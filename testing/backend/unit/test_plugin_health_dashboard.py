import json
from pathlib import Path

from scripts.plugin_health_dashboard import (
    discover_plugins,
    safe_relative_path,
)


def test_safe_relative_path_returns_relative_path(tmp_path):
    base = tmp_path
    path = base / "plugins" / "nmap"

    path.mkdir(parents=True)

    assert Path(safe_relative_path(path, base)) == Path("plugins") / "nmap"


def test_safe_relative_path_returns_absolute_when_outside_base(tmp_path):
    base = tmp_path / "project"
    base.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    assert safe_relative_path(outside, base) == str(outside)


def test_discover_plugins_returns_empty_for_missing_directory(tmp_path):
    plugin_root = tmp_path / "plugins"

    result = discover_plugins(plugin_root)

    assert result == []


def test_discover_plugins_returns_empty_for_empty_directory(tmp_path):
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()

    result = discover_plugins(plugin_root)

    assert result == []


def test_discover_plugins_finds_plugin_with_parser(tmp_path):
    plugin_root = tmp_path / "plugins"

    plugin_dir = plugin_root / "nmap"
    plugin_dir.mkdir(parents=True)

    metadata = {
        "name": "Nmap",
        "category": "network",
        "description": "Network scanner",
    }

    (plugin_dir / "metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    (plugin_dir / "parser.py").write_text(
        "# parser",
        encoding="utf-8",
    )

    result = discover_plugins(plugin_root)

    assert len(result) == 1

    plugin = result[0]

    assert plugin["name"] == "Nmap"
    assert plugin["category"] == "network"
    assert plugin["description"] == "Network scanner"
    assert plugin["has_metadata"] is True
    assert plugin["has_parser"] is True
    assert Path(plugin["path"]) == Path("plugins") / "nmap"
    assert Path(plugin["metadata_path"]) == (
    Path("plugins") / "nmap" / "metadata.json"
)


def test_discover_plugins_without_parser(tmp_path):
    plugin_root = tmp_path / "plugins"

    plugin_dir = plugin_root / "testplugin"
    plugin_dir.mkdir(parents=True)

    (plugin_dir / "metadata.json").write_text(
        json.dumps({"name": "Test Plugin"}),
        encoding="utf-8",
    )

    result = discover_plugins(plugin_root)

    assert len(result) == 1
    assert result[0]["has_parser"] is False


def test_discover_plugins_invalid_metadata_json(tmp_path):
    plugin_root = tmp_path / "plugins"

    plugin_dir = plugin_root / "broken_plugin"
    plugin_dir.mkdir(parents=True)

    (plugin_dir / "metadata.json").write_text(
        "{ invalid json",
        encoding="utf-8",
    )

    result = discover_plugins(plugin_root)

    assert len(result) == 1

    plugin = result[0]

    assert plugin["name"] == "broken_plugin"
    assert plugin["category"] == "uncategorized"
    assert plugin["description"] == ""
    assert plugin["has_parser"] is False

def test_discover_plugins_defaults_name_to_directory(tmp_path):
    plugin_root = tmp_path / "plugins"

    plugin_dir = plugin_root / "sample_plugin"
    plugin_dir.mkdir(parents=True)

    (plugin_dir / "metadata.json").write_text(
        json.dumps(
            {
                "category": "network"
            }
        ),
        encoding="utf-8",
    )

    result = discover_plugins(plugin_root)

    assert len(result) == 1

    plugin = result[0]

    assert plugin["name"] == "sample_plugin"
    assert plugin["category"] == "network"
    assert plugin["description"] == ""
    assert plugin["has_parser"] is False

def test_discover_plugins_sorted_by_name(tmp_path):
    plugin_root = tmp_path / "plugins"

    for name in ["Zulu", "Alpha"]:
        plugin_dir = plugin_root / name.lower()
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "metadata.json").write_text(
            json.dumps({"name": name}),
            encoding="utf-8",
        )

    result = discover_plugins(plugin_root)

    assert [plugin["name"] for plugin in result] == [
        "Alpha",
        "Zulu",
    ]