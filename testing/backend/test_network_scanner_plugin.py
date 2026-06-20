"""
Contract and parser tests for the network_scanner plugin.

These tests load the real plugins/network_scanner/metadata.json, validate it through
the project PluginMetadataValidator, render commands through the real
PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #503: Add parser and contract coverage for plugin `network_scanner`
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
from plugins.network_scanner.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "network_scanner"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_network_scanner_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_network_scanner_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_network_scanner_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.

    This will fail if any required field is missing, the engine type or safety
    level is invalid, the command template references an undeclared field, or
    the checksum field is absent or malformed.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_network_scanner_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "network_scanner"


def test_network_scanner_engine_is_nmap():
    """Engine binary must be 'nmap' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "nmap"


def test_network_scanner_has_required_target_field():
    """Plugin must declare a required 'target' field for network scanning."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_network_scanner_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_network_scanner_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_network_scanner_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct nmap command for network scanning.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("network_scanner", {"target": "192.168.1.1"})

    assert command is not None, "build_command returned None for valid inputs"
    assert "nmap" in command
    assert "--top-ports" in command
    assert "192.168.1.1" in command


def test_network_scanner_command_uses_default_top_ports(setup_test_environment):
    """When top_ports is omitted, the command must use the default value from metadata.json."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("network_scanner", {"target": "example.com"})

    assert command is not None
    assert "--top-ports" in command
    ports_idx = command.index("--top-ports")
    assert (
        command[ports_idx + 1] == "1000"
    ), f"Default top ports must be '1000'. Got: {command[ports_idx + 1]}"


def test_network_scanner_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load network_scanner from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("network_scanner")
    assert plugin is not None
    assert plugin.id == "network_scanner"
    assert plugin.name == "Network Scanner"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------


_NETWORK_SCANNER_OUTPUT_FIXTURE = (
    "PORT     STATE SERVICE\n"
    "22/tcp   open  ssh\n"
    "80/tcp   open  http\n"
    "443/tcp  open  https\n"
    "3306/tcp open  mysql\n"
)


def test_network_scanner_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_NETWORK_SCANNER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_network_scanner_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_NETWORK_SCANNER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_network_scanner_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_NETWORK_SCANNER_OUTPUT_FIXTURE)
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


def test_network_scanner_parser_items_list_matches_non_empty_lines():
    """items must contain each non-empty line from the output."""
    result = parse(_NETWORK_SCANNER_OUTPUT_FIXTURE)
    expected_lines = [
        l.strip() for l in _NETWORK_SCANNER_OUTPUT_FIXTURE.splitlines() if l.strip()
    ]
    assert result["items"] == expected_lines


def test_network_scanner_parser_empty_output():
    """Parser must handle empty input without raising and return empty findings."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_network_scanner_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "22/tcp   open  ssh\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "22/tcp   open  ssh"
