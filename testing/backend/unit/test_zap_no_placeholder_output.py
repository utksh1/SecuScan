"""Regression tests ensuring the ZAP plugin does not produce or accept placeholder
scan output (issue #1419).

Acceptance criteria:
  - Parser rejects strings that look like hardcoded stub/placeholder output
    (plain text summaries with no WARN-NEW/FAIL-NEW alerts) as valid findings.
  - Plugin implementation_status is flagged as 'placeholder' so the UI can
    warn users before they rely on its output.
  - The real command path is Docker-based (not a stub command).
  - When Docker is unavailable the scanner reports completion without inventing
    fake findings.
  - Existing ZAP parser sample tests (WARN-NEW / FAIL-NEW lines) still pass.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager, _PLACEHOLDER_PLUGIN_IDS

PLUGIN_ID = "zap_scanner"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / PLUGIN_ID / "sample_output.txt"
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"

# ------------------------------------------------------------------
# Strings that look like placeholder / stub scan output.
# The parser must NOT treat any of these as real alert findings.
# ------------------------------------------------------------------
_PLACEHOLDER_STRINGS = [
    # Generic connector-level placeholders
    "ZAP connector placeholder scan",
    "ZAP scan completed (placeholder)",
    "placeholder scan output",
    "Placeholder: ZAP baseline not executed",
    # Plain summary lines with no alert prefixes
    "Scan completed successfully.",
    "No alerts found.",
    "PASS: Passive scan completed",
    # Partial / unformatted output
    "ZAP baseline.py finished",
    "Total alerts: 0",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_parser():
    spec = importlib.util.spec_from_file_location("zap_scanner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def parser():
    return _load_parser()


@pytest.fixture
def plugin_manager(setup_test_environment) -> PluginManager:
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


# ---------------------------------------------------------------------------
# Regression: parser must not accept placeholder strings as findings
# ---------------------------------------------------------------------------

class TestParserRejectsPlaceholderOutput:
    """The parser must produce zero findings for any placeholder-style string."""

    @pytest.mark.parametrize("stub_output", _PLACEHOLDER_STRINGS)
    def test_placeholder_string_produces_no_findings(self, parser, stub_output):
        result = parser.parse(stub_output)
        assert result["findings"] == [], (
            f"Parser accepted placeholder output as findings: {stub_output!r}\n"
            f"Got findings: {result['findings']}"
        )
        assert result["count"] == 0, (
            f"Parser reported non-zero count for placeholder output: {stub_output!r}"
        )

    @pytest.mark.parametrize("stub_output", _PLACEHOLDER_STRINGS)
    def test_placeholder_string_produces_no_items(self, parser, stub_output):
        result = parser.parse(stub_output)
        assert result["items"] == [], (
            f"Parser returned non-empty items list for placeholder output: {stub_output!r}"
        )

    def test_multiline_placeholder_with_no_alerts_produces_no_findings(self, parser):
        """Multi-line output that contains no WARN-NEW/FAIL-NEW lines must yield nothing."""
        output = "\n".join([
            "OWASP ZAP 2.14.0",
            "Connecting to: https://example.com",
            "PASS: Passive scan complete",
            "Total of 0 URLs",
            "PASS: No Issues Found",
        ])
        result = parser.parse(output)
        assert result["findings"] == []
        assert result["count"] == 0

    def test_pass_only_lines_produce_no_findings(self, parser):
        """Lines starting with PASS: must be ignored — only WARN-NEW/FAIL-NEW matter."""
        output = "PASS: All alerts cleared\nPASS: Scan complete"
        result = parser.parse(output)
        assert result["findings"] == []

    def test_empty_output_produces_no_findings(self, parser):
        result = parser.parse("")
        assert result["findings"] == []
        assert result["count"] == 0
        assert result["items"] == []

    def test_whitespace_only_produces_no_findings(self, parser):
        result = parser.parse("   \n\n  \t  ")
        assert result["findings"] == []
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# Regression: real alert lines must still produce findings (existing coverage)
# ---------------------------------------------------------------------------

class TestParserAcceptsRealAlertOutput:
    """Ensure the fix does not break parsing of real WARN-NEW/FAIL-NEW lines."""

    def test_warn_new_line_produces_finding(self, parser):
        result = parser.parse("WARN-NEW: X-Frame-Options Header Not Set [10020]")
        assert result["count"] == 1
        assert result["findings"][0]["severity"] == "low"

    def test_fail_new_line_produces_finding(self, parser):
        result = parser.parse("FAIL-NEW: SQL Injection [40018]")
        assert result["count"] == 1
        assert result["findings"][0]["severity"] == "high"

    def test_fixture_sample_output_still_passes(self, parser):
        """Existing fixture sample must continue to produce 3 findings."""
        raw = FIXTURE_PATH.read_text(encoding="utf-8")
        result = parser.parse(raw)
        assert result["count"] == 3
        assert len(result["findings"]) == 3

    def test_mixed_pass_and_alerts_only_counts_alerts(self, parser):
        """PASS: lines alongside real alerts must not inflate the finding count."""
        output = (
            "PASS: Passive scan completed\n"
            "WARN-NEW: Content Security Policy Header Not Set [10038]\n"
            "PASS: No SQL injection found\n"
            "FAIL-NEW: Path Traversal [6]\n"
        )
        result = parser.parse(output)
        assert result["count"] == 2
        severities = {f["severity"] for f in result["findings"]}
        assert "low" in severities
        assert "high" in severities


# ---------------------------------------------------------------------------
# Regression: plugin is correctly flagged as placeholder in the catalog
# ---------------------------------------------------------------------------

class TestPluginPlaceholderStatus:
    """The plugin must be discoverable but clearly flagged as a placeholder."""

    def test_zap_scanner_in_placeholder_ids(self):
        """zap_scanner must be in the _PLACEHOLDER_PLUGIN_IDS set."""
        assert PLUGIN_ID in _PLACEHOLDER_PLUGIN_IDS, (
            f"{PLUGIN_ID!r} was removed from _PLACEHOLDER_PLUGIN_IDS — "
            "if it now executes real scans, remove it from the set and update this test."
        )

    def test_implementation_status_is_placeholder(self, plugin_manager):
        """list_plugins() must advertise implementation_status='placeholder'."""
        plugins = plugin_manager.list_plugins()
        zap = next((p for p in plugins if p["id"] == PLUGIN_ID), None)
        assert zap is not None, f"{PLUGIN_ID!r} not found in loaded plugins"
        assert zap["implementation_status"] == "placeholder", (
            f"Expected implementation_status='placeholder', got {zap['implementation_status']!r}. "
            "If ZAP now executes real scans, update the implementation status and remove from "
            "_PLACEHOLDER_PLUGIN_IDS."
        )

    def test_plugin_loads_and_has_correct_metadata(self, plugin_manager):
        plugin = plugin_manager.get_plugin(PLUGIN_ID)
        assert plugin is not None
        assert plugin.id == PLUGIN_ID
        assert plugin.category == "vulnerability"
        assert plugin.safety.get("level") == "exploit"
        assert plugin.safety.get("requires_consent") is True


# ---------------------------------------------------------------------------
# Regression: command path is real Docker (not a stub/hardcoded string)
# ---------------------------------------------------------------------------

class TestCommandPathIsRealDocker:
    """The plugin command must target the real ZAP Docker image."""

    def test_command_starts_with_docker(self, plugin_manager):
        command = plugin_manager.build_command(PLUGIN_ID, {"target": "https://example.com"})
        assert command is not None
        assert command[0] == "docker", (
            f"Expected command to start with 'docker', got {command[0]!r}. "
            "A placeholder plugin must not ship a fake/hardcoded command."
        )

    def test_command_uses_real_zaproxy_image(self, plugin_manager):
        command = plugin_manager.build_command(PLUGIN_ID, {"target": "https://example.com"})
        assert command is not None
        assert "ghcr.io/zaproxy/zaproxy:stable" in command, (
            "ZAP command must reference the real zaproxy Docker image. "
            f"Got command: {command}"
        )

    def test_command_includes_zap_baseline_script(self, plugin_manager):
        command = plugin_manager.build_command(PLUGIN_ID, {"target": "https://example.com"})
        assert command is not None
        assert "zap-baseline.py" in command, (
            "ZAP command must include 'zap-baseline.py'. "
            f"Got command: {command}"
        )

    def test_command_passes_target_url(self, plugin_manager):
        target = "https://secuscan.in"
        command = plugin_manager.build_command(PLUGIN_ID, {"target": target})
        assert command is not None
        assert target in command


# ---------------------------------------------------------------------------
# Regression: when Docker is unavailable, scanner reports no invented findings
# ---------------------------------------------------------------------------

class TestScannerWithoutDocker:
    """When Docker is missing the scanner must not invent placeholder findings."""

    @pytest.mark.asyncio
    async def test_no_docker_returns_completed_with_no_zap_findings(self, setup_test_environment):
        from backend.secuscan.scanners.zap_scanner import ZAPScanner

        mock_db = AsyncMock()
        scanner = ZAPScanner(task_id="test-task", db=mock_db, safe_mode=True)

        empty_crawl: Dict[str, Any] = {"pages": [], "forms": [], "links": []}

        with patch("backend.secuscan.scanners.zap_scanner.crawl_target", return_value=empty_crawl), \
             patch("shutil.which", return_value=None):
            result = await scanner.run("https://example.com", {"target": "https://example.com"})

        assert result["status"] == "completed", (
            "Scanner must report 'completed' even when Docker is absent."
        )
        # No ZAP findings should be invented when Docker is not available
        zap_findings = [
            f for f in result.get("findings", [])
            if f.get("category") == "DAST"
        ]
        assert zap_findings == [], (
            f"Scanner invented {len(zap_findings)} DAST findings despite Docker being absent: "
            f"{zap_findings}"
        )

    @pytest.mark.asyncio
    async def test_no_docker_does_not_produce_placeholder_text_in_output(self, setup_test_environment):
        from backend.secuscan.scanners.zap_scanner import ZAPScanner

        mock_db = AsyncMock()
        scanner = ZAPScanner(task_id="test-task", db=mock_db, safe_mode=True)

        empty_crawl: Dict[str, Any] = {"pages": [], "forms": [], "links": []}

        with patch("backend.secuscan.scanners.zap_scanner.crawl_target", return_value=empty_crawl), \
             patch("shutil.which", return_value=None):
            result = await scanner.run("https://example.com", {"target": "https://example.com"})

        # zap_output_excerpt must be empty — no fabricated output
        excerpt = result.get("zap_output_excerpt", "")
        assert excerpt == "", (
            f"zap_output_excerpt should be empty when Docker is absent, got: {excerpt!r}"
        )