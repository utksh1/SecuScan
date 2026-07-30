"""
Contract and parser tests for the sharepoint_scanner plugin.

These tests load the real plugins/sharepoint_scanner/metadata.json, validate it through
the project PluginMetadataValidator, render commands through the real
PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #506: Add parser and contract coverage for plugin `sharepoint_scanner`
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
from plugins.sharepoint_scanner.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "sharepoint_scanner"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_sharepoint_scanner_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_sharepoint_scanner_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_sharepoint_scanner_passes_validator():
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


def test_sharepoint_scanner_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "sharepoint_scanner"


def test_sharepoint_scanner_engine_is_nuclei():
    """Engine binary must be 'nuclei' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "nuclei"


def test_sharepoint_scanner_has_required_target_field():
    """Plugin must declare a required 'target' field for the SharePoint URL."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_sharepoint_scanner_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_sharepoint_scanner_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_sharepoint_scanner_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct nuclei command for a SharePoint scan.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("sharepoint_scanner", {"target": "https://sharepoint.example.com"})

    assert command is not None, "build_command returned None for valid inputs"
    assert "nuclei" in command
    assert "-u" in command
    assert "https://sharepoint.example.com" in command
    assert "-silent" in command


def test_sharepoint_scanner_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("sharepoint_scanner", {"target": "https://secuscan.in"})

    assert command == ["nuclei", "-u", "https://secuscan.in", "-silent"], (
        f"Command template drift detected. Got: {command}"
    )


def test_sharepoint_scanner_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load sharepoint_scanner from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("sharepoint_scanner")
    assert plugin is not None
    assert plugin.id == "sharepoint_scanner"
    assert plugin.name == "Sharepoint Scanner"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------


_SHAREPOINT_SCANNER_OUTPUT_FIXTURE = (
    "https://sharepoint.example.com/sites/admin [found]\n"
    "https://sharepoint.example.com/sites/documents [critical]\n"
    "https://sharepoint.example.com/lists [exposed]\n"
    "https://sharepoint.example.com/_vti_bin [injection]\n"
)


def test_sharepoint_scanner_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_SHAREPOINT_SCANNER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_sharepoint_scanner_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_SHAREPOINT_SCANNER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_sharepoint_scanner_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_SHAREPOINT_SCANNER_OUTPUT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding, f"Finding missing key: {key}"


def test_sharepoint_scanner_parser_critical_and_injection_raise_to_high():
    """Lines containing 'critical' or 'injection' must be classified as 'high' severity."""
    result = parse(_SHAREPOINT_SCANNER_OUTPUT_FIXTURE)
    high_findings = [
        f for f in result["findings"]
        if "critical" in f["description"].lower() or "injection" in f["description"].lower()
    ]
    assert high_findings, "Expected at least one high-severity finding"
    for finding in high_findings:
        assert finding["severity"] == "high"


def test_sharepoint_scanner_parser_exposed_or_found_is_at_least_low():
    """Lines containing 'exposed', 'found', or 'detected' must be at least 'low' severity."""
    result = parse(_SHAREPOINT_SCANNER_OUTPUT_FIXTURE)
    flagged = [
        f for f in result["findings"]
        if any(kw in f["description"].lower() for kw in ("exposed", "found", "detected"))
    ]
    assert flagged, "Expected at least one low-severity finding from flagged keywords"
    for finding in flagged:
        assert finding["severity"] in ("low", "high")


def test_sharepoint_scanner_parser_items_list_matches_non_empty_lines():
    """items must contain each non-empty line from the output."""
    result = parse(_SHAREPOINT_SCANNER_OUTPUT_FIXTURE)
    expected_lines = [l.strip() for l in _SHAREPOINT_SCANNER_OUTPUT_FIXTURE.splitlines() if l.strip()]
    assert result["items"] == expected_lines


def test_sharepoint_scanner_parser_empty_output():
    """Parser must handle empty input without raising and return empty findings."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_sharepoint_scanner_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "https://sharepoint.example.com/sites/admin [found]\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "https://sharepoint.example.com/sites/admin [found]"
