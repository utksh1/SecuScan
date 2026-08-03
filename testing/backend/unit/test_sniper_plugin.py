"""Parser and contract coverage for plugins/sniper (issue #508)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "sniper"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_sniper_parser():
    spec = importlib.util.spec_from_file_location("sniper_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_sniper_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Sniper: Auto-Exploiter"
    assert plugin.category == "exploit"
    assert plugin.safety.get("level") == "exploit"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids


def test_sniper_build_command_renders_representative_target(plugin_manager):
    target = "secuscan.in"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert command[0] == "python3"
    assert command[1] == "-c"
    assert target in command
    assert "Sniper simulation started" in command[2]


def test_sniper_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_sniper_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3
    assert parsed["items"] == [
        "Sniper simulation started",
        "target=secuscan.in",
        "status=planned_exploit_path",
    ]

    first = parsed["findings"][0]
    assert first["title"] == "Recon/Scan Observation"
    assert first["category"] == "Security Scan"
    assert first["severity"] == "info"
    assert first["metadata"]["raw"] == "Sniper simulation started"

    exploit_line = parsed["findings"][-1]
    assert exploit_line["severity"] == "high"
    assert "exploit" in exploit_line["description"].lower()


def test_sniper_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_sniper_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_sniper_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_sniper_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed)

    assert normalized["count"] == 3
    assert len(normalized["findings"]) == 3
    assert normalized["findings"][-1]["severity"] == "high"
    assert all(f["title"] for f in normalized["findings"])
    assert all(f["category"] for f in normalized["findings"])
