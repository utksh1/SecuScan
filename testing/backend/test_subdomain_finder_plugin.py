"""Contract and parser tests for the subdomain-finder plugin."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "subdomain-finder"
PLUGIN_DIR = REPO_ROOT / "plugins" / PLUGIN_ID
PLUGINS_DIR = REPO_ROOT / "plugins"
PARSER_PATH = PLUGIN_DIR / "parser.py"


def _load_parser():
    spec = importlib.util.spec_from_file_location("subdomain_finder_parser", PARSER_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module.parse


parse = _load_parser()


def test_subdomain_finder_metadata_file_exists():
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_subdomain_finder_metadata_is_valid_json():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert data["id"] == PLUGIN_ID


def test_subdomain_finder_passes_validator():
    result = PluginMetadataValidator(PLUGIN_DIR).validate()

    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_subdomain_finder_metadata_contract():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))

    assert data["name"] == "Subdomain Finder"
    assert data["category"] == "recon"
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "subfinder"
    assert data["output"]["format"] == "text"
    assert data["output"]["parser"] == "custom"
    assert data["safety"]["requires_consent"] is False

    fields = {field["id"]: field for field in data["fields"]}
    assert fields["target"]["required"] is True
    assert fields["target"]["label"] == "Root Domain"


def test_subdomain_finder_parser_file_exists():
    assert PARSER_PATH.exists()


def test_subdomain_finder_command_renders_target(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        PLUGIN_ID,
        {"target": "secuscan.in"},
    )

    assert command == [
        "subfinder",
        "-d",
        "secuscan.in",
        "-silent",
    ]


def test_subdomain_finder_loaded_by_plugin_manager(setup_test_environment):
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Subdomain Finder"


_SUBDOMAIN_OUTPUT_FIXTURE = (
    "api.secuscan.in\n"
    "admin.secuscan.in  52.0.200.63\n"
    "dev.secuscan.in\n"
)


def test_subdomain_finder_parser_returns_normalized_results():
    result = parse(_SUBDOMAIN_OUTPUT_FIXTURE)

    assert set(result.keys()) == {"findings", "count", "structured"}
    assert result["count"] == 1
    assert len(result["findings"]) == 1
    assert result["structured"]["type"] == "subdomains"
    assert result["structured"]["total_count"] == 3


def test_subdomain_finder_parser_returns_structured_rows():
    result = parse(_SUBDOMAIN_OUTPUT_FIXTURE)

    assert result["structured"]["rows"] == [
        {
            "subdomain": "api.secuscan.in",
            "ip": "-",
            "service": "Found via Recon",
            "state": "Live",
        },
        {
            "subdomain": "admin.secuscan.in",
            "ip": "52.0.200.63",
            "service": "Found via Recon",
            "state": "Live",
        },
        {
            "subdomain": "dev.secuscan.in",
            "ip": "-",
            "service": "Found via Recon",
            "state": "Live",
        },
    ]


def test_subdomain_finder_parser_normalizes_finding_shape():
    result = parse(_SUBDOMAIN_OUTPUT_FIXTURE)
    finding = result["findings"][0]

    assert set(finding.keys()) == {
        "title",
        "category",
        "severity",
        "description",
        "remediation",
        "metadata",
    }
    assert finding["title"] == "Discovery: 3 Subdomains Identified"
    assert finding["category"] == "Recon"
    assert finding["severity"] == "info"
    assert finding["metadata"] == {"discovered_count": 3}


def test_subdomain_finder_parser_ignores_non_subdomain_lines():
    result = parse(
        "not a domain\n"
        "random text\n"
        "api.secuscan.in\n"
    )

    assert result["structured"]["total_count"] == 1
    assert result["structured"]["rows"][0]["subdomain"] == "api.secuscan.in"


def test_subdomain_finder_parser_handles_empty_output():
    result = parse("")

    assert result["findings"] == []
    assert result["count"] == 0
    assert result["structured"] == {
        "rows": [],
        "type": "subdomains",
        "total_count": 0,
    }