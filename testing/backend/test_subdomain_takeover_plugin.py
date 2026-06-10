import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager
from plugins.subdomain_takeover.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "subdomain_takeover"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------

def test_subdomain_takeover_metadata_file_exists():
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_subdomain_takeover_metadata_is_valid_json():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text())
    assert isinstance(data, dict)


def test_subdomain_takeover_passes_validator():
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "\n".join(e.display() for e in result.errors)


def test_subdomain_takeover_metadata_id_matches_directory():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text())
    assert data["id"] == "subdomain_takeover"


def test_subdomain_takeover_engine_is_subfinder():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text())
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "subfinder"


def test_subdomain_takeover_output_parser_is_custom():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text())
    assert data["output"]["parser"] == "custom"


def test_subdomain_takeover_parser_file_exists():
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests
# ---------------------------------------------------------------------------

def test_subdomain_takeover_command_renders_with_target(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "subdomain_takeover",
        {"target": "secuscan.in"},
    )

    assert command is not None
    assert command[0] == "subfinder"
    assert "-d" in command
    assert "secuscan.in" in command
    assert "-silent" in command


def test_subdomain_takeover_command_full_token_sequence(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "subdomain_takeover",
        {"target": "secuscan.in"},
    )

    assert command == [
        "subfinder",
        "-d",
        "secuscan.in",
        "-silent",
    ]


def test_subdomain_takeover_drops_target_token_when_absent(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("subdomain_takeover", {})

    assert rendered == ["subfinder", "-d", "-silent"]

    populated = manager.build_command(
        "subdomain_takeover",
        {"target": "secuscan.in"},
    )

    assert "secuscan.in" in populated


def test_subdomain_takeover_loaded_by_plugin_manager(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("subdomain_takeover")

    assert plugin is not None
    assert plugin.id == "subdomain_takeover"
    assert plugin.name.lower().replace(" ", "_") == "subdomain_takeover"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

_FIXTURE = (
    "blog.example.com\n"
    "cdn.example.com [found]\n"
    "old.example.com [exposed]\n"
    "critical exploit detected\n"
)


def test_subdomain_takeover_parser_returns_required_keys():
    result = parse(_FIXTURE)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_subdomain_takeover_parser_count_matches_findings():
    result = parse(_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_subdomain_takeover_parser_finding_has_required_keys():
    result = parse(_FIXTURE)

    for f in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in f


def test_subdomain_takeover_parser_severity_classification():
    result = parse(_FIXTURE)
    findings = result["findings"]

    assert findings[0]["severity"] == "info"
    assert findings[1]["severity"] == "low"
    assert findings[2]["severity"] == "low"
    assert findings[3]["severity"] == "high"


def test_subdomain_takeover_parser_empty_output():
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_subdomain_takeover_parser_preserves_raw_line():
    result = parse("sub.example.com [exposed]\n")
    assert result["findings"][0]["metadata"]["raw"] == "sub.example.com [exposed]"