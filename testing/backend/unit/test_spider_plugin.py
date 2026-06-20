"""Parser and contract coverage for plugins/spider (issue #509)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "spider"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_spider_parser():
    spec = importlib.util.spec_from_file_location("spider_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_spider_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Spider"
    assert plugin.category == "robots"
    assert plugin.safety.get("level") == "intrusive"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert {"target", "depth"} <= field_ids


def test_spider_build_command_renders_representative_target(plugin_manager):
    target = "https://secuscan.in"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert command[:4] == ["katana", "-u", target, "-jc"]
    assert "-depth" in command
    assert "3" in command
    assert command[-1] == "-silent"


def test_spider_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_spider_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3
    assert parsed["items"][-1] == "found 2 endpoints during crawl"

    summary = parsed["findings"][-1]
    assert summary["title"] == "Recon/Scan Observation"
    assert summary["severity"] == "low"
    assert summary["metadata"]["raw"] == "found 2 endpoints during crawl"


def test_spider_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_spider_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_spider_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_spider_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(
        plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed
    )

    assert normalized["count"] == 3
    assert normalized["findings"][-1]["severity"] == "low"
    assert all(f["title"] for f in normalized["findings"])
