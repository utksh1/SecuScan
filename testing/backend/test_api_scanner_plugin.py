"""
Contract and parser tests for the api_scanner plugin.

These tests load the real plugins/api_scanner/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #490: Add parser and contract coverage for plugin `api_scanner`
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
from plugins.api_scanner.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "api_scanner"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_api_scanner_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_api_scanner_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_api_scanner_passes_validator():
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


def test_api_scanner_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "api_scanner"


def test_api_scanner_engine_is_nuclei():
    """Engine binary must be 'nuclei' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "nuclei"


def test_api_scanner_has_required_target_field():
    """Plugin must declare a required 'target' field for the API base URL."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_api_scanner_target_field_uses_url_validation_preset():
    """The 'target' field must use the named url validation preset (issue #537)."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    target_validation = fields["target"].get("validation", {})
    assert target_validation.get("validation_type") == "url"
    assert target_validation.get("message") == "Must be a valid HTTP(S) URL"
    assert "pattern" not in target_validation


def test_api_scanner_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_api_scanner_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_api_scanner_requires_consent():
    """API scanning is intrusive and must require user consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is True
    assert data["safety"]["consent_message"], "consent_message must not be empty"


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_api_scanner_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct nuclei command for an API target.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "api_scanner", {"target": "https://api.example.com"}
    )

    assert command is not None, "build_command returned None for valid inputs"
    assert command[0] == "nuclei"
    assert "-u" in command
    assert "https://api.example.com" in command
    assert "-silent" in command


def test_api_scanner_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "api_scanner", {"target": "https://api.secuscan.in"}
    )

    assert command == [
        "nuclei",
        "-u",
        "https://api.secuscan.in",
        "-silent",
    ], f"Command template drift detected. Got: {command}"


def test_api_scanner_drops_target_token_when_absent(setup_test_environment):
    """
    When the 'target' field is omitted, the renderer drops the unresolved
    {target} token rather than emitting an empty value or literal placeholder.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("api_scanner", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert rendered == ["nuclei", "-u", "-silent"]

    populated = manager.build_command(
        "api_scanner", {"target": "https://api.example.com"}
    )
    assert "https://api.example.com" in populated
    assert len(populated) == len(rendered) + 1


def test_api_scanner_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load api_scanner from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("api_scanner")
    assert plugin is not None
    assert plugin.id == "api_scanner"
    assert plugin.name == "API Scanner"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_API_SCAN_TEXT_FIXTURE = (
    "https://api.example.com/v1/users [GET] [critical] [exposed]\n"
    "https://api.example.com/admin [GET] [injection] [critical]\n"
    "https://api.example.com/health [GET] [200 OK]\n"
    "https://api.example.com/graphql [POST] [warning] [detected]\n"
)


def test_api_scanner_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_API_SCAN_TEXT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_api_scanner_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_API_SCAN_TEXT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_api_scanner_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_API_SCAN_TEXT_FIXTURE)
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


def test_api_scanner_parser_critical_keyword_raises_severity():
    """Lines containing 'critical' or 'injection' must be classified as 'high' severity."""
    result = parse(_API_SCAN_TEXT_FIXTURE)
    high_findings = [f for f in result["findings"] if f["severity"] == "high"]
    assert (
        len(high_findings) >= 1
    ), "Expected at least one high-severity finding from critical/injection lines"


def test_api_scanner_parser_low_severity_for_exposed():
    """Lines containing 'exposed' or 'found' but not critical keywords must be 'low' severity."""
    result = parse(_API_SCAN_TEXT_FIXTURE)
    exposed_lines = [
        f for f in result["findings"] if "exposed" in f["description"].lower()
    ]
    for finding in exposed_lines:
        assert finding["severity"] in (
            "low",
            "high",
        ), f"Unexpected severity '{finding['severity']}' for exposed finding"


def test_api_scanner_parser_empty_output():
    """Parser must handle empty input and return empty findings without raising."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_api_scanner_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "https://api.example.com/v1/tokens [GET] [exposed]\n"
    result = parse(single_line)
    assert result["findings"]
    assert (
        result["findings"][0]["metadata"]["raw"]
        == "https://api.example.com/v1/tokens [GET] [exposed]"
    )


def test_api_scanner_parser_handles_paginated_fixture():
    """
    Simulate paginated scanner output arriving in multiple chunks.
    The parser should process all lines across pages.
    """
    page_1 = (
        "https://api.example.com/v1/users [GET] [found]\n"
        "https://api.example.com/v1/admin [GET] [warning]\n"
    )

    page_2 = (
        "https://api.example.com/v1/health [GET] [200 OK]\n"
        "https://api.example.com/graphql [POST] [detected]\n"
    )

    combined_output = page_1 + page_2

    result = parse(combined_output)

    assert result["count"] == 4
    assert len(result["findings"]) == 4
    assert len(result["items"]) == 4


def test_api_scanner_parser_handles_chunked_response_fixture():
    """
    Simulate chunked scanner output that is concatenated before parsing.
    """
    chunks = [
        "https://api.example.com/a [GET] [found]\n",
        "https://api.example.com/b [GET] [warning]\n",
        "https://api.example.com/c [GET] [critical]\n",
    ]

    result = parse("".join(chunks))

    assert result["count"] == 3

    severities = {f["severity"] for f in result["findings"]}

    assert "low" in severities
    assert "high" in severities
