"""Parser and contract coverage for plugins/sqlmap (issue #1535)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "sqlmap"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_sqlmap_parser():
    spec = importlib.util.spec_from_file_location("sqlmap_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_sqlmap_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None


def test_sqlmap_build_command_renders_representative_target(plugin_manager):
    target = "https://vuln.example.com/page?id=1"
    command = plugin_manager.build_command(PLUGIN_ID, {"url": target})

    assert command is not None
    assert "sqlmap" in command
    assert target in " ".join(command) or any(target in arg for arg in command)


def test_sqlmap_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_sqlmap_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert len(parsed["findings"]) == 1

    finding = parsed["findings"][0]
    assert finding["title"] == "SQL Injection Vulnerability: q"
    assert finding["category"] == "Injection"
    assert finding["severity"] == "critical"
    assert finding["metadata"]["parameter"] == "q"
    assert "GET" in finding["metadata"]["type"]

    assert parsed["metadata"]["dbms"] == "MySQL 8.0"
    assert "PHP 8.1" in parsed["metadata"]["tech_stack"]


def test_sqlmap_parser_empty_output_returns_empty_findings(plugin_manager):
    parser = _load_sqlmap_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []


def test_sqlmap_parser_non_vulnerable_output_returns_empty_findings(plugin_manager):
    parser = _load_sqlmap_parser()
    raw = "sqlmap/1.8 running...\n[INFO] testing parameter 'q'\n[INFO] parameter 'q' does not appear to be injectable"
    parsed = parser.parse(raw)

    assert parsed["findings"] == []


def test_sqlmap_parser_unspecified_vulnerability_when_param_not_parsed(plugin_manager):
    parser = _load_sqlmap_parser()
    raw = "sqlmap running...\n[CRITICAL] The target is vulnerable to SQL injection but parameter could not be determined"
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["title"] == "Unspecified SQL Injection Vulnerability"
    assert parsed["findings"][0]["severity"] == "critical"


def test_sqlmap_parser_extracts_dbms_from_output(plugin_manager):
    parser = _load_sqlmap_parser()
    raw = "back-end DBMS: PostgreSQL 15.2"
    parsed = parser.parse(raw)

    assert parsed["metadata"]["dbms"] == "PostgreSQL 15.2"


def test_sqlmap_parser_extracts_tech_stack_from_output(plugin_manager):
    parser = _load_sqlmap_parser()
    raw = "web application technology: Apache 2.4, PHP 7.4"
    parsed = parser.parse(raw)

    assert parsed["metadata"]["tech_stack"] == "Apache 2.4, PHP 7.4"


def test_sqlmap_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_sqlmap_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(
        plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed
    )

    assert len(normalized["findings"]) == 1
    assert normalized["findings"][0]["severity"] == "critical"
    assert all(f["title"] for f in normalized["findings"])
