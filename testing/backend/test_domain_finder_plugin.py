"""
Contract and parser tests for the domain-finder plugin.

These tests load the real plugins/domain-finder/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #496: Add parser and contract coverage for plugin `domain-finder`
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
from plugins.domain_finder.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "domain-finder"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_domain_finder_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_domain_finder_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_domain_finder_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_domain_finder_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "domain-finder"


def test_domain_finder_engine_is_amass():
    """Engine binary must be 'amass' for domain enumeration."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "amass"


def test_domain_finder_has_required_target_field():
    """Plugin must declare a required 'target' field for domain."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_domain_finder_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_domain_finder_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_domain_finder_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct domain-finder command for a domain.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("domain-finder", {"target": "secuscan.in"})

    assert command is not None, "build_command returned None for valid inputs"
    assert command[0] == "amass"
    assert "enum" in command
    assert "-d" in command
    assert "secuscan.in" in command
    assert "-dir" in command
    assert "/tmp/amass" in command
    assert "-silent" in command


def test_domain_finder_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("domain-finder", {"target": "secuscan.in"})

    assert command == [
        "amass",
        "enum",
        "-d",
        "secuscan.in",
        "-dir",
        "/tmp/amass",
        "-silent",
    ], f"Command template drift detected. Got: {command}"


def test_domain_finder_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load domain-finder from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("domain-finder")
    assert plugin is not None
    assert plugin.id == "domain-finder"
    assert plugin.name == "Domain Finder"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_DOMAIN_FINDER_OUTPUT_FIXTURE = (
    "secuscan.in\n"
    "api.secuscan.in [alive]\n"
    "dev.secuscan.in\n"
    "admin.secuscan.in [exposed]\n"
    "staging.secuscan.in [found]\n"
)


def test_domain_finder_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_DOMAIN_FINDER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_domain_finder_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_DOMAIN_FINDER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_domain_finder_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_DOMAIN_FINDER_OUTPUT_FIXTURE)
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


def test_domain_finder_parser_severity_classification():
    """Lines with keywords must be 'low' severity, others 'info'."""
    result = parse(_DOMAIN_FINDER_OUTPUT_FIXTURE)
    findings = result["findings"]
    assert len(findings) == 5

    # "secuscan.in" -> info
    assert findings[0]["severity"] == "info"
    # "api.secuscan.in [alive]" -> low
    assert findings[1]["severity"] == "low"
    # "dev.secuscan.in" -> info
    assert findings[2]["severity"] == "info"
    # "admin.secuscan.in [exposed]" -> low
    assert findings[3]["severity"] == "low"
    # "staging.secuscan.in [found]" -> low
    assert findings[4]["severity"] == "low"


def test_domain_finder_parser_empty_output():
    """Parser must handle empty input and return empty findings without raising."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_domain_finder_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw_line must match the original output line."""
    single_line = "sub.secuscan.in [exposed]\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw_line"] == "sub.secuscan.in [exposed]"
