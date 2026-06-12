"""Parser and contract coverage for plugins/url-fuzzer-2 (issue #515)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "url-fuzzer-2"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_url_fuzzer_2_parser():
    spec = importlib.util.spec_from_file_location("url_fuzzer_2_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_url_fuzzer_2_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "URL Fuzzer"
    assert plugin.category == "recon"
    assert plugin.safety.get("level") == "intrusive"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert {"target", "wordlist"} <= field_ids


def test_url_fuzzer_2_build_command_renders_representative_target(plugin_manager):
    target = "https://secuscan.in"
    wordlist = Path(settings.wordlists_dir) / "medium.txt"
    wordlist.write_text("admin\nlogin\n", encoding="utf-8")

    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": target, "wordlist": "medium"},
    )

    assert command is not None
    assert command[0] == "ffuf"
    assert command[1] == "-u"
    assert command[2] == f"{target}/FUZZ"
    wordlist_index = command.index("-w") + 1
    assert command[wordlist_index].endswith("medium.txt")
    assert "-mc" in command
    assert command[-1] == "-s"


def test_url_fuzzer_2_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_url_fuzzer_2_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3

    first = parsed["findings"][0]
    assert first["title"] == "URL Fuzzer Observation"
    assert first["category"] == "Recon"
    assert first["severity"] == "info"

    found = parsed["findings"][-1]
    assert found["severity"] == "low"
    assert "found" in found["description"].lower()


def test_url_fuzzer_2_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_url_fuzzer_2_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_url_fuzzer_2_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_url_fuzzer_2_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed)

    assert normalized["count"] == 3
    assert all(f["title"] for f in normalized["findings"])
