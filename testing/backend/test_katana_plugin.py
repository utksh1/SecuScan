"""
Contract and parser tests for the katana plugin.

These tests load the real plugins/katana/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #501: Add parser and contract coverage for plugin `katana`
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager
from plugins.katana.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "katana"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_katana_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_katana_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_katana_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_katana_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "katana"


def test_katana_engine_is_katana():
    """Engine binary must be 'katana'."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "katana"


def test_katana_has_required_target_field():
    """Plugin must declare a required 'target' field."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_katana_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_katana_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_katana_requires_consent():
    """Katana crawling is intrusive and requires consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is True


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_katana_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct katana command for a target.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("katana", {"target": "https://secuscan.in"})

    assert command is not None, "build_command returned None for valid inputs"
    assert command[0] == "katana"
    assert "-u" in command
    assert "https://secuscan.in" in command
    assert "-silent" in command


def test_katana_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("katana", {"target": "https://secuscan.in"})

    assert command == [
        "katana",
        "-u",
        "https://secuscan.in",
        "-silent",
    ], f"Command template drift detected. Got: {command}"


def test_katana_drops_target_token_when_absent(setup_test_environment):
    """
    When the 'target' field is omitted, the renderer drops the unresolved
    {target} token rather than emitting an empty value or literal placeholder.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("katana", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert rendered == ["katana", "-u", "-silent"]

    populated = manager.build_command("katana", {"target": "https://secuscan.in"})
    assert "https://secuscan.in" in populated
    assert len(populated) == len(rendered) + 1


def test_katana_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load katana from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("katana")
    assert plugin is not None
    assert plugin.id == "katana"
    assert plugin.name == "Katana"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_KATANA_OUTPUT_FIXTURE = (
    "https://secuscan.in\n"
    "https://secuscan.in/api\n"
    "https://secuscan.in/api/exposed\n"
    "https://api.secuscan.in/v1/endpoint\n"
    "https://admin.secuscan.in/vulnerable\n"
)


def test_katana_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_KATANA_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_katana_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_KATANA_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_katana_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_KATANA_OUTPUT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in (
            "title",
            "category",
            "severity",
            "description",
            "remediation",
            "metadata",
        ):
            assert key in finding, f"Finding missing key: {key}"


def test_katana_parser_severity_classification():
    """Lines with vulnerability keywords must be 'low' severity, others 'info'."""
    result = parse(_KATANA_OUTPUT_FIXTURE)
    findings = result["findings"]
    assert len(findings) == 5

    # "https://secuscan.in" -> info
    assert findings[0]["severity"] == "info"
    # "https://secuscan.in/api" -> info
    assert findings[1]["severity"] == "info"
    # "https://secuscan.in/api/exposed" -> low
    assert findings[2]["severity"] == "low"
    # "https://api.secuscan.in/v1/endpoint" -> info
    assert findings[3]["severity"] == "info"
    # "https://admin.secuscan.in/vulnerable" -> low
    assert findings[4]["severity"] == "low"


def test_katana_parser_empty_output():
    """Parser must handle empty input and return empty findings without raising."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_katana_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw_line must match the original output line."""
    single_line = "https://secuscan.in/admin/exposed\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw_line"] == "https://secuscan.in/admin/exposed"
