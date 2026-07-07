"""Parser and contract coverage for plugins/zap_scanner (issues #521, #1419).

Issue #1419 regression: the ZAP plugin must not surface placeholder / stub
scan output as genuine findings.  The parser only accepts lines that begin
with ``WARN-NEW:`` or ``FAIL-NEW:`` (the real ZAP baseline format).  Any
other content — including free-text summaries, connector stubs, or generic
progress messages — must parse to zero findings.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from backend.secuscan.config import settings
from backend.secuscan.executor import executor
from backend.secuscan.plugins import PluginManager, _PLACEHOLDER_PLUGIN_IDS

PLUGIN_ID = "zap_scanner"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"

# ---------------------------------------------------------------------------
# Placeholder strings that must NEVER be treated as real scan output.
# Each entry is a string that a placeholder / stub / connector might emit.
# The parser must produce zero findings for every one of them.
# ---------------------------------------------------------------------------
_PLACEHOLDER_OUTPUTS = [
    # Generic "scan running" progress messages
    "ZAP scan in progress...",
    "Running ZAP baseline scan",
    "Scanning target with OWASP ZAP",
    # Connector / stub responses
    "ZAP connector placeholder scan",
    "placeholder",
    "stub output",
    # Docker-unavailable fallback messages
    "Docker not available. Skipping ZAP scan.",
    "ZAP scan skipped: docker binary not found",
    # Generic status-only lines (no WARN-NEW / FAIL-NEW prefix)
    "PASS: Passive scan completed",
    "INFO: Starting ZAP baseline scan",
    "Total of 0 URLs",
    # Free-text summaries that look useful but aren't ZAP alert lines
    "No issues found",
    "Scan complete. 0 alerts.",
    "ZAP baseline scan completed successfully.",
    # Whitespace / empty
    "",
    "   ",
    "\n\n",
]


def _load_zap_scanner_parser():
    spec = importlib.util.spec_from_file_location("zap_scanner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


# ===========================================================================
# Existing parser and metadata tests (issue #521) — must all continue to pass
# ===========================================================================

def test_zap_scanner_metadata_loads_through_validation_path(plugin_manager):
    plugin = plugin_manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "DAST Web Proxy (ZAP)"
    assert plugin.category == "vulnerability"
    assert plugin.safety.get("level") == "exploit"
    assert plugin.safety.get("requires_consent") is True

    schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
    assert schema is not None

    field_ids = {field["id"] for field in schema["fields"]}
    assert "target" in field_ids


def test_zap_scanner_build_command_renders_representative_target(plugin_manager):
    target = "https://secuscan.in"

    command = plugin_manager.build_command(
        PLUGIN_ID,
        {"target": target},
    )

    assert command is not None
    assert command[0] == "docker"
    assert command[1] == "run"
    assert "--rm" in command
    assert "ghcr.io/zaproxy/zaproxy:stable" in command
    assert "zap-baseline.py" in command
    assert "-t" in command
    assert target in command


def test_zap_scanner_parser_fixture_produces_stable_findings(plugin_manager):
    parser = _load_zap_scanner_parser()
    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")

    parsed = parser.parse(raw_output)

    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3

    first = parsed["findings"][0]
    assert first["title"] == "Recon/Scan Observation"
    assert first["severity"] == "low"
    assert "X-Frame-Options" in first["description"]

    second = parsed["findings"][1]
    assert second["severity"] == "high"
    assert "SQL Injection" in second["description"]

    third = parsed["findings"][2]
    assert third["severity"] == "low"


def test_zap_scanner_parser_empty_output_is_deterministic(plugin_manager):
    parser = _load_zap_scanner_parser()

    parsed = parser.parse("")

    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["items"] == []


def test_zap_scanner_executor_normalizes_parser_fixture(plugin_manager):
    parser = _load_zap_scanner_parser()

    plugin = plugin_manager.get_plugin(PLUGIN_ID)
    assert plugin is not None

    raw_output = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parser.parse(raw_output)

    normalized = executor._normalize_parsed_result(
        plugin,
        raw_output,
        parsed,
    )

    assert normalized["count"] == 3
    assert len(normalized["findings"]) == 3

    assert all(f["title"] for f in normalized["findings"])
    assert all(f["category"] for f in normalized["findings"])


# ===========================================================================
# Regression tests: placeholder / stub output must not produce findings
# (issue #1419)
# ===========================================================================

class TestZAPParserRejectsPlaceholderOutput:
    """The parser must not accept free-text or stub strings as findings.

    Only lines prefixed with ``WARN-NEW:`` or ``FAIL-NEW:`` are valid ZAP
    baseline alert lines.  Anything else must produce zero findings so that
    a placeholder connector or a Docker-unavailable fallback cannot silently
    inflate the finding count.
    """

    def test_placeholder_outputs_produce_no_findings(self):
        """Every known placeholder / stub string must parse to zero findings."""
        parser = _load_zap_scanner_parser()
        for stub in _PLACEHOLDER_OUTPUTS:
            result = parser.parse(stub)
            assert result["count"] == 0, (
                f"Parser accepted placeholder output as findings: {stub!r} "
                f"→ count={result['count']}, items={result['items']}"
            )
            assert result["findings"] == [], (
                f"Parser returned non-empty findings for placeholder: {stub!r}"
            )

    def test_plain_pass_line_is_not_a_finding(self):
        """PASS: lines appear in real ZAP output but are not alerts."""
        parser = _load_zap_scanner_parser()
        result = parser.parse("PASS: Passive scan completed\nPASS: No issues found")
        assert result["count"] == 0
        assert result["findings"] == []

    def test_info_line_is_not_a_finding(self):
        """INFO: lines are diagnostic noise, not security alerts."""
        parser = _load_zap_scanner_parser()
        result = parser.parse("INFO: Starting ZAP scan\nINFO: Crawling 5 pages")
        assert result["count"] == 0
        assert result["findings"] == []

    def test_mixed_placeholder_and_real_alerts_counts_only_real(self):
        """Placeholder lines mixed with real alerts must not inflate the count."""
        parser = _load_zap_scanner_parser()
        mixed = (
            "ZAP scan in progress...\n"
            "PASS: Passive scan completed\n"
            "WARN-NEW: X-Frame-Options Header Not Set [10020]\n"
            "INFO: Crawling complete\n"
            "FAIL-NEW: SQL Injection [40018]\n"
            "Scan complete."
        )
        result = parser.parse(mixed)
        # Only the two real alert lines should be counted
        assert result["count"] == 2
        assert len(result["findings"]) == 2
        assert all(
            item.startswith("WARN-NEW:") or item.startswith("FAIL-NEW:")
            for item in result["items"]
        )

    def test_fixture_contains_no_placeholder_lines(self):
        """The canonical fixture must only contain real ZAP alert lines (or PASS:)."""
        parser = _load_zap_scanner_parser()
        raw = FIXTURE_PATH.read_text(encoding="utf-8")
        result = parser.parse(raw)

        # Every parsed item must be a real ZAP alert prefix
        for item in result["items"]:
            assert item.startswith("WARN-NEW:") or item.startswith("FAIL-NEW:"), (
                f"Fixture item is not a real ZAP alert line: {item!r}"
            )

    def test_parser_findings_have_real_alert_in_description(self):
        """Every finding's description must reference the original alert line.

        A placeholder response could produce findings with generic descriptions
        that contain no ZAP alert content.  This test ensures each description
        traces back to a WARN-NEW: or FAIL-NEW: line.
        """
        parser = _load_zap_scanner_parser()
        raw = FIXTURE_PATH.read_text(encoding="utf-8")
        result = parser.parse(raw)

        for finding in result["findings"]:
            desc = finding.get("description", "")
            assert "WARN-NEW:" in desc or "FAIL-NEW:" in desc, (
                f"Finding description does not reference a real ZAP alert: {desc!r}"
            )


class TestZAPPluginImplementationStatus:
    """The plugin's implementation status must be accurately reported.

    zap_scanner sets ``"implementation_status": "integrated"`` explicitly in
    its metadata.json.  The _resolve_implementation_status helper returns the
    explicit metadata value first, so the _PLACEHOLDER_PLUGIN_IDS fallback
    does NOT apply here.  These tests lock in the current declared status so
    any accidental change to the metadata is caught immediately.
    """

    def test_zap_scanner_is_in_placeholder_plugin_ids(self):
        """zap_scanner is still listed in _PLACEHOLDER_PLUGIN_IDS as a
        belt-and-suspenders marker; confirm the set membership is intact."""
        assert PLUGIN_ID in _PLACEHOLDER_PLUGIN_IDS

    def test_implementation_status_resolves_to_integrated(self, plugin_manager):
        """list_plugins() must surface implementation_status='integrated' for ZAP.

        The metadata.json explicitly declares ``implementation_status: integrated``
        which takes precedence over the _PLACEHOLDER_PLUGIN_IDS fallback.
        """
        plugins = plugin_manager.list_plugins()
        zap = next((p for p in plugins if p["id"] == PLUGIN_ID), None)
        assert zap is not None
        status = zap["implementation_status"]
        # Accept both the string and enum-repr forms to be robust across versions.
        assert status in ("integrated", "PluginImplementationStatus.INTEGRATED"), (
            f"Unexpected implementation_status {status!r}. "
            "If ZAP has been promoted or demoted, update this assertion."
        )

    def test_schema_implementation_status_resolves_to_integrated(self, plugin_manager):
        """get_plugin_schema() must also surface implementation_status='integrated'."""
        schema = plugin_manager.get_plugin_schema(PLUGIN_ID)
        assert schema is not None
        status = schema.get("implementation_status")
        assert status in ("integrated", "PluginImplementationStatus.INTEGRATED"), (
            f"Unexpected schema implementation_status {status!r}."
        )


class TestZAPCommandPathIsReal:
    """The built command must invoke the real ZAP Docker image, not a stub.

    Regression: if the command template is replaced with a placeholder
    command (e.g. ``echo``, ``true``, or a no-op), the test must fail.
    """

    def test_command_invokes_zaproxy_docker_image(self, plugin_manager):
        """The Docker image must be the official ZAP image, not a placeholder."""
        command = plugin_manager.build_command(
            PLUGIN_ID, {"target": "https://example.com"}
        )
        assert command is not None
        # Must use the official ZAP image
        assert "ghcr.io/zaproxy/zaproxy:stable" in command, (
            "ZAP command must reference the official ghcr.io/zaproxy/zaproxy:stable image"
        )
        # Must not be a placeholder no-op command
        assert command[0] != "echo", "ZAP command must not be a no-op echo stub"
        assert command[0] != "true", "ZAP command must not be a no-op true stub"
        assert "placeholder" not in " ".join(command).lower(), (
            "ZAP command must not contain the word 'placeholder'"
        )

    def test_command_uses_zap_baseline_entrypoint(self, plugin_manager):
        """The command must call zap-baseline.py, not a stub entrypoint."""
        command = plugin_manager.build_command(
            PLUGIN_ID, {"target": "https://example.com"}
        )
        assert command is not None
        assert "zap-baseline.py" in command, (
            "ZAP command must invoke zap-baseline.py as the entrypoint"
        )

    def test_command_passes_target_to_zap(self, plugin_manager):
        """The target URL must be forwarded to the ZAP -t flag."""
        target = "https://secuscan.in"
        command = plugin_manager.build_command(PLUGIN_ID, {"target": target})
        assert command is not None
        assert "-t" in command
        t_index = command.index("-t")
        assert command[t_index + 1] == target, (
            f"Expected target {target!r} after -t flag, got {command[t_index + 1]!r}"
        )
