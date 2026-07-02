"""Parser and contract coverage for plugins/yara_scan."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "yara_scan"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_yara_parser():
    spec = importlib.util.spec_from_file_location("yara_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_yara_metadata_loads(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin_manager.get_plugin_schema(PLUGIN_ID) is not None


def test_yara_build_command(plugin_manager):
    command = plugin_manager.build_command(
        PLUGIN_ID,
        {
            "target": "/tmp/sample.exe",
            "rules": "/tmp/rules.yar",
        },
    )

    assert command is not None
    assert command[0] == "yara"
    assert "-r" in command
    assert "/tmp/sample.exe" in command
    assert "/tmp/rules.yar" in command


def test_yara_parser_fixture(plugin_manager):
    parser = _load_yara_parser()

    parsed = parser.parse(FIXTURE_PATH.read_text())

    assert parsed["count"] == 2
    assert len(parsed["findings"]) == 2

    first = parsed["findings"][0]
    assert first["title"] == "YARA Match: Malware_Family_A"
    assert first["metadata"]["path"] == "/tmp/suspicious.exe"

    second = parsed["findings"][1]
    assert second["title"] == "YARA Match: Credential_Leak"


def test_yara_parser_empty_output(plugin_manager):
    parser = _load_yara_parser()

    parsed = parser.parse("")

    assert parsed["count"] == 0
    assert parsed["findings"] == []
    assert parsed["matches"] == []


def test_yara_parser_single_rule_without_target(plugin_manager):
    parser = _load_yara_parser()

    parsed = parser.parse("OnlyRule")

    assert parsed["count"] == 1

    finding = parsed["findings"][0]

    assert finding["metadata"]["rule"] == "OnlyRule"
    assert finding["metadata"]["path"] == "unknown_target"


def test_yara_executor_normalizes(plugin_manager):
    parser = _load_yara_parser()

    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text())

    normalized = executor._normalize_parsed_result(
        plugin,
        FIXTURE_PATH.read_text(),
        parsed,
    )

    assert normalized["count"] == 2
    assert len(normalized["findings"]) == 2
