"""Parser and contract coverage for plugins/nmap (issue #1429)."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager
from backend.secuscan.plugin_validator import PluginMetadataValidator

PLUGIN_ID = "nmap"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"

def _load_nmap_parser():
    spec = importlib.util.spec_from_file_location("nmap_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager

def test_nmap_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Network Scanning"
    assert plugin.category == "network"
    assert plugin.safety.get("level") == "safe"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None

    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids
    assert "preset" in field_ids
    assert "ports" in field_ids
    assert "scan_type" in field_ids
    assert "service_detection" in field_ids
    assert "os_detection" in field_ids
    assert "timeout" in field_ids
    assert "safe_mode" in field_ids

def test_nmap_metadata_passes_validator():
    plugin_dir = Path(settings.plugins_dir) / PLUGIN_ID
    result = PluginMetadataValidator(plugin_dir).validate()
    assert result.valid, (
        "Plugin validation errors:\n"
        + "\n".join(e.display() for e in result.errors)
    )

def test_nmap_build_command_renders_representative_target(plugin_manager):
    # Test default preset
    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": "192.168.1.1"},
    )
    assert command is not None
    assert command[0] == "nmap"
    assert "-T3" in command
    assert "-sT" in command
    assert "--top-ports" in command
    assert "100" in command
    assert "192.168.1.1" in command

    # Test custom options (safe_mode = False, custom ports, service & OS detection)
    custom_command = plugin_manager.build_command(
        PLUGIN_ID,
        {
            "target": "10.0.0.1",
            "safe_mode": False,
            "ports": "22,80,443",
            "service_detection": True,
            "os_detection": True,
        },
    )
    assert custom_command is not None
    assert custom_command[0] == "nmap"
    assert "-T4" in custom_command
    assert "-sT" in custom_command
    assert "-p" in custom_command
    assert "22,80,443" in custom_command
    assert "-sV" in custom_command
    assert "-O" in custom_command
    assert "10.0.0.1" in custom_command

def test_nmap_parser_fixture_produces_stable_findings():
    parser = _load_nmap_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)

    assert len(parsed["findings"]) == 4
    assert parsed["open_ports"] == [22, 80, 443, 3306]
    assert parsed["services"] == ["http", "https", "mysql", "ssh"]
    assert parsed["os"] == "Linux 5.4.0-74-generic"

    # Verify high-risk severity mapping vs normal severity mapping
    findings_by_port = {
        finding["metadata"]["port"]: finding for finding in parsed["findings"]
    }

    # Port 22 (SSH) is high risk -> severity "low"
    assert findings_by_port[22]["severity"] == "low"
    assert "Version detected: OpenSSH 8.2p1" in findings_by_port[22]["description"]

    # Port 80 (HTTP) is standard -> severity "info"
    assert findings_by_port[80]["severity"] == "info"
    assert "Version detected: Apache httpd 2.4.41" in findings_by_port[80]["description"]

    # Port 443 (HTTPS) is standard -> severity "info"
    assert findings_by_port[443]["severity"] == "info"
    assert "Version detected" not in findings_by_port[443]["description"]

    # Port 3306 (MySQL) is high risk -> severity "low"
    assert findings_by_port[3306]["severity"] == "low"
    assert "Version detected: MySQL 8.0.25" in findings_by_port[3306]["description"]

def test_nmap_parser_heuristic_vulnerability():
    parser = _load_nmap_parser()

    # Case containing "VULNERABLE"
    vuln_output = (
        "PORT     STATE SERVICE\n"
        "80/tcp   open  http\n"
        "|_http-vuln-cve2017-5638: VULNERABLE\n"
    )
    parsed = parser.parse(vuln_output)
    assert len(parsed["findings"]) == 2  # 1 for port 80 + 1 for vulnerability heuristic
    vuln_finding = next(
        f for f in parsed["findings"] if f["category"] == "Vulnerability"
    )
    assert vuln_finding["title"] == "Potential Vulnerability/Exploit Detected"
    assert vuln_finding["severity"] == "high"

    # Case containing "Exploit"
    exploit_output = (
        "PORT     STATE SERVICE\n"
        "80/tcp   open  http\n"
        "|_exploit-results: Exploit available\n"
    )
    parsed_exploit = parser.parse(exploit_output)
    assert len(parsed_exploit["findings"]) == 2
    exploit_finding = next(
        f for f in parsed_exploit["findings"] if f["category"] == "Vulnerability"
    )
    assert exploit_finding["severity"] == "high"

def test_nmap_parser_empty_and_malformed_outputs():
    parser = _load_nmap_parser()

    # Empty string
    parsed_empty = parser.parse("")
    assert parsed_empty["findings"] == []
    assert parsed_empty["open_ports"] == []
    assert parsed_empty["services"] == []
    assert parsed_empty["os"] == "Unknown"

    # Malformed / no match string
    parsed_malformed = parser.parse("Nmap scan report for target\nSome unparseable lines here.")
    assert parsed_malformed["findings"] == []
    assert parsed_malformed["open_ports"] == []
    assert parsed_malformed["services"] == []
    assert parsed_malformed["os"] == "Unknown"

def test_nmap_executor_normalizes_parsed_result(plugin_manager):
    parser = _load_nmap_parser()
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parser.parse(raw_output)

    normalized = executor._normalize_parsed_result(
        plugin,
        raw_output,
        parsed,
    )

    assert normalized["count"] == 4
    assert len(normalized["findings"]) == 4

    for finding in normalized["findings"]:
        assert finding["title"]
        assert finding["category"]
        assert finding["severity"] in {"info", "low", "medium", "high", "critical"}
