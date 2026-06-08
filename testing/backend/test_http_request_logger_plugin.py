"""
Contract and parser tests for the http_request_logger plugin.

These tests load the real plugins/http_request_logger/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #499: Add parser and contract coverage for plugin `http_request_logger`
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
from plugins.http_request_logger.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "http_request_logger"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_http_request_logger_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_http_request_logger_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_http_request_logger_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_http_request_logger_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "http_request_logger"


def test_http_request_logger_engine_is_httpx():
    """Engine binary must be 'httpx' for HTTP logging."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "httpx"


def test_http_request_logger_has_required_target_field():
    """Plugin must declare a required 'target' field for URL."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_http_request_logger_target_has_url_validation():
    """Target field must have URL pattern validation."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "validation" in fields["target"]
    assert "pattern" in fields["target"]["validation"]


def test_http_request_logger_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_http_request_logger_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_http_request_logger_requires_consent():
    """HTTP request logging is intrusive and requires consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is True


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_http_request_logger_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct httpx command for a target URL.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("http_request_logger", {"target": "https://secuscan.in"})

    assert command is not None, "build_command returned None for valid inputs"
    assert command[0] == "httpx"
    assert "-u" in command
    assert "https://secuscan.in" in command
    assert "-status-code" in command
    assert "-title" in command
    assert "-web-server" in command
    assert "-silent" in command


def test_http_request_logger_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("http_request_logger", {"target": "https://secuscan.in"})

    assert command == [
        "httpx",
        "-u",
        "https://secuscan.in",
        "-status-code",
        "-title",
        "-web-server",
        "-silent",
    ], f"Command template drift detected. Got: {command}"


def test_http_request_logger_drops_target_token_when_absent(setup_test_environment):
    """
    When the 'target' field is omitted, the renderer drops the unresolved
    {target} token rather than emitting an empty value or literal placeholder.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("http_request_logger", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert "httpx" in rendered
    assert "-status-code" in rendered

    populated = manager.build_command("http_request_logger", {"target": "https://secuscan.in"})
    assert "https://secuscan.in" in populated
    assert len(populated) > len(rendered)


def test_http_request_logger_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load http_request_logger from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("http_request_logger")
    assert plugin is not None
    assert plugin.id == "http_request_logger"
    assert plugin.name == "HTTP Request Logger"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_HTTP_REQUEST_LOGGER_OUTPUT_FIXTURE = (
    "[200] https://secuscan.in\n"
    "[200] https://secuscan.in/api\n"
    "[403] https://secuscan.in/admin - Exposed\n"
    "[500] https://api.secuscan.in - Critical Error\n"
    "[302] https://secuscan.in/redirect - Open redirect detected\n"
)


def test_http_request_logger_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_HTTP_REQUEST_LOGGER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_http_request_logger_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_HTTP_REQUEST_LOGGER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_http_request_logger_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_HTTP_REQUEST_LOGGER_OUTPUT_FIXTURE)
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


def test_http_request_logger_parser_severity_classification():
    """Severity must be classified based on keywords: info, low (found/warning), high (critical/exploit)."""
    result = parse(_HTTP_REQUEST_LOGGER_OUTPUT_FIXTURE)
    findings = result["findings"]
    assert len(findings) == 5

    # "[200] https://secuscan.in" -> info
    assert findings[0]["severity"] == "info"
    # "[200] https://secuscan.in/api" -> info
    assert findings[1]["severity"] == "info"
    # "[403] ... Exposed" -> low
    assert findings[2]["severity"] == "low"
    # "[500] ... Critical Error" -> high
    assert findings[3]["severity"] == "high"
    # "[302] ... Open redirect detected" -> low
    assert findings[4]["severity"] == "low"


def test_http_request_logger_parser_empty_output():
    """Parser must handle empty input and return empty findings without raising."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_http_request_logger_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "[200] https://secuscan.in/api - Vulnerable endpoint\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "[200] https://secuscan.in/api - Vulnerable endpoint"
