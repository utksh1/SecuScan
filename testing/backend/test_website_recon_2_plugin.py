"""
Contract and parser tests for the website-recon-2 plugin.

These tests load the real plugins/website-recon-2/metadata.json,
validate it through the project PluginMetadataValidator, render
commands through the real PluginManager, and call the real parser.py
parse() function.

Related to issue #519: Add parser and contract coverage for plugin
`website-recon-2`
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager

PLUGIN_DIR = REPO_ROOT / "plugins" / "website_recon"
PLUGINS_DIR = REPO_ROOT / "plugins"

# ---------------------------------------------------------------------------
# Load parser dynamically (directory contains '-')
# ---------------------------------------------------------------------------

_parser_path = PLUGIN_DIR / "parser.py"

spec = importlib.util.spec_from_file_location(
    "website_recon_2_parser",
    _parser_path,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parse = module.parse

# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------

def test_website_recon_2_metadata_file_exists():
    assert (PLUGIN_DIR / "metadata.json").exists()

def test_website_recon_2_metadata_is_valid_json():
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)

def test_website_recon_2_passes_validator():
    result = PluginMetadataValidator(PLUGIN_DIR).validate()

    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )

def test_website_recon_2_metadata_id_matches_directory():
    data = json.loads(
        (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    )

    assert data["id"] == "website_recon"

def test_website_recon_2_engine_is_httpx():
    data = json.loads(
        (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    )

    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "httpx"

def test_website_recon_2_has_required_target_field():
    data = json.loads(
        (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    )

    fields = {f["id"]: f for f in data["fields"]}

    assert "target" in fields
    assert fields["target"]["required"] is True

def test_website_recon_2_output_parser_is_custom():
    data = json.loads(
        (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    )

    assert data["output"]["parser"] == "custom"

def test_website_recon_2_parser_file_exists():
    assert (PLUGIN_DIR / "parser.py").exists()

# ---------------------------------------------------------------------------
# Command rendering tests
# ---------------------------------------------------------------------------

def test_website_recon_2_command_renders_with_target(
    setup_test_environment,
):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "website_recon",
        {"target": "https://secuscan.in"},
    )

    assert command is not None

    assert command[0] == "httpx"
    assert "-u" in command
    assert "https://secuscan.in" in command
    assert "-title" in command
    assert "-status-code" in command
    assert "-tech-detect" in command
    assert "-silent" in command

def test_website_recon_2_command_full_token_sequence(
    setup_test_environment,
):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "website_recon",
        {"target": "https://secuscan.in"},
    )

    assert command == [
        "httpx",
        "-u",
        "https://secuscan.in",
        "-title",
        "-status-code",
        "-tech-detect",
        "-silent",
    ]

def test_website_recon_2_drops_target_token_when_absent(
    setup_test_environment,
):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command(
        "website_recon",
        {},
    )

    assert rendered is not None
    assert not any("{" in token for token in rendered)

    populated = manager.build_command(
        "website_recon",
        {"target": "https://secuscan.in"},
    )

    assert "https://secuscan.in" in populated

def test_website_recon_2_loaded_by_plugin_manager(
    setup_test_environment,
):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("website_recon")

    assert plugin is not None
    assert plugin.id == "website_recon"

# ---------------------------------------------------------------------------
# Parser contract tests
# ---------------------------------------------------------------------------

_HTTPX_OUTPUT_FIXTURE = (
    "https://secuscan.in [200] [SecuScan] [Cloudflare]\n"
    "https://api.secuscan.in alive\n"
    "https://admin.secuscan.in exposed\n"
    "https://staging.secuscan.in found\n"
    "https://dev.secuscan.in\n"
)

def test_website_recon_2_parser_returns_required_keys():
    result = parse(_HTTPX_OUTPUT_FIXTURE)

    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result

def test_website_recon_2_parser_count_matches_findings():
    result = parse(_HTTPX_OUTPUT_FIXTURE)

    assert result["count"] == len(result["findings"])

def test_website_recon_2_parser_finding_has_required_keys():
    result = parse(_HTTPX_OUTPUT_FIXTURE)

    assert result["findings"]

    for finding in result["findings"]:
        for key in (
            "title",
            "category",
            "severity",
            "description",
            "remediation",
            "metadata",
        ):
            assert key in finding

def test_website_recon_2_parser_severity_classification():
    result = parse(_HTTPX_OUTPUT_FIXTURE)

    findings = result["findings"]

    assert findings[0]["severity"] == "info"
    assert findings[1]["severity"] == "low"
    assert findings[2]["severity"] == "low"
    assert findings[3]["severity"] == "low"
    assert findings[4]["severity"] == "info"

def test_website_recon_2_parser_empty_output():
    result = parse("")

    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []

def test_website_recon_2_parser_preserves_raw_line_in_metadata():
    line = "https://admin.secuscan.in exposed\n"

    result = parse(line)

    assert result["findings"]
    assert (
        result["findings"][0]["metadata"]["raw_line"]
        == "https://admin.secuscan.in exposed"
    )