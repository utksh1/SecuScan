"""Parser and contract coverage for plugins/nuclei (issue #1430)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager
from backend.secuscan.plugin_validator import PluginMetadataValidator
from plugins.nuclei.parser import parse

PLUGIN_ID = "nuclei"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"

@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager

def test_nuclei_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "Template Vulnerability Scan"
    assert plugin.category == "web"
    assert plugin.safety.get("level") == "intrusive"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None

    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids
    assert "preset" in field_ids
    assert "templates" in field_ids
    assert "severity" in field_ids

def test_nuclei_metadata_passes_validator():
    plugin_dir = Path(settings.plugins_dir) / PLUGIN_ID
    result = PluginMetadataValidator(plugin_dir).validate()
    assert result.valid, (
        "Plugin validation errors:\n"
        + "\n".join(e.display() for e in result.errors)
    )

def test_nuclei_build_command_renders_representative_target(plugin_manager):
    # Test default preset
    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": "http://127.0.0.1"},
    )
    assert command is not None
    assert command[0] == "nuclei"
    assert "-u" in command
    assert "http://127.0.0.1" in command
    assert "-nc" in command
    assert "-jsonl" in command

    # Test with custom templates and severity (representing the 'cves' preset mapped values)
    command_cves = plugin_manager.build_command(
        PLUGIN_ID,
        {
            "target": "http://127.0.0.1",
            "templates": "cves",
            "severity": "critical,high",
        },
    )
    assert command_cves is not None
    assert "-t" in command_cves
    assert "cves" in command_cves
    assert "-s" in command_cves
    assert "critical,high" in command_cves

    # Test custom options (templates & severity)
    custom_command = plugin_manager.build_command(
        PLUGIN_ID,
        {
            "target": "http://127.0.0.1",
            "templates": "vulnerabilities",
            "severity": "medium",
        },
    )
    assert custom_command is not None
    assert "-t" in custom_command
    assert "vulnerabilities" in custom_command
    assert "-s" in custom_command
    assert "medium" in custom_command

def test_nuclei_parser_fixture_produces_stable_findings():
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse(raw_output)

    assert "findings" in parsed
    findings = parsed["findings"]
    assert len(findings) == 2

    # First finding: git-config
    f1 = findings[0]
    assert f1["title"] == "Git Config File Disclosure"
    assert f1["category"] == "http"
    assert f1["severity"] == "medium"
    assert f1["description"] == "Git configuration file was disclosed."
    assert f1["remediation"] == "Restrict access to .git directory."
    assert f1["proof"] == "curl -X GET -H 'User-Agent: Nuclei' http://127.0.0.1/.git/config"
    assert f1["cvss"] == 5.0
    assert f1["cve"] == "CVE-2020-0000"
    assert f1["metadata"]["template_id"] == "git-config"
    assert f1["metadata"]["matched_at"] == "http://127.0.0.1/.git/config"
    assert f1["metadata"]["extracted_results"] == ["repositoryformatversion"]

    # Second finding: wordpress-xmlrpc
    f2 = findings[1]
    assert f2["title"] == "WordPress XML-RPC Enabled"
    assert f2["category"] == "http"
    assert f2["severity"] == "info"
    assert f2["description"] == "WordPress XML-RPC is enabled."
    assert f2["remediation"] == ""
    assert f2["proof"] == "curl -X POST http://127.0.0.1/xmlrpc.php"
    assert f2["cvss"] is None
    assert f2["cve"] is None
    assert f2["metadata"]["template_id"] == "wordpress-xmlrpc"
    assert f2["metadata"]["matched_at"] == "http://127.0.0.1/xmlrpc.php"
    assert f2["metadata"]["extracted_results"] == []

def test_nuclei_parser_empty_and_malformed_outputs():
    # Empty string
    parsed_empty = parse("")
    assert parsed_empty["findings"] == []

    # Malformed JSON line followed by a good one
    malformed_output = (
        "not json at all\n"
        '{"template-id":"git-config","info":{"name":"Git Config File Disclosure"}}\n'
        "{\n"  # incomplete JSON
    )
    parsed_malformed = parse(malformed_output)
    assert len(parsed_malformed["findings"]) == 1
    assert parsed_malformed["findings"][0]["metadata"]["template_id"] == "git-config"
    assert parsed_malformed["findings"][0]["title"] == "Git Config File Disclosure"

def test_nuclei_executor_normalizes_parsed_result(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse(raw_output)

    normalized = executor._normalize_parsed_result(
        plugin,
        raw_output,
        parsed,
    )

    assert normalized["count"] == 2
    assert len(normalized["findings"]) == 2

    for finding in normalized["findings"]:
        assert finding["title"]
        assert finding["category"]
        assert finding["severity"] in {"info", "low", "medium", "high", "critical"}
