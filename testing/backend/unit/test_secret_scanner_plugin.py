"""Parser and contract coverage for plugins/secret_scanner (issue #1533)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "secret_scanner"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_secret_scanner_parser():
    spec = importlib.util.spec_from_file_location("secret_scanner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_secret_scanner_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None


def test_secret_scanner_build_command_renders_representative_target(plugin_manager):
    target = "https://github.com/example/repo"
    command = plugin_manager.build_command(PLUGIN_ID, {"target": target})

    assert command is not None
    assert "gitleaks" in " ".join(command) or any("git" in arg for arg in command)


def test_secret_scanner_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_secret_scanner_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 2
    assert len(parsed["findings"]) == 2

    first = parsed["findings"][0]
    assert first["title"] == "Secret Leak: github-pat in src/config/credentials.py"
    assert first["category"] == "Credential Leak"
    assert first["severity"] == "critical"
    assert first["metadata"]["file"] == "src/config/credentials.py"
    assert first["metadata"]["line"] == 12

    second = parsed["findings"][1]
    assert second["title"] == "Secret Leak: aws-access-key in deployments/env"
    assert second["severity"] == "critical"


def test_secret_scanner_parser_empty_json_array_returns_empty_findings(plugin_manager):
    parser = _load_secret_scanner_parser()
    parsed = parser.parse("[]")

    assert parsed["findings"] == []
    assert parsed["count"] == 0


def test_secret_scanner_parser_no_leaks_message_returns_empty_findings(plugin_manager):
    parser = _load_secret_scanner_parser()
    parsed = parser.parse("No leaks found.")

    assert parsed["findings"] == []
    assert parsed["count"] == 0


def test_secret_scanner_parser_malformed_json_returns_empty_findings(plugin_manager):
    parser = _load_secret_scanner_parser()
    parsed = parser.parse("not-valid-json {{{{broken")

    assert parsed["findings"] == []
    assert parsed["count"] == 0


def test_secret_scanner_parser_uses_default_rule_id_when_missing(plugin_manager):
    parser = _load_secret_scanner_parser()
    raw = '[{"File": "src/main.py", "StartLine": 1}]'
    parsed = parser.parse(raw)

    assert len(parsed["findings"]) == 1
    assert (
        parsed["findings"][0]["title"] == "Secret Leak: Secret Detected in src/main.py"
    )


def test_secret_scanner_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_secret_scanner_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(
        plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed
    )

    assert normalized["count"] == 2
    assert len(normalized["findings"]) == 2
    assert normalized["findings"][0]["severity"] == "critical"
    assert all(f["title"] for f in normalized["findings"])


def test_secret_scanner_parser_defaults_file_line_and_offender(plugin_manager):
    parser = _load_secret_scanner_parser()

    raw = '[{"RuleID": "generic-secret"}]'
    parsed = parser.parse(raw)

    assert parsed["count"] == 1

    finding = parsed["findings"][0]
    assert finding["title"] == "Secret Leak: generic-secret in Unknown"
    assert finding["metadata"]["file"] == "Unknown"
    assert finding["metadata"]["line"] == 0
    assert finding["metadata"]["offender"] == "****"


def test_secret_scanner_parser_defaults_rule_when_missing_allows_metadata(
    plugin_manager,
):
    parser = _load_secret_scanner_parser()

    raw = '[{"File":"config.env","StartLine":8,"Offender":"SECRET_VALUE"}]'
    parsed = parser.parse(raw)

    assert parsed["count"] == 1

    finding = parsed["findings"][0]
    assert finding["title"] == "Secret Leak: Secret Detected in config.env"
    assert finding["metadata"]["rule"] == "Secret Detected"
    assert finding["metadata"]["offender"] == "SECRET_VALUE"


def test_secret_scanner_parser_mixed_complete_and_partial_entries(plugin_manager):
    parser = _load_secret_scanner_parser()

    raw = """
    [
      {
        "RuleID":"github-pat",
        "File":"src/app.py",
        "StartLine":10,
        "Offender":"ghp_test"
      },
      {
        "RuleID":"generic-secret"
      }
    ]
    """

    parsed = parser.parse(raw)

    assert parsed["count"] == 2

    assert parsed["findings"][0]["metadata"]["file"] == "src/app.py"

    assert parsed["findings"][1]["metadata"]["file"] == "Unknown"
    assert parsed["findings"][1]["metadata"]["line"] == 0
    assert parsed["findings"][1]["metadata"]["offender"] == "****"
