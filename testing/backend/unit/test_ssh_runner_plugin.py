"""Parser and contract coverage for plugins/ssh_runner (issue #1536)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "ssh_runner"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_ssh_runner_parser():
    spec = importlib.util.spec_from_file_location("ssh_runner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_ssh_runner_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None


def test_ssh_runner_build_command_renders_representative_target(plugin_manager):
    target = "user@server.example.com"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert target in " ".join(command) or any(target in arg for arg in command)


def test_ssh_runner_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_ssh_runner_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert len(parsed["findings"]) == 1

    finding = parsed["findings"][0]
    assert finding["title"] == "SSH Command Executed Successfully"
    assert finding["category"] == "Remote Execution"
    assert finding["severity"] == "info"
    assert finding["metadata"]["raw_output"] == raw_output


def test_ssh_runner_parser_empty_output_produces_info_finding(plugin_manager):
    parser = _load_ssh_runner_parser()
    parsed = parser.parse("")

    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["severity"] == "info"
    assert parsed["findings"][0]["title"] == "SSH Command Executed Successfully"


def test_ssh_runner_parser_permission_denied_adjusts_severity(plugin_manager):
    parser = _load_ssh_runner_parser()
    raw = "Connecting to user@server.example.com...\nPermission denied (publickey)."
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["title"] == "SSH Execution Failed / Error"
    assert parsed["findings"][0]["severity"] == "medium"


def test_ssh_runner_parser_connection_refused_adjusts_severity(plugin_manager):
    parser = _load_ssh_runner_parser()
    raw = "ssh: connect to host server.example.com port 22: Connection refused"
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["severity"] == "medium"
    assert parsed["findings"][0]["title"] == "SSH Execution Failed / Error"


def test_ssh_runner_parser_combined_error_conditions(plugin_manager):
    parser = _load_ssh_runner_parser()
    raw = "Permission denied and Connection refused"
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["severity"] == "medium"


def test_ssh_runner_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_ssh_runner_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(
        plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed
    )

    assert len(normalized["findings"]) == 1
    assert all(f["title"] for f in normalized["findings"])
