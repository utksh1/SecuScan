"""Parser and contract coverage for plugins/sqli_checker (issue #1534)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "sqli_checker"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_sqli_checker_parser():
    spec = importlib.util.spec_from_file_location("sqli_checker_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_sqli_checker_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None


def test_sqli_checker_build_command_renders_representative_target(plugin_manager):
    target = "https://vuln.example.com/page?id=1"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert target in " ".join(command) or any(target in arg for arg in command)


def test_sqli_checker_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_sqli_checker_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] >= 2
    assert len(parsed["findings"]) >= 2

    titles = [f["title"] for f in parsed["findings"]]
    assert "SQL Injection Found" in titles
    assert "Databases Enumerated" in titles

    sqli = next(f for f in parsed["findings"] if f["title"] == "SQL Injection Found")
    assert sqli["severity"] == "critical"
    assert "' OR 1=1 --" in sqli["metadata"]["payload"]


def test_sqli_checker_parser_extracts_multiple_payloads(plugin_manager):
    parser = _load_sqli_checker_parser()
    raw = "payload: ' OR 1=1 --\npayload: admin' --"
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 2
    payloads = [f["metadata"]["payload"] for f in parsed["findings"]]
    assert "' OR 1=1 --" in payloads
    assert "admin' --" in payloads


def test_sqli_checker_parser_limits_to_5_payloads(plugin_manager):
    parser = _load_sqli_checker_parser()
    raw = "payload: a\n" * 10
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) <= 5


def test_sqli_checker_parser_empty_output_returns_empty_findings(plugin_manager):
    parser = _load_sqli_checker_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0


def test_sqli_checker_parser_not_injectable_returns_info_finding(plugin_manager):
    parser = _load_sqli_checker_parser()
    raw = "Testing https://example.com...\nTarget does not appear injectable (not injectable)"
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["title"] == "No SQLi Detected"
    assert parsed["findings"][0]["severity"] == "info"


def test_sqli_checker_parser_extracts_database_names(plugin_manager):
    parser = _load_sqli_checker_parser()
    raw = "[info] available databases:\n[information_schema]\nwebapp_db"
    parsed = parser.parse(raw)

    db_finding = next(
        (f for f in parsed["findings"] if f["title"] == "Databases Enumerated"),
        None,
    )
    assert db_finding is not None
    assert "webapp_db" in db_finding["metadata"]["databases"]


def test_sqli_checker_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_sqli_checker_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(
        plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed
    )

    assert len(normalized["findings"]) >= 2
    assert all(f["title"] for f in normalized["findings"])
