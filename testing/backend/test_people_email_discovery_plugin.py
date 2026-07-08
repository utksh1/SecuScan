"""
Contract and parser tests for the people-email-discovery plugin.

These tests load the real plugins/people-email-discovery/metadata.json, validate it through
the project PluginMetadataValidator, render commands through the real
PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #505: Add parser and contract coverage for plugin `people-email-discovery`
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
from plugins.people_email_discovery.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "people-email-discovery"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_people_email_discovery_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_people_email_discovery_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_people_email_discovery_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.

    This will fail if any required field is missing, the engine type or safety
    level is invalid, the command template references an undeclared field, or
    the checksum field is absent or malformed.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, (
        "Plugin validation errors:\n"
        + "\n".join(e.display() for e in result.errors)
    )


def test_people_email_discovery_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "people-email-discovery"


def test_people_email_discovery_engine_is_theHarvester():
    """Engine binary must be 'theHarvester' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "theHarvester"


def test_people_email_discovery_has_required_target_field():
    """Plugin must declare a required 'target' field for the domain to enumerate."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_people_email_discovery_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_people_email_discovery_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_people_email_discovery_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct theHarvester command for domain enumeration.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("people-email-discovery", {"target": "example.com"})

    assert command is not None, "build_command returned None for valid inputs"
    assert "theHarvester" in command
    assert "-d" in command
    assert "example.com" in command
    assert "-b" in command
    assert "all" in command


def test_people_email_discovery_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("people-email-discovery", {"target": "secuscan.in"})

    assert command == ["theHarvester", "-d", "secuscan.in", "-b", "all"], (
        f"Command template drift detected. Got: {command}"
    )


def test_people_email_discovery_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load people-email-discovery from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("people-email-discovery")
    assert plugin is not None
    assert plugin.id == "people-email-discovery"
    assert plugin.name == "People Hunter"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------


_PEOPLE_EMAIL_DISCOVERY_OUTPUT_FIXTURE = (
    "admin@example.com\n"
    "info@example.com\n"
    "support@example.com\n"
    "test@example.com\n"
)


def test_people_email_discovery_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_PEOPLE_EMAIL_DISCOVERY_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_people_email_discovery_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_PEOPLE_EMAIL_DISCOVERY_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_people_email_discovery_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_PEOPLE_EMAIL_DISCOVERY_OUTPUT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding, f"Finding missing key: {key}"


def test_people_email_discovery_parser_items_list_matches_non_empty_lines():
    """items must contain each non-empty line from the output."""
    result = parse(_PEOPLE_EMAIL_DISCOVERY_OUTPUT_FIXTURE)
    expected_lines = [l.strip() for l in _PEOPLE_EMAIL_DISCOVERY_OUTPUT_FIXTURE.splitlines() if l.strip()]
    assert result["items"] == expected_lines


def test_people_email_discovery_parser_empty_output():
    """Parser must handle empty input without raising and return empty findings."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_people_email_discovery_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "admin@example.com\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "admin@example.com"
