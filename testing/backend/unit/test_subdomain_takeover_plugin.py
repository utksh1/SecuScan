"""Parser and contract coverage for plugins/subdomain_takeover (issue #512)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "subdomain_takeover"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_subdomain_takeover_parser():
    spec = importlib.util.spec_from_file_location("subdomain_takeover_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_subdomain_takeover_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Subdomain Takeover"
    assert plugin.category == "exploit"
    assert plugin.safety.get("level") == "intrusive"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids


def test_subdomain_takeover_build_command_renders_representative_target(plugin_manager):
    target = "secuscan.in"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert command == ["subfinder", "-d", target, "-silent"]


def test_subdomain_takeover_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_subdomain_takeover_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3

    detected = parsed["findings"][-1]
    assert detected["severity"] == "low"
    assert "detected" in detected["description"].lower()


def test_subdomain_takeover_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_subdomain_takeover_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_subdomain_takeover_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_subdomain_takeover_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed)

    assert normalized["count"] == 3
    assert all(f["title"] for f in normalized["findings"])
