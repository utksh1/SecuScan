"""
Contract and parser tests for the cloud_storage_auditor plugin.

These tests load the real plugins/cloud_storage_auditor/metadata.json, validate
it through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #492: Add parser and contract coverage for plugin `cloud_storage_auditor`
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
from plugins.cloud_storage_auditor.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "cloud_storage_auditor"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_cloud_storage_auditor_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_cloud_storage_auditor_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_cloud_storage_auditor_passes_validator():
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


def test_cloud_storage_auditor_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "cloud_storage_auditor"


def test_cloud_storage_auditor_engine_is_uncover():
    """Engine binary must be 'uncover' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "uncover"


def test_cloud_storage_auditor_has_required_query_field():
    """Plugin must declare a required 'query' field for the search query."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "query" in fields, "Missing required field: query"
    assert fields["query"]["required"] is True


def test_cloud_storage_auditor_has_optional_limit_field_with_default():
    """Plugin must declare an optional 'limit' field with a default of 100."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "limit" in fields, "Missing optional field: limit"
    assert fields["limit"].get("default") == 100, "limit default must be 100"


def test_cloud_storage_auditor_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_cloud_storage_auditor_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_cloud_storage_auditor_command_renders_with_query(setup_test_environment):
    """
    PluginManager must produce the correct uncover command for a storage query.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "cloud_storage_auditor",
        {"query": "s3.amazonaws.com org:example"},
    )

    assert command is not None, "build_command returned None for valid inputs"
    assert "uncover" in command
    assert "-q" in command
    assert "s3.amazonaws.com org:example" in command
    assert "-silent" in command


def test_cloud_storage_auditor_command_uses_default_limit(setup_test_environment):
    """
    When 'limit' is omitted, the command must use the default value from metadata.json (100).
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "cloud_storage_auditor",
        {"query": "s3.amazonaws.com org:example"},
    )

    assert command is not None
    assert "-limit" in command
    limit_idx = command.index("-limit")
    assert command[limit_idx + 1] == "100", (
        f"Default limit must be '100'. Got: {command[limit_idx + 1]}"
    )


def test_cloud_storage_auditor_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "cloud_storage_auditor",
        {"query": "s3.amazonaws.com"},
    )

    assert command == ["uncover", "-q", "s3.amazonaws.com", "-limit", "100", "-silent"], (
        f"Command template drift detected. Got: {command}"
    )


def test_cloud_storage_auditor_command_respects_explicit_limit(setup_test_environment):
    """When 'limit' is explicitly provided, it must override the default."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "cloud_storage_auditor",
        {"query": "s3.amazonaws.com", "limit": 50},
    )

    assert command is not None
    limit_idx = command.index("-limit")
    assert command[limit_idx + 1] == "50"


def test_cloud_storage_auditor_drops_query_token_when_absent(setup_test_environment):
    """
    When the 'query' field is omitted, the renderer drops the unresolved
    {query} token rather than emitting an empty value or literal placeholder.
    The default limit scaffold is preserved.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("cloud_storage_auditor", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert rendered == ["uncover", "-q", "-limit", "100", "-silent"]

    populated = manager.build_command(
        "cloud_storage_auditor", {"query": "s3.amazonaws.com"}
    )
    assert "s3.amazonaws.com" in populated
    assert len(populated) == len(rendered) + 1


def test_cloud_storage_auditor_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load cloud_storage_auditor."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("cloud_storage_auditor")
    assert plugin is not None
    assert plugin.id == "cloud_storage_auditor"
    assert plugin.name == "S3 / Blob Auditor"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_STORAGE_AUDIT_TEXT_FIXTURE = (
    "s3.amazonaws.com org:example-public\n"
    "found exposed bucket: example-public-assets\n"
    "warning: public-read ACL detected on example-public-assets\n"
    "critical: bucket exposed sensitive documents\n"
    "blob.core.windows.net container:org-backup\n"
)


def test_cloud_storage_auditor_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_STORAGE_AUDIT_TEXT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_cloud_storage_auditor_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_STORAGE_AUDIT_TEXT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_cloud_storage_auditor_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_STORAGE_AUDIT_TEXT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding, f"Finding missing key: {key}"


def test_cloud_storage_auditor_parser_critical_keyword_raises_to_high():
    """Lines containing 'critical' must be classified as 'high' severity."""
    result = parse(_STORAGE_AUDIT_TEXT_FIXTURE)
    critical_findings = [f for f in result["findings"] if "critical" in f["description"].lower()]
    assert critical_findings, "No findings from the critical line"
    for finding in critical_findings:
        assert finding["severity"] == "high"


def test_cloud_storage_auditor_parser_found_or_exposed_is_low():
    """Lines containing 'found' or 'exposed' must be at least 'low' severity."""
    result = parse(_STORAGE_AUDIT_TEXT_FIXTURE)
    exposed_findings = [
        f for f in result["findings"]
        if "exposed" in f["description"].lower() or "found" in f["description"].lower()
    ]
    assert exposed_findings, "Expected findings from exposed/found lines"
    for finding in exposed_findings:
        assert finding["severity"] in ("low", "high")


def test_cloud_storage_auditor_parser_empty_output():
    """Parser must handle empty input without raising and return empty findings."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_cloud_storage_auditor_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "found exposed bucket: example-data\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "found exposed bucket: example-data"
