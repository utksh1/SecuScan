"""Parser and contract coverage for plugins/zap_scanner (issue #521)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "zap_scanner"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_zap_scanner_parser():
    spec = importlib.util.spec_from_file_location("zap_scanner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_zap_scanner_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "DAST Web Proxy (ZAP)"
    assert plugin.category == "vulnerability"
    assert plugin.safety.get("level") == "exploit"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None

    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids


def test_zap_scanner_build_command_renders_representative_target(plugin_manager):
    target = "https://secuscan.in"

    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": target},
    )

    assert command is not None
    assert command[0] == "python3"
    assert command[1] == "plugins/zap_scanner/run.py"
    assert command[2] == target


def test_zap_scanner_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_zap_scanner_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)

    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3

    first = parsed["findings"][0]

    assert first["title"] == "SQL Injection"
    assert first["category"] == "DAST"
    assert first["severity"] == "high"
    assert first["metadata"]["cweid"] == "89"

    second = parsed["findings"][1]
    assert second["title"] == "XSS Vulnerability"
    assert second["severity"] == "medium"

    third = parsed["findings"][2]
    assert third["title"] == "Missing Security Header"
    assert third["severity"] == "low"


def test_zap_scanner_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_zap_scanner_parser()

    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_zap_scanner_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_zap_scanner_parser()

    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parser.parse(raw_output)

    normalized = executor._normalize_parsed_result(
        plugin,
        raw_output,
        parsed,
    )

    assert normalized["count"] == 3
    assert len(normalized["findings"]) == 3

    assert all(f["title"] for f in normalized["findings"])
    assert all(f["category"] for f in normalized["findings"])