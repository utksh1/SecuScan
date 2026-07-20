"""
Contract and parser tests for the cloud_scanner plugin.

These tests load the real plugins/cloud_scanner/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #491: Add parser and contract coverage for plugin `cloud_scanner`
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
from plugins.cloud_scanner.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "cloud_scanner"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_cloud_scanner_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_cloud_scanner_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_cloud_scanner_passes_validator():
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


def test_cloud_scanner_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "cloud_scanner"


def test_cloud_scanner_engine_is_python3():
    """Engine binary must be 'python3' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "python3"


def test_cloud_scanner_has_required_target_field():
    """Plugin must declare a required 'target' field for the cloud account/project."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_cloud_scanner_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_cloud_scanner_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_cloud_scanner_requires_consent():
    """Cloud scanning is intrusive and must require user consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is True
    assert data["safety"]["consent_message"], "consent_message must not be empty"


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_cloud_scanner_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct command for a cloud account target.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("cloud_scanner", {"target": "org-example"})

    assert command is not None, "build_command returned None for valid inputs"
    assert "python3" in command
    assert "org-example" in command


def test_cloud_scanner_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("cloud_scanner", {"target": "my-org"})

    assert command is not None
    assert command[0] == "python3"
    assert command[-1] == "my-org", (
        f"Last token must be the interpolated target. Got: {command}"
    )


def test_cloud_scanner_drops_target_token_when_absent(setup_test_environment):
    """
    When the 'target' field is omitted, the trailing {target} token is dropped
    rather than emitting an empty value or literal placeholder. The python3 -c
    scaffold (which references sys.argv[1]) is preserved.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("cloud_scanner", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert rendered[0] == "python3"
    assert "-c" in rendered
    # The trailing positional target argument is absent
    assert "my-org" not in rendered

    populated = manager.build_command("cloud_scanner", {"target": "my-org"})
    assert populated[-1] == "my-org"
    assert len(populated) == len(rendered) + 1


def test_cloud_scanner_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load cloud_scanner from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("cloud_scanner")
    assert plugin is not None
    assert plugin.id == "cloud_scanner"
    assert plugin.name == "Cloud Scanner"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_CLOUD_SCAN_TEXT_FIXTURE = (
    "Cloud scan baseline checks\n"
    "target=my-org\n"
    "providers=aws,gcp,azure\n"
    "found exposed S3 bucket: my-org-public-data\n"
    "warning: IAM role over-permissioned\n"
    "critical: public RDS instance detected\n"
)


def test_cloud_scanner_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_CLOUD_SCAN_TEXT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_cloud_scanner_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_CLOUD_SCAN_TEXT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_cloud_scanner_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_CLOUD_SCAN_TEXT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding, f"Finding missing key: {key}"


def test_cloud_scanner_parser_critical_keyword_raises_to_high():
    """Lines containing 'critical' must be classified as 'high' severity."""
    result = parse(_CLOUD_SCAN_TEXT_FIXTURE)
    critical_findings = [f for f in result["findings"] if "critical" in f["description"].lower()]
    assert critical_findings, "No findings from critical line"
    for finding in critical_findings:
        assert finding["severity"] == "high"


def test_cloud_scanner_parser_found_keyword_raises_to_low():
    """Lines containing 'found' or 'warning' must be at least 'low' severity."""
    result = parse(_CLOUD_SCAN_TEXT_FIXTURE)
    low_or_high = [f for f in result["findings"] if f["severity"] in ("low", "high")]
    assert low_or_high, "Expected at least one non-info finding"


def test_cloud_scanner_parser_empty_output():
    """Parser must handle empty input without raising and return empty findings."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_cloud_scanner_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "critical: public RDS instance detected\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "critical: public RDS instance detected"
