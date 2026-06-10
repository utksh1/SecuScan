"""Parser and contract coverage for plugins/subdomain-finder (issue #511)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "subdomain-finder"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_subdomain_finder_parser():
    spec = importlib.util.spec_from_file_location("subdomain_finder_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_subdomain_finder_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Subdomain Finder"
    assert plugin.category == "recon"
    assert plugin.safety.get("level") == "safe"
    assert plugin.safety.get("requires_consent") is False

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids


def test_subdomain_finder_build_command_renders_representative_target(plugin_manager):
    target = "secuscan.in"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert command == ["subfinder", "-d", target, "-silent"]


def test_subdomain_finder_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_subdomain_finder_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 1
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["title"] == "Discovery: 3 Subdomains Identified"
    assert parsed["findings"][0]["category"] == "Recon"
    assert parsed["findings"][0]["metadata"]["discovered_count"] == 3

    rows = parsed["structured"]["rows"]
    assert len(rows) == 3
    assert rows[0]["subdomain"] == "api.secuscan.in"
    assert rows[0]["ip"] == "52.0.200.63"
    assert rows[1]["subdomain"] == "staging.secuscan.in"
    assert rows[1]["ip"] == "-"
    assert parsed["structured"]["type"] == "subdomains"
    assert parsed["structured"]["total_count"] == 3


def test_subdomain_finder_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_subdomain_finder_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["structured"]["rows"] == []
    assert parsed["structured"]["total_count"] == 0


def test_subdomain_finder_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_subdomain_finder_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed)

    assert normalized["count"] == 1
    assert normalized["findings"][0]["severity"] == "info"
    assert all(f["title"] for f in normalized["findings"])
