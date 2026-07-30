"""Parser and contract coverage for plugins/scapy_recon (issue #1532)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "scapy_recon"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_scapy_recon_parser():
    spec = importlib.util.spec_from_file_location("scapy_recon_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_scapy_recon_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Advanced Network Recon"
    assert plugin.category == "network"
    assert plugin.safety.get("level") == "safe"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert {"target", "type"} <= field_ids


def test_scapy_recon_build_command_renders_representative_target(plugin_manager):
    target = "192.168.1.0/24"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert "python3" in command
    assert "-c" in command
    assert "scapy" in " ".join(command)


def test_scapy_recon_build_command_includes_type_field(plugin_manager):
    target = "10.0.0.1"
    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": target, "type": "icmp_ping"},
    )

    assert command is not None
    assert "icmp_ping" in " ".join(command)


def test_scapy_recon_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_scapy_recon_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3
    assert len(parsed["hosts"]) == 3

    assert parsed["hosts"][0]["ip"] == "192.168.1.1"
    assert parsed["hosts"][0]["mac"] == "00:11:22:33:44:55"
    assert parsed["hosts"][1]["ip"] == "192.168.1.2"
    assert parsed["hosts"][1]["mac"] == "aa:bb:cc:dd:ee:ff"
    assert parsed["hosts"][2]["ip"] == "192.168.1.3"
    assert parsed["hosts"][2]["mac"] == "Unknown"

    first = parsed["findings"][0]
    assert first["title"] == "Live Host Discovered: 192.168.1.1"
    assert first["category"] == "Network Discovery"
    assert first["severity"] == "info"
    assert first["metadata"]["ip"] == "192.168.1.1"
    assert first["metadata"]["mac"] == "00:11:22:33:44:55"


def test_scapy_recon_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_scapy_recon_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["hosts"] == []


def test_scapy_recon_parser_ignores_non_up_lines(plugin_manager):
    parser = _load_scapy_recon_parser()
    raw = "scapy version 2.5.0 loaded.\nUP: 10.0.0.1 - ff:ee:dd:cc:bb:aa\nsome other output line"
    parsed = parser.parse(raw)

    assert parsed["count"] == 1
    assert parsed["hosts"][0]["ip"] == "10.0.0.1"
    assert parsed["hosts"][0]["mac"] == "ff:ee:dd:cc:bb:aa"


def test_scapy_recon_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_scapy_recon_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(
        plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed
    )

    assert normalized["count"] == 3
    assert len(normalized["findings"]) == 3
    assert normalized["findings"][0]["severity"] == "info"
    assert all(f["title"] for f in normalized["findings"])
