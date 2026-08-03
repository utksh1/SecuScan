"""Contract and parser tests for the sitemap_gen plugin."""

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager
from plugins.sitemap_gen.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "sitemap_gen"
PLUGINS_DIR = REPO_ROOT / "plugins"


def test_sitemap_gen_metadata_file_exists():
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_sitemap_gen_metadata_is_valid_json():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "sitemap_gen"


def test_sitemap_gen_passes_validator():
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_sitemap_gen_metadata_contract():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert data["name"] == "Sitemap Generator"
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "katana"
    assert data["output"]["parser"] == "custom"
    assert data["safety"]["requires_consent"] is True

    fields = {field["id"]: field for field in data["fields"]}
    assert fields["target"]["required"] is True
    assert fields["depth"]["default"] == 4


def test_sitemap_gen_parser_file_exists():
    assert (PLUGIN_DIR / "parser.py").exists()


def test_sitemap_gen_command_uses_default_depth(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "sitemap_gen",
        {"target": "https://secuscan.in"},
    )

    assert command == [
        "katana",
        "-u",
        "https://secuscan.in",
        "-depth",
        "4",
        "-silent",
    ]


def test_sitemap_gen_command_respects_explicit_depth(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "sitemap_gen",
        {"target": "https://secuscan.in", "depth": 2},
    )

    assert command == [
        "katana",
        "-u",
        "https://secuscan.in",
        "-depth",
        "2",
        "-silent",
    ]


def test_sitemap_gen_loaded_by_plugin_manager(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("sitemap_gen")

    assert plugin is not None
    assert plugin.id == "sitemap_gen"
    assert plugin.name == "Sitemap Generator"


_SITEMAP_OUTPUT_FIXTURE = (
    "https://secuscan.in/\n"
    "https://secuscan.in/about\n"
    "https://secuscan.in/admin [found]\n"
    "https://secuscan.in/api/exposed\n"
    "https://secuscan.in/debug [critical]\n"
)


def test_sitemap_gen_parser_returns_normalized_results():
    result = parse(_SITEMAP_OUTPUT_FIXTURE)

    assert set(result.keys()) == {"findings", "count", "items"}
    assert result["count"] == 5
    assert len(result["findings"]) == 5
    assert result["items"] == [
        "https://secuscan.in/",
        "https://secuscan.in/about",
        "https://secuscan.in/admin [found]",
        "https://secuscan.in/api/exposed",
        "https://secuscan.in/debug [critical]",
    ]


def test_sitemap_gen_parser_normalizes_finding_shape_and_severity():
    result = parse(_SITEMAP_OUTPUT_FIXTURE)
    findings = result["findings"]

    for finding in findings:
        assert set(finding.keys()) == {
            "title",
            "category",
            "severity",
            "description",
            "remediation",
            "metadata",
        }

    assert findings[0]["severity"] == "info"
    assert findings[1]["severity"] == "info"
    assert findings[2]["severity"] == "low"
    assert findings[3]["severity"] == "low"
    assert findings[4]["severity"] == "high"


def test_sitemap_gen_parser_preserves_raw_line_in_metadata():
    result = parse("https://secuscan.in/admin [found]\n")

    assert result["findings"][0]["metadata"]["raw"] == (
        "https://secuscan.in/admin [found]"
    )


def test_sitemap_gen_parser_handles_empty_output():
    result = parse("")

    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []