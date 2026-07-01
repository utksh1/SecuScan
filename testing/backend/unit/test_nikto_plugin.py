"""Parser and contract coverage for plugins/nikto (issue #1428)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager
from plugins.nikto.parser import parse

PLUGIN_ID = "nikto"
JSON_FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.json"
TXT_FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def test_nikto_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Nikto"
    assert plugin.category == "web"
    assert plugin.safety.get("level") == "intrusive"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids
    assert "port" in field_ids
    assert "tuning" in field_ids


def test_nikto_build_command_renders_representative_target(plugin_manager):
    target = "127.0.0.1"
    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": target, "port": "80,443", "tuning": "123"},
    )
    assert command is not None
    assert command[0] == "nikto"
    # Ensure port and tuning codes are correctly placed in command list
    assert "-h" in command
    assert target in command
    assert "-port" in command
    assert "80,443" in command
    assert "-Tuning" in command
    assert "123" in command


def test_nikto_parser_json_fixture_produces_stable_findings():
    raw_output = JSON_FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse(raw_output)

    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3
    assert parsed["target"] == "example.com"
    assert parsed["raw"] is None

    # First finding (Retrieved via header: 1.1 google.)
    f1 = parsed["findings"][0]
    assert f1["title"] == "Retrieved via header: 1.1 google."
    assert f1["category"] == "Security Headers"  # matches because of "header" in msg
    assert f1["severity"] == "medium"  # default severity
    assert f1["proof"] == "GET /"
    assert f1["metadata"]["id"] == "999986"

    # Second finding (The X-Content-Type-Options header is not set. See http://cve.mitre.org)
    f2 = parsed["findings"][1]
    assert f2["title"] == "The X-Content-Type-Options header is not set. See http://cve.mitre.org"
    assert f2["category"] == "Security Headers"
    assert f2["severity"] == "medium"
    assert f2["proof"] == "GET /robots.txt"
    assert f2["metadata"]["references"] == "https://example.com/reference"

    # Third finding (Default credential admin/admin found.)
    f3 = parsed["findings"][2]
    assert f3["title"] == "Default credential admin/admin found."
    assert f3["category"] == "Web Vulnerability"
    assert f3["severity"] == "high"
    assert f3["proof"] == "POST /login"
    assert f3["metadata"]["id"] == "500000"


def test_nikto_parser_text_fixture_produces_stable_findings():
    raw_output = TXT_FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse(raw_output)

    # Let's inspect findings
    # Banners should be skipped, target IP/hostname/port/server mapped.
    # Server banner is parsed as a finding ("Server banner disclosed").
    # Plus /admin.php, robots.txt, /index.php, /login.php -> 4 more findings.
    # Plus "1 host(s) tested" parsed as a finding -> 1 more finding.
    # Total findings: 6
    assert parsed["count"] == 6
    assert len(parsed["findings"]) == 6

    # Check metadata
    assert parsed["metadata"]["target_ip"] == "192.168.1.1"
    assert parsed["metadata"]["target_hostname"] == "example.com"
    assert parsed["metadata"]["target_port"] == "80"

    # Check server finding
    server_finding = parsed["findings"][0]
    assert server_finding["title"] == "Server banner disclosed"
    assert server_finding["category"] == "Information Disclosure"
    assert server_finding["severity"] == "low"
    assert server_finding["proof"] == "Server:             Apache/2.4.41"

    # Check Admin login finding
    admin_finding = parsed["findings"][1]
    assert admin_finding["title"] == "Admin login page found."
    assert admin_finding["category"] == "Web Vulnerability"
    assert admin_finding["severity"] == "medium"
    assert admin_finding["proof"] == "/admin.php: Admin login page found."
    assert admin_finding["metadata"]["path"] == "/admin.php"

    # Check robots.txt finding (no path in key-split but is a line finding)
    robots_finding = parsed["findings"][2]
    assert robots_finding["title"] == "robots.txt contains 1 entry which should be manually viewed."
    assert robots_finding["category"] == "Web Vulnerability"
    assert robots_finding["severity"] == "medium"
    assert robots_finding["proof"] == "robots.txt contains 1 entry which should be manually viewed."
    assert robots_finding["metadata"]["path"] is None

    # Check references in finding
    ref_finding = parsed["findings"][3]
    assert ref_finding["title"] == "Powered by header disclosed. See"
    assert ref_finding["category"] == "Security Headers"  # contains "header"
    assert ref_finding["severity"] == "low"
    assert ref_finding["metadata"]["references"] == "http://cve.mitre.org"

    # Check outdated finding
    outdated_finding = parsed["findings"][4]
    assert outdated_finding["title"] == "Apache/2.4.41 appears to be outdated."
    assert outdated_finding["category"] == "Web Vulnerability"
    assert outdated_finding["severity"] == "high"  # due to "outdated"

    # Check 1 host(s) tested finding
    host_tested_finding = parsed["findings"][5]
    assert host_tested_finding["title"] == "1 host(s) tested"


def test_nikto_parser_empty_output_is_deterministic():
    parsed = parse("")
    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["metadata"] == {}
    assert parsed["summary"] == []
    assert parsed["raw"] == ""


def test_nikto_parser_malformed_json_falls_back_to_text():
    # If the output starts with some text and contains invalid JSON
    # or just contains incomplete JSON, it should fall back to text parsing.
    malformed = """
    {"vulnerabilities": [
        {"id": "1", "msg": "Test"
    """
    parsed = parse(malformed)
    # Since there are no findings starting with "+ ", it should parse nothing but not crash
    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["raw"] == malformed


def test_nikto_parser_json_variants():
    # 1. Direct list of vulnerabilities
    vlist = [
        {"msg": "Vuln 1", "url": "/vuln1"},
        {"msg": "Vuln 2", "url": "/vuln2"}
    ]
    parsed = parse(json.dumps(vlist))
    assert parsed["count"] == 2
    assert parsed["findings"][0]["title"] == "Vuln 1"

    # 2. Dict with findings key
    vfindings = {"findings": [{"msg": "Vuln A"}, {"msg": "Vuln B"}]}
    parsed = parse(json.dumps(vfindings))
    assert parsed["count"] == 2
    assert parsed["findings"][1]["title"] == "Vuln B"

    # 3. Host nested vulnerabilities
    vnested = {
        "host_data": {
            "vulnerabilities": [
                {"msg": "Nested Vuln"}
            ]
        }
    }
    parsed = parse(json.dumps(vnested))
    assert parsed["count"] == 1
    assert parsed["findings"][0]["title"] == "Nested Vuln"


def test_nikto_parser_severity_and_remediation_heuristics():
    # Test specific high/medium/low keywords
    v_high = [{"msg": "Target has outdated sql injection component"}]  # contains "outdated" -> triggers Upgrade
    p_high = parse(json.dumps(v_high))
    assert p_high["findings"][0]["severity"] == "high"
    assert "Upgrade" in p_high["findings"][0]["remediation"]

    v_med = [{"msg": "Missing x-frame-options header in response"}]
    p_med = parse(json.dumps(v_med))
    assert p_med["findings"][0]["severity"] == "medium"
    assert "security header" in p_med["findings"][0]["remediation"]

    v_low = [{"msg": "server leaks detailed version banner"}]
    p_low = parse(json.dumps(v_low))
    assert p_low["findings"][0]["severity"] == "low"
    assert "Review" in p_low["findings"][0]["remediation"]

    v_other = [{"msg": "some generic HTTP methods allowed"}]
    p_other = parse(json.dumps(v_other))
    assert p_other["findings"][0]["severity"] == "medium"
    assert "Disable" in p_other["findings"][0]["remediation"]


def test_nikto_executor_normalizes_parsed_result(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    raw_output = JSON_FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse(raw_output)

    normalized = executor._normalize_parsed_result(
        plugin,
        raw_output,
        parsed,
    )
    assert normalized["count"] == 3
    assert len(normalized["findings"]) == 3
    assert all(f["title"] for f in normalized["findings"])
    assert all(f["category"] for f in normalized["findings"])
