"""Parser and contract coverage for plugins/metasploit."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "metasploit"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"

def _load_metasploit_parser():
    spec = importlib.util.spec_from_file_location("metasploit_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager

def test_metasploit_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Exploitation Connector"
    assert plugin.category == "expert"
    assert plugin.safety.get("level") == "exploit"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert {"target", "module", "payload"} <= field_ids

def test_metasploit_build_command(plugin_manager):
    command = plugin_manager.build_command(
        PLUGIN_ID,
        {
            "target": "10.0.0.1",
            "module": "exploit/multi/handler",
            "payload": "generic/shell_reverse_tcp"
        }
    )
    assert command is not None
    assert command == [
        "msfconsole",
        "-q",
        "-x",
        "use exploit/multi/handler; set RHOSTS 10.0.0.1; set PAYLOAD generic/shell_reverse_tcp; run; exit"
    ]

def test_metasploit_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_metasploit_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)
    assert parsed["count"] == 2
    assert len(parsed["findings"]) == 2

    vuln_match = next(f for f in parsed["findings"] if f["title"] == "Metasploit Vulnerability Match")
    assert vuln_match["severity"] == "high"
    assert vuln_match["description"] == "MS17-010 EternalBlue Windows SMB Remote Code Execution"
    assert vuln_match["metadata"]["line"] == "Found vulnerability: MS17-010 EternalBlue Windows SMB Remote Code Execution"

    session_match = next(f for f in parsed["findings"] if f["title"] == "Metasploit Session Opened")
    assert session_match["severity"] == "critical"
    assert session_match["description"] == "Meterpreter session 2 opened."
    assert session_match["metadata"]["session_type"].lower() == "meterpreter"
    assert session_match["metadata"]["session_id"] == "2"

def test_metasploit_parser_command_shell_session(plugin_manager):
    parser = _load_metasploit_parser()
    output = "Command Shell session 5 opened"
    parsed = parser.parse(output)

    assert parsed["count"] == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "Metasploit Session Opened"
    assert finding["severity"] == "critical"
    assert finding["description"] == "Command Shell session 5 opened."
    assert finding["metadata"]["session_type"].lower() == "command shell"
    assert finding["metadata"]["session_id"] == "5"

def test_metasploit_parser_exploit_failed_with_no_findings(plugin_manager):
    parser = _load_metasploit_parser()
    output = "Exploit failed: connection timeout"
    parsed = parser.parse(output)

    assert parsed["count"] == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "Metasploit Attempt Failed"
    assert finding["severity"] == "medium"
    assert finding["description"] == "Exploit execution did not open a session."

def test_metasploit_parser_exploit_failed_ignored_with_findings(plugin_manager):
    parser = _load_metasploit_parser()
    output = "Found vulnerability: CVE-2023-1234\nExploit failed"
    parsed = parser.parse(output)

    assert parsed["count"] == 1
    assert parsed["findings"][0]["title"] == "Metasploit Vulnerability Match"

def test_metasploit_parser_empty_output(plugin_manager):
    parser = _load_metasploit_parser()
    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0

def test_metasploit_parser_malformed_output(plugin_manager):
    parser = _load_metasploit_parser()

    # Random text that doesn't trigger session, vulnerability, or failure matches
    parsed_noise = parser.parse("No fail, no session, no vulnerability. Just status: active.")
    assert parsed_noise["findings"] == []
    assert parsed_noise["count"] == 0

    # Incomplete matches with exploit failed
    parsed_partial = parser.parse("meterpreter session opened but no id\nexploit failed")
    assert parsed_partial["count"] == 1
    assert parsed_partial["findings"][0]["title"] == "Metasploit Attempt Failed"

def test_metasploit_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_metasploit_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    parsed = parser.parse(FIXTURE_PATH.read_text(encoding="utf-8"))
    normalized = executor._normalize_parsed_result(plugin, FIXTURE_PATH.read_text(encoding="utf-8"), parsed)

    assert normalized["count"] == 2
    assert all(f["title"] for f in normalized["findings"])
