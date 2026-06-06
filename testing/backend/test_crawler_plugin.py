"""
Contract and parser tests for the crawler plugin.

These tests load the real plugins/crawler/metadata.json, validate it through
the project PluginMetadataValidator, render commands through the real
PluginManager, and call the real parser.py parse() function.

Assertions are tied to the actual plugin contract: if metadata.json,
the command template, or parser.py drift, these tests will fail.

Related to issue #494: Add parser and contract coverage for plugin `crawler`
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
from plugins.crawler.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "crawler"
PLUGINS_DIR = REPO_ROOT / "plugins"


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_crawler_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_crawler_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    raw = (PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_crawler_passes_validator():
    """
    The full PluginMetadataValidator must accept the plugin without errors.

    This will fail if any required field is missing, the engine type or safety
    level is invalid, the command template references an undeclared field, or
    the checksum field is absent or malformed.
    """
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, (
        "Plugin validation errors:\n"
        + "\n".join(e.display() for e in result.errors)
    )


def test_crawler_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["id"] == "crawler"


def test_crawler_engine_is_katana():
    """Engine binary must be 'katana' -- update this if the underlying tool changes."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "katana"


def test_crawler_has_required_target_field():
    """Plugin must declare a required 'target' field for the URL to crawl."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


def test_crawler_target_field_requires_http_url():
    """The 'target' field must validate for an HTTP(S) URL."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    target_validation = fields["target"].get("validation", {})
    pattern = target_validation.get("pattern", "")
    assert "https?" in pattern or "http" in pattern, (
        "target field must validate for HTTP(S) URL format"
    )


def test_crawler_has_optional_depth_field_with_default():
    """Plugin must declare an optional 'depth' field with a default of 2."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}
    assert "depth" in fields, "Missing optional field: depth"
    assert fields["depth"].get("default") == 2, "depth default must be 2"


def test_crawler_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["output"]["parser"] == "custom"


def test_crawler_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_crawler_requires_consent():
    """Web crawling is intrusive and must require user consent."""
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    assert data["safety"]["requires_consent"] is True
    assert data["safety"]["consent_message"], "consent_message must not be empty"


# ---------------------------------------------------------------------------
# Command rendering tests via real PluginManager
# ---------------------------------------------------------------------------


def test_crawler_command_renders_with_target(setup_test_environment):
    """
    PluginManager must produce the correct katana command for a crawl target.

    This test will fail if command_template in metadata.json changes or a
    placeholder becomes mismatched.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("crawler", {"target": "https://example.com"})

    assert command is not None, "build_command returned None for valid inputs"
    assert "katana" in command
    assert "-u" in command
    assert "https://example.com" in command
    assert "-silent" in command


def test_crawler_command_uses_default_depth(setup_test_environment):
    """
    When 'depth' is omitted, the command must use the default value from
    metadata.json (2).
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("crawler", {"target": "https://example.com"})

    assert command is not None
    assert "-depth" in command
    depth_idx = command.index("-depth")
    assert command[depth_idx + 1] == "2", (
        f"Default depth must be '2'. Got: {command[depth_idx + 1]}"
    )


def test_crawler_command_full_token_sequence(setup_test_environment):
    """Full rendered command must exactly match the command_template token sequence."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("crawler", {"target": "https://secuscan.in"})

    assert command == ["katana", "-u", "https://secuscan.in", "-depth", "2", "-silent"], (
        f"Command template drift detected. Got: {command}"
    )


def test_crawler_command_respects_explicit_depth(setup_test_environment):
    """When 'depth' is explicitly provided, it must override the default."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("crawler", {"target": "https://example.com", "depth": 5})

    assert command is not None
    depth_idx = command.index("-depth")
    assert command[depth_idx + 1] == "5", (
        f"Explicit depth=5 must override default. Got: {command[depth_idx + 1]}"
    )


<<<<<<< HEAD
def test_crawler_drops_target_token_when_absent(setup_test_environment):
    """
    When the 'target' field is omitted, the renderer drops the unresolved
    {target} token rather than emitting an empty value or literal placeholder.
    The default depth scaffold is preserved.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    rendered = manager.build_command("crawler", {})

    assert rendered is not None
    assert not any("{" in token for token in rendered), "Unresolved placeholder leaked"
    assert rendered == ["katana", "-u", "-depth", "2", "-silent"]

    populated = manager.build_command("crawler", {"target": "https://example.com"})
    assert "https://example.com" in populated
    assert len(populated) == len(rendered) + 1
=======
def test_crawler_requires_target_field(setup_test_environment):
    """build_command must return None when the required 'target' field is absent."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    result = manager.build_command("crawler", {})
    assert result is None
>>>>>>> ac1eabf (test(crawler): add contract and parser coverage for crawler plugin)


def test_crawler_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must successfully load crawler from the real plugins directory."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("crawler")
    assert plugin is not None
    assert plugin.id == "crawler"
    assert plugin.name == "Crawler"


# ---------------------------------------------------------------------------
# Parser contract tests against the real parser.py
# ---------------------------------------------------------------------------

_CRAWLER_OUTPUT_FIXTURE = (
    "https://example.com/\n"
    "https://example.com/about\n"
    "https://example.com/admin [found]\n"
    "https://example.com/login?redirect=http://evil.com [warning] [detected]\n"
    "https://example.com/api/v1/users [exposed]\n"
    "https://example.com/internal/debug [critical] [injection]\n"
)


def test_crawler_parser_returns_required_keys():
    """parse() must return a dict with 'findings', 'count', and 'items' keys."""
    result = parse(_CRAWLER_OUTPUT_FIXTURE)
    assert isinstance(result, dict)
    assert "findings" in result
    assert "count" in result
    assert "items" in result


def test_crawler_parser_count_matches_findings():
    """'count' must equal len(findings)."""
    result = parse(_CRAWLER_OUTPUT_FIXTURE)
    assert result["count"] == len(result["findings"])


def test_crawler_parser_finding_has_required_keys():
    """Each finding must have title, category, severity, description, remediation, metadata."""
    result = parse(_CRAWLER_OUTPUT_FIXTURE)
    assert result["findings"], "Expected at least one finding"
    for finding in result["findings"]:
        for key in ("title", "category", "severity", "description", "remediation", "metadata"):
            assert key in finding, f"Finding missing key: {key}"


def test_crawler_parser_critical_and_injection_raise_to_high():
    """Lines containing 'critical' or 'injection' must be classified as 'high' severity."""
    result = parse(_CRAWLER_OUTPUT_FIXTURE)
    high_findings = [
        f for f in result["findings"]
        if "critical" in f["description"].lower() or "injection" in f["description"].lower()
    ]
    assert high_findings, "Expected at least one high-severity finding"
    for finding in high_findings:
        assert finding["severity"] == "high"


def test_crawler_parser_exposed_or_found_is_at_least_low():
    """Lines containing 'exposed', 'found', or 'detected' must be at least 'low' severity."""
    result = parse(_CRAWLER_OUTPUT_FIXTURE)
    flagged = [
        f for f in result["findings"]
        if any(kw in f["description"].lower() for kw in ("exposed", "found", "detected"))
    ]
    assert flagged, "Expected at least one low-severity finding from flagged keywords"
    for finding in flagged:
        assert finding["severity"] in ("low", "high")


def test_crawler_parser_items_list_matches_non_empty_lines():
    """items must contain each non-empty line from the output."""
    result = parse(_CRAWLER_OUTPUT_FIXTURE)
    expected_lines = [l.strip() for l in _CRAWLER_OUTPUT_FIXTURE.splitlines() if l.strip()]
    assert result["items"] == expected_lines


def test_crawler_parser_empty_output():
    """Parser must handle empty input without raising and return empty findings."""
    result = parse("")
    assert result["findings"] == []
    assert result["count"] == 0
    assert result["items"] == []


def test_crawler_parser_preserves_raw_line_in_metadata():
    """Each finding's metadata.raw must match the original output line."""
    single_line = "https://example.com/admin [found]\n"
    result = parse(single_line)
    assert result["findings"]
    assert result["findings"][0]["metadata"]["raw"] == "https://example.com/admin [found]"
