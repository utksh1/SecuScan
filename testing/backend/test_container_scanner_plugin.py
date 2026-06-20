"""
Contract and parser tests for the container_scanner plugin.

These tests load the real plugins/container_scanner/metadata.json, validate
it through the project PluginMetadataValidator, render commands through the
real PluginManager, and call the real parser.py parse() function.

The assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #493: Add parser and contract coverage for plugin `container_scanner`
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager
from plugins.container_scanner.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "container_scanner"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_container_scanner_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_container_scanner_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_container_scanner_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.

    This test will fail if any required field is missing, the engine type or
    safety level is invalid, the command template references an undeclared field,
    or the checksum field is absent or malformed.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_container_scanner_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "container_scanner"


def test_container_scanner_engine_is_trivy():
    """Engine binary must be 'trivy' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "trivy"


def test_container_scanner_has_required_target_field():
    """Plugin must declare a required 'target' field for the Docker image."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_container_scanner_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_container_scanner_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_container_scanner_command_renders_with_image_target(setup_test_environment):
    """
    PluginManager must produce the exact Trivy command for a Docker image target.

    This test will fail if command_template in metadata.json is changed or if
    a placeholder becomes mismatched with the declared fields.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("container_scanner", {"target": "ubuntu:latest"})

    assert command is not None, "build_command returned None for valid inputs"
    assert command[0] == "trivy"
    assert "image" in command
    assert "-f" in command and "json" in command
    assert "--no-progress" in command
    assert "ubuntu:latest" in command


def test_container_scanner_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("container_scanner", {"target": "alpine:3.15"})

    assert command == [
        "trivy",
        "image",
        "-f",
        "json",
        "--no-progress",
        "alpine:3.15",
    ], f"Command template drift detected. Got: {command}"


def test_container_scanner_drops_target_token_when_absent(setup_test_environment):
    """
    When the 'target' field is omitted, the renderer drops the unresolved
    {target} token rather than emitting an empty or literal placeholder.

    This proves no image argument is fabricated when nothing is supplied, and
    contrasts with the populated render where the image is the final argument.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("container_scanner", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert rendered == ["trivy", "image", "-f", "json", "--no-progress"]

    populated = manager.build_command("container_scanner", {"target": "ubuntu:latest"})
    assert populated[-1] == "ubuntu:latest"
    assert len(populated) == len(rendered) + 1


def test_container_scanner_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load container_scanner from the real plugins dir."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("container_scanner")
    assert plugin is not None
    assert plugin.id == "container_scanner"
    assert plugin.name == "Container Scan (Trivy)"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_TRIVY_JSON_FIXTURE = json.dumps(
    {
        "Results": [
            {
                "Target": "ubuntu:latest (ubuntu 22.04)",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2024-1234",
                        "PkgName": "libssl1.1",
                        "Severity": "HIGH",
                        "Title": "OpenSSL buffer overflow in libssl1.1",
                        "Description": "Heap-based buffer overflow in libssl1.1 allows RCE.",
                        "InstalledVersion": "1.1.1f-1ubuntu2",
                        "FixedVersion": "1.1.1f-1ubuntu2.23",
                        "CVSS": {"nvd": {"V3Score": 9.8}},
                    },
                    {
                        "VulnerabilityID": "CVE-2024-5678",
                        "PkgName": "curl",
                        "Severity": "MEDIUM",
                        "Title": "SSRF in curl",
                        "Description": "Server-side request forgery in curl.",
                        "InstalledVersion": "7.81.0-1ubuntu1.13",
                        "FixedVersion": "7.81.0-1ubuntu1.16",
                        "CVSS": {},
                    },
                ],
            }
        ]
    }
)


def test_container_scanner_parser_returns_findings_key():
    """parse() must return a dict with a 'findings' key."""
    result = parse(_TRIVY_JSON_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result


def test_container_scanner_parser_extracts_both_vulnerabilities():
    """Parser must extract one finding per CVE entry in the Trivy output."""
    result = parse(_TRIVY_JSON_FIXTURE)
    assert len(result["findings"]) == 2


def test_container_scanner_parser_normalizes_high_severity():
    """'HIGH' Trivy severity must map to 'high' in the normalized findings."""
    result = parse(_TRIVY_JSON_FIXTURE)
    high_findings = [f for f in result["findings"] if f["severity"] == "high"]
    assert len(high_findings) == 1
    assert high_findings[0]["metadata"]["cve"] == "CVE-2024-1234"


def test_container_scanner_parser_normalizes_medium_severity():
    """'MEDIUM' Trivy severity must map to 'medium' in the normalized findings."""
    result = parse(_TRIVY_JSON_FIXTURE)
    medium_findings = [f for f in result["findings"] if f["severity"] == "medium"]
    assert len(medium_findings) == 1


def test_container_scanner_parser_finding_has_required_keys():
    """Each finding must contain title, category, severity, description, remediation, metadata."""
    result = parse(_TRIVY_JSON_FIXTURE)
    for finding in result["findings"]:
        for key in (
            "title",
            "category",
            "severity",
            "description",
            "remediation",
            "metadata",
        ):
            assert key in finding, f"Finding missing required key: {key}"


def test_container_scanner_parser_category_is_container_vulnerability():
    """Category must be 'Container Vulnerability' for all findings."""
    result = parse(_TRIVY_JSON_FIXTURE)
    for finding in result["findings"]:
        assert finding["category"] == "Container Vulnerability"


def test_container_scanner_parser_remediation_includes_package_name():
    """Remediation text must include the affected package name."""
    result = parse(_TRIVY_JSON_FIXTURE)
    ssl_finding = next(
        f for f in result["findings"] if f["metadata"]["package"] == "libssl1.1"
    )
    assert "libssl1.1" in ssl_finding["remediation"]


def test_container_scanner_parser_empty_output_returns_empty_findings():
    """Parser must handle empty input without raising."""
    result = parse("")
    assert result == {"findings": []}


def test_container_scanner_parser_handles_no_vulnerabilities():
    """Parser must return empty findings when Results has no vulnerabilities."""
    output = json.dumps({"Results": [{"Target": "alpine:3.15", "Vulnerabilities": []}]})
    result = parse(output)
    assert result["findings"] == []
