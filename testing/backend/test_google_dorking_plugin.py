"""
Contract and parser tests for the google-dorking plugin.

These tests load the real plugins/google-dorking/metadata.json, validate it
through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #498: Add parser and contract coverage for plugin `google-dorking`
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager

# ---------------------------------------------------------------------------
# Load parser from hyphenated directory name
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location(
    "google_dorking_parser",
    REPO_ROOT / "plugins" / "google-dorking" / "parser.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse = _mod.parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "google-dorking"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_google_dorking_metadata_file_exists():
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_google_dorking_metadata_is_valid_json():
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_google_dorking_passes_validator():
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_google_dorking_metadata_id_matches_directory():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "google-dorking"


def test_google_dorking_engine_is_python3():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "python3"


def test_google_dorking_has_required_target_field():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields
    assert fields["target"]["required"] is True


def test_google_dorking_output_parser_is_custom():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_google_dorking_parser_file_exists():
    assert (PLUGIN_DIR / "parser.py").exists()


def test_google_dorking_does_not_require_consent():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is False


def test_google_dorking_category_is_recon():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["category"] == "recon"


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_google_dorking_loaded_by_plugin_manager(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())
    plugin = manager.get_plugin("google-dorking")
    assert plugin is not None
    assert plugin.id == "google-dorking"
    assert plugin.name == "Google Hacking"


def test_google_dorking_command_renders_with_target(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())
    command = manager.build_command("google-dorking", {"target": "secuscan.in"})
    assert command is not None
    assert command[0] == "python3"
    assert "secuscan.in" in " ".join(command)


def test_google_dorking_command_contains_dork_queries(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())
    command = manager.build_command("google-dorking", {"target": "secuscan.in"})
    full_command = " ".join(command)
    assert "site:" in full_command
    assert "inurl:admin" in full_command
    assert "filetype:sql" in full_command
    assert "intitle:index.of" in full_command


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_GOOGLE_DORKING_OUTPUT_FIXTURE = (
    "site:secuscan.in\n"
    "inurl:admin site:secuscan.in\n"
    "filetype:sql site:secuscan.in\n"
    "intitle:index.of secuscan.in\n"
    "exposed admin panel found at secuscan.in/admin\n"
    "open directory detected\n"
)


def test_google_dorking_parser_returns_required_keys():
    result = parse(_GOOGLE_DORKING_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_google_dorking_parser_count_matches_findings():
    result = parse(_GOOGLE_DORKING_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_google_dorking_parser_finding_has_required_keys():
    result = parse(_GOOGLE_DORKING_OUTPUT_FIXTURE)
    assert result["findings"]
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding


def test_google_dorking_parser_finding_title_is_stable():
    result = parse(_GOOGLE_DORKING_OUTPUT_FIXTURE)
    for finding in result["findings"]:
        assert finding["title"] == "Google Hacking Observation"


def test_google_dorking_parser_severity_classification():
    result = parse(_GOOGLE_DORKING_OUTPUT_FIXTURE)
    findings = result["findings"]
    assert len(findings) == 6
    assert findings[0]["severity"] == "info"
    assert findings[1]["severity"] == "info"
    assert findings[2]["severity"] == "info"
    assert findings[3]["severity"] == "info"
    assert findings[4]["severity"] == "low"
    assert findings[5]["severity"] == "low"


def test_google_dorking_parser_empty_output():
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_google_dorking_parser_preserves_raw_line_in_metadata():
    single_line = "exposed login page found at secuscan.in/admin\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw_line"] == "exposed login page found at secuscan.in/admin"


def test_google_dorking_parser_items_matches_lines():
    result = parse(_GOOGLE_DORKING_OUTPUT_FIXTURE)
    expected = [line.strip() for line in _GOOGLE_DORKING_OUTPUT_FIXTURE.splitlines() if line.strip()]
    assert result["items"] == expected


def test_google_dorking_parser_respects_200_line_limit():
    large_input = "\n".join(f"site:example.com/page{i}" for i in range(300))
    result = parse(large_input)
    assert result["count"] <= 200
    assert len(result["items"]) <= 200