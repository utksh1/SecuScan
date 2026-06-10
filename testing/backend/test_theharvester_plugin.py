"""
Contract and parser tests for the theharvester plugin.

These tests load the real plugins/theharvester/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #513: Add parser and contract coverage for plugin `theharvester`
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
from plugins.theharvester.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "theharvester"
PLUGINS_DIR = REPO_ROOT / "plugins"

# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------

def test_theharvester_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()

def test_theharvester_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)

def test_theharvester_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )

def test_theharvester_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "theharvester"

def test_theharvester_engine_is_theharvester():
    """Engine binary must be theHarvester."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "theHarvester"

def test_theharvester_has_required_target_field():
    """Plugin must declare a required target field."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))

    fields = {f["id"]: f for f in data["fields"]}

    assert "target" in fields
    assert fields["target"]["required"] is True

def test_theharvester_output_parser_is_custom():
    """Parser type must be custom and backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert data["output"]["parser"] == "custom"

def test_theharvester_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()

# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------

def test_theharvester_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct theHarvester command.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "theharvester",
        {"target": "secuscan.in"},
    )

    assert command is not None
    assert command[0] == "theHarvester"
    assert "-d" in command
    assert "secuscan.in" in command
    assert "-b" in command
    assert "all" in command

def test_theharvester_command_full_token_sequence(setup_test_environment):
    """
    Full rendered command must exactly match the command_template.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "theharvester",
        {"target": "secuscan.in"},
    )

    assert command == [
        "theHarvester",
        "-d",
        "secuscan.in",
        "-b",
        "all",
    ], f"Command template drift detected. Got: {command}"

def test_theharvester_drops_target_token_when_absent(
    setup_test_environment,
):
    """
    Renderer should not leak unresolved placeholders.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("theharvester", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered)

    populated = manager.build_command(
        "theharvester",
        {"target": "secuscan.in"},
    )

    assert "secuscan.in" in populated
    assert len(populated) == len(rendered) + 1

def test_theharvester_loaded_by_plugin_manager(
    setup_test_environment,
):
    """PluginManager must successfully load theharvester."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("theharvester")

    assert plugin is not None
    assert plugin.id == "theharvester"
    assert plugin.name == "theHarvester"

# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_THEHARVESTER_OUTPUT_FIXTURE = (
    "admin@secuscan.in\n"
    "support@secuscan.in\n"
    "mail.secuscan.in alive\n"
    "vpn.secuscan.in exposed\n"
    "portal.secuscan.in found\n"
)

def test_theharvester_parser_returns_required_keys():
    """parse() must return findings, count and items."""
    result = parse(_THEHARVESTER_OUTPUT_FIXTURE)

    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result

def test_theharvester_parser_count_matches_findings():
    """count must equal len(findings)."""
    result = parse(_THEHARVESTER_OUTPUT_FIXTURE)

    assert result["count"] == len(result["findings"])

def test_theharvester_parser_finding_has_required_keys():
    """Each finding must contain the normalized contract keys."""
    result = parse(_THEHARVESTER_OUTPUT_FIXTURE)

    assert result["findings"]

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

def test_theharvester_parser_severity_classification():
    """
    Lines with discovery keywords must be low severity.
    Other observations remain info severity.
    """
    result = parse(_THEHARVESTER_OUTPUT_FIXTURE)

    findings = result["findings"]

    assert len(findings) == 5

    assert findings[0]["severity"] == "info"
    assert findings[1]["severity"] == "info"
    assert findings[2]["severity"] == "low"
    assert findings[3]["severity"] == "low"
    assert findings[4]["severity"] == "low"

def test_theharvester_parser_empty_output():
    """Parser must handle empty input safely."""
    result = parse("")

    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []

def test_theharvester_parser_preserves_raw_line_in_metadata():
    """metadata.raw_line must preserve the original line."""
    result = parse("mail.secuscan.in alive\n")

    assert result["findings"]
    assert (
        result["findings"][0]["metadata"]["raw_line"]
        == "mail.secuscan.in alive"
    )

def test_theharvester_parser_finding_shape():
    """Verify normalized finding structure remains stable."""
    result = parse("vpn.secuscan.in exposed\n")

    finding = result["findings"][0]

    assert finding["title"] == "theHarvester Observation"
    assert finding["category"] == "Recon"
    assert finding["severity"] == "low"
    assert "Review discovery output" in finding["remediation"]