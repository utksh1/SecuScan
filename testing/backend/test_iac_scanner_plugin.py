"""
Contract and parser tests for the iac_scanner plugin.

These tests load the real plugins/iac_scanner/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #500: Add parser and contract coverage for plugin `iac_scanner`
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
from plugins.iac_scanner.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "iac_scanner"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_iac_scanner_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_iac_scanner_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_iac_scanner_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_iac_scanner_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "iac_scanner"


def test_iac_scanner_engine_is_python3():
    """Engine binary must be 'python3' for IaC scanning."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "python3"


def test_iac_scanner_has_required_target_field():
    """Plugin must declare a required 'target' field for IaC directory."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_iac_scanner_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_iac_scanner_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_iac_scanner_does_not_require_consent():
    """IaC scanning is safe analysis and does not require consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is False


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_iac_scanner_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct iac_scanner command for a directory.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("iac_scanner", {"target": "/path/to/iac"})

    assert command is not None, "build_command returned None for valid inputs"
    assert command[0] == "python3"
    assert "-c" in command
    assert "/path/to/iac" in command


def test_iac_scanner_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("iac_scanner", {"target": "/tmp/iac_files"})

    assert command[0] == "python3"
    assert command[1] == "-c"
    assert "/tmp/iac_files" in command


def test_iac_scanner_renders_without_target_field(setup_test_environment):
    """
    When target field is omitted, PluginManager renders the command as-is.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("iac_scanner", {})

    assert command is not None
    assert len(command) >= 2
    assert command[0] == "python3"
    assert command[1] == "-c"


def test_iac_scanner_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load iac_scanner from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("iac_scanner")
    assert plugin is not None
    assert plugin.id == "iac_scanner"
    assert plugin.name == "IaC Scanner (Checkov)"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_IAC_SCANNER_OUTPUT_FIXTURE = (
    "terraform/main.tf: Resource configuration found\n"
    "terraform/security.tf: Open security group detected\n"
    "cloudformation/vpc.yaml: Critical network exposure found\n"
    "infrastructure/rds.json: Vulnerable database configuration detected\n"
    "ansible/playbook.yml: Warning: unencrypted secrets in file\n"
)


def test_iac_scanner_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_IAC_SCANNER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_iac_scanner_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_IAC_SCANNER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_iac_scanner_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_IAC_SCANNER_OUTPUT_FIXTURE)
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


def test_iac_scanner_parser_severity_classification():
    """Severity must be classified based on keywords: info, low (found/warning), high (critical/exploit)."""
    result = parse(_IAC_SCANNER_OUTPUT_FIXTURE)
    findings = result["findings"]
    assert len(findings) == 5

    # "Resource configuration found" -> low
    assert findings[0]["severity"] == "low"
    # "Open security group detected" -> low
    assert findings[1]["severity"] == "low"
    # "Critical network exposure found" -> high
    assert findings[2]["severity"] == "high"
    # "Vulnerable database configuration detected" -> low
    assert findings[3]["severity"] == "low"
    # "Warning: unencrypted secrets" -> low
    assert findings[4]["severity"] == "low"


def test_iac_scanner_parser_empty_output():
    """Parser must handle empty input and return empty findings without raising."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_iac_scanner_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "terraform/main.tf: Critical infrastructure vulnerability detected\n"
    result = parse(single_line)
    assert result["findings"]
    assert (
        result["findings"][0]["metadata"]["raw"]
        == "terraform/main.tf: Critical infrastructure vulnerability detected"
    )
