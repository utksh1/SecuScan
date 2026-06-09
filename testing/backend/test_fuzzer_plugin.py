"""
Contract and parser tests for the fuzzer plugin.

These tests load the real plugins/fuzzer/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Related to issue #497: Add parser and contract coverage for plugin `fuzzer`
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
from plugins.fuzzer.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "fuzzer"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_fuzzer_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_fuzzer_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_fuzzer_passes_validator():
    """The full PluginMetadataValidator must accept the plugin without errors."""
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_fuzzer_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "fuzzer"


def test_fuzzer_engine_is_python3():
    """Engine binary must be 'python3'."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "python3"


def test_fuzzer_has_required_target_field():
    """Plugin must declare a required 'target' field."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_fuzzer_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_fuzzer_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_fuzzer_requires_consent():
    """Fuzzer is exploit-level and must require consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is True


def test_fuzzer_safety_level_is_exploit():
    """Safety level must be 'exploit'."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["level"] == "exploit"


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_fuzzer_command_renders_with_target(setup_test_environment):
    """PluginManager must produce a valid command for a target."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("fuzzer", {"target": "https://secuscan.in"})

    assert command is not None, "build_command returned None for valid inputs"
    assert "python3" in command
    assert "https://secuscan.in" in command


def test_fuzzer_command_contains_target_token(setup_test_environment):
    """Rendered command must contain the target value."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("fuzzer", {"target": "https://example.com"})
    assert "https://example.com" in command


def test_fuzzer_drops_target_token_when_absent(setup_test_environment):
    """When 'target' is omitted, no unresolved placeholder must appear."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("fuzzer", {})
    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"


def test_fuzzer_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load fuzzer from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("fuzzer")
    assert plugin is not None
    assert plugin.id == "fuzzer"
    assert plugin.name == "Payload Fuzzer"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_FUZZER_OUTPUT_FIXTURE = (
    "Fuzzer simulation\n"
    "target=https://secuscan.in\n"
    "payload_count=1000\n"
    "found injection point at /search\n"
    "critical: exploit successful at /admin\n"
)


def test_fuzzer_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_FUZZER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_fuzzer_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_FUZZER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_fuzzer_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_FUZZER_OUTPUT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding, f"Finding missing key: {key}"


def test_fuzzer_parser_severity_classification():
    """Lines with exploit/critical keywords must be 'high'; found/injection 'low'; others 'info'."""
    result = parse(_FUZZER_OUTPUT_FIXTURE)
    findings = {f["description"]: f["severity"] for f in result["findings"]}

    assert findings["Fuzzer simulation"] == "info"
    assert findings["target=https://secuscan.in"] == "info"
    assert findings["payload_count=1000"] == "info"
    assert findings["found injection point at /search"] == "high"
    assert findings["critical: exploit successful at /admin"] == "high"


def test_fuzzer_parser_empty_output():
    """Parser must handle empty input and return empty findings without raising."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_fuzzer_parser_high_severity_on_critical():
    """Lines containing 'critical' must produce high severity findings."""
    result = parse("critical vulnerability detected\n")
    assert result["findings"][0]["severity"] == "high"


def test_fuzzer_parser_low_severity_on_found():
    """Lines containing 'found' must produce low severity findings."""
    result = parse("found open endpoint\n")
    assert result["findings"][0]["severity"] == "low"


def test_fuzzer_parser_respects_300_line_limit():
    """Parser must cap output at 300 lines."""
    big_output = "\n".join(f"line {i}" for i in range(500))
    result = parse(big_output)
    assert result["count"] <= 300
    assert len(result["items"]) <= 300
