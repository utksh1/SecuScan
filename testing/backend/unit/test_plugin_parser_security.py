"""
Security tests for plugin parser execution and command argument injection.

Covers:
  - Parser integrity re-verification at execution time (TOCTOU defence)
  - Input schema validation that prevents CLI argument injection
  - PortScanner scan-type and port normalisation
"""

import asyncio
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.secuscan.config import settings
from backend.secuscan.models import PluginField, PluginFieldType, PluginMetadata
from backend.secuscan.plugins import PluginManager
from backend.secuscan.scanners.port_scanner import PortScanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(plugins_dir: str) -> PluginManager:
    manager = PluginManager(plugins_dir)
    asyncio.run(manager.load_plugins())
    return manager


def _make_mock_plugin(extra_fields: list | None = None) -> PluginMetadata:
    """Minimal plugin with one plain STRING field for unit-testing schema validation."""
    fields = [
        PluginField(
            id="custom_arg",
            label="Custom Arg",
            type=PluginFieldType.STRING,
            required=False,
        )
    ]
    if extra_fields:
        fields.extend(extra_fields)
    return PluginMetadata(
        id="mock_plugin",
        name="Mock Plugin",
        version="1.0.0",
        description="Unit test fixture",
        category="network",
        engine={"type": "cli", "binary": "nmap"},
        command_template=["nmap", "{custom_arg}"],
        fields=fields,
        presets={},
        output={"parser": "text", "format": "text"},
        safety={"level": "safe"},
    )


# ---------------------------------------------------------------------------
# Issue #202 — Parser integrity verification at execution time
# ---------------------------------------------------------------------------


class TestParserIntegrityAtExecTime:
    """verify_parser_at_exec_time() must block execution of tampered parsers."""

    def test_valid_checksum_passes(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        plugin = manager.get_plugin("nmap")
        assert plugin is not None
        plugin_dir = manager.plugins_dir / "nmap"
        assert manager.verify_parser_at_exec_time(plugin, plugin_dir)

    def test_tampered_parser_is_rejected(self, tmp_path):
        """Modifying parser.py after load must be caught before execution."""
        plugin_dir = tmp_path / "evil_plugin"
        plugin_dir.mkdir()

        metadata = {
            "id": "evil_plugin",
            "name": "Evil Plugin",
            "version": "1.0.0",
            "description": "Test",
            "category": "network",
            "engine": {"type": "cli", "binary": "nmap"},
            "command_template": ["nmap", "{target}"],
            "fields": [],
            "presets": {},
            "output": {"parser": "custom", "format": "text"},
            "safety": {"level": "safe"},
        }
        metadata_file = plugin_dir / "metadata.json"
        parser_file = plugin_dir / "parser.py"

        # Write both files before computing the digest (metadata.json must exist first)
        parser_file.write_text("def parse(output): return {}", encoding="utf-8")
        metadata_file.write_text(json.dumps(metadata), encoding="utf-8")

        checksum = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        metadata["checksum"] = checksum
        metadata_file.write_text(json.dumps(metadata), encoding="utf-8")

        # Load the plugin so it exists in the manager
        manager = PluginManager(str(tmp_path))
        asyncio.run(manager.load_plugins())
        plugin = manager.get_plugin("evil_plugin")
        assert plugin is not None

        # Tamper with the parser AFTER loading
        parser_file.write_text(
            "import os; os.system('id')\ndef parse(output): return {}",
            encoding="utf-8",
        )

        assert not manager.verify_parser_at_exec_time(plugin, plugin_dir)

    def test_missing_checksum_blocked_when_enforcement_enabled(self, tmp_path, monkeypatch):
        """No checksum + enforce_plugin_signatures=True must block execution."""
        monkeypatch.setattr(settings, "enforce_plugin_signatures", True)

        plugin_dir = tmp_path / "unsigned_plugin"
        plugin_dir.mkdir()
        metadata_file = plugin_dir / "metadata.json"
        parser_file = plugin_dir / "parser.py"

        metadata = {
            "id": "unsigned_plugin",
            "name": "Unsigned",
            "version": "1.0.0",
            "description": "Test",
            "category": "network",
            "engine": {"type": "cli", "binary": "nmap"},
            "command_template": ["nmap", "{target}"],
            "fields": [],
            "presets": {},
            "output": {"parser": "custom", "format": "text"},
            "safety": {"level": "safe"},
        }
        metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
        parser_file.write_text("def parse(output): return {}", encoding="utf-8")

        manager = PluginManager(str(tmp_path))
        # Skip the load-time integrity check for this test
        from backend.secuscan.models import PluginMetadata
        plugin = PluginMetadata(**metadata)
        manager.plugins["unsigned_plugin"] = plugin

        assert not manager.verify_parser_at_exec_time(plugin, plugin_dir)

    def test_missing_checksum_allowed_when_enforcement_disabled(self, tmp_path, monkeypatch):
        """No checksum + enforce_plugin_signatures=False must pass with a warning."""
        monkeypatch.setattr(settings, "enforce_plugin_signatures", False)

        plugin_dir = tmp_path / "lax_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "parser.py").write_text("def parse(o): return {}", encoding="utf-8")

        from backend.secuscan.models import PluginMetadata
        plugin = PluginMetadata(
            id="lax_plugin",
            name="Lax Plugin",
            version="1.0.0",
            description="No checksum",
            category="network",
            engine={"type": "cli", "binary": "nmap"},
            command_template=["nmap", "{target}"],
            fields=[],
            presets={},
            output={"parser": "custom", "format": "text"},
            safety={"level": "safe"},
            checksum=None,
        )

        manager = PluginManager(str(tmp_path))
        assert manager.verify_parser_at_exec_time(plugin, plugin_dir)

    def test_digest_computation_failure_rejects_execution(self, tmp_path):
        """If digest computation throws, execution must be refused."""
        from backend.secuscan.models import PluginMetadata
        plugin = PluginMetadata(
            id="broken",
            name="Broken",
            version="1.0.0",
            description="x",
            category="network",
            engine={"type": "cli", "binary": "nmap"},
            command_template=["nmap", "{target}"],
            fields=[],
            presets={},
            output={"parser": "custom", "format": "text"},
            safety={"level": "safe"},
            checksum="somechecksum",
        )

        manager = PluginManager(str(tmp_path))
        # plugin_dir doesn't exist, so compute_plugin_digest will raise
        missing_dir = tmp_path / "no_such_plugin"
        assert not manager.verify_parser_at_exec_time(plugin, missing_dir)


# ---------------------------------------------------------------------------
# Issue #201 — Command argument injection via scanner inputs
# ---------------------------------------------------------------------------


class TestInputSchemaValidation:
    """_validate_inputs_against_schema() must reject injection-prone values."""

    def test_valid_nmap_inputs_pass(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        # Should not raise
        manager.build_command("nmap", {"target": "192.168.1.1", "scan_type": "T", "ports": "80,443"})

    def test_invalid_select_value_rejected(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        with pytest.raises(ValueError, match="not in the allowed set"):
            manager.build_command("nmap", {"target": "192.168.1.1", "scan_type": "X"})

    def test_port_injection_via_flag_prefix_rejected(self, setup_test_environment):
        """ports='--script=evil.nse' would inject a flag into the nmap argv."""
        manager = _make_manager(settings.plugins_dir)
        with pytest.raises(ValueError, match="port specification"):
            manager.build_command("nmap", {"target": "192.168.1.1", "ports": "--script=evil.nse"})

    def test_port_injection_via_dash_prefix_rejected(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        with pytest.raises(ValueError, match="port specification"):
            manager.build_command("nmap", {"target": "192.168.1.1", "ports": "-p-"})

    def test_valid_port_range_passes(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        cmd = manager.build_command("nmap", {"target": "192.168.1.1", "ports": "1-1000"})
        assert "1-1000" in cmd

    def test_valid_comma_ports_pass(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        cmd = manager.build_command("nmap", {"target": "192.168.1.1", "ports": "22,80,443"})
        assert "22,80,443" in cmd

    def test_scan_type_with_leading_dash_rejected(self, setup_test_environment):
        """scan_type is a select field; free-text values that aren't in the options list are rejected."""
        manager = _make_manager(settings.plugins_dir)
        with pytest.raises(ValueError, match="not in the allowed set"):
            manager.build_command("nmap", {"target": "192.168.1.1", "scan_type": "-sS --script=evil"})

    def test_target_field_pattern_enforced(self, setup_test_environment):
        """The nmap target field has pattern ^[a-zA-Z0-9.-]+$ that blocks shell metacharacters."""
        manager = _make_manager(settings.plugins_dir)
        with pytest.raises(ValueError):
            manager.build_command("nmap", {"target": "192.168.1.1; id"})

    def test_string_field_leading_dash_rejected(self, tmp_path):
        """Any STRING field value starting with '-' is rejected to prevent flag injection."""
        manager = PluginManager(str(tmp_path))
        plugin = _make_mock_plugin()
        manager.plugins["mock_plugin"] = plugin
        with pytest.raises(ValueError, match="must not begin with"):
            manager._validate_inputs_against_schema(plugin, {"custom_arg": "-v --evil-payload"})

    def test_integer_field_type_enforced(self, setup_test_environment):
        manager = _make_manager(settings.plugins_dir)
        with pytest.raises(ValueError, match="expects an integer"):
            manager.build_command(
                "http_inspector",
                {"url": "http://localhost", "timeout": "not_a_number"},
            )


# ---------------------------------------------------------------------------
# PortScanner input normalisation
# ---------------------------------------------------------------------------


class TestPortScannerInputNormalisation:
    """PortScanner must produce values that pass the nmap plugin's schema validation."""

    @pytest.mark.parametrize("raw,expected_letter,expected_svc", [
        ("T", "T", False),
        ("S", "S", False),
        ("U", "U", False),
        ("-sV", "T", True),   # service-version detection maps to TCP connect + svc flag
        ("sV", "T", True),
        ("-sS", "S", False),
        ("-sT", "T", False),
        ("-sU", "U", False),
        ("", "T", False),     # empty defaults to TCP connect
        ("X", "T", False),    # unknown letter defaults safely
    ])
    def test_resolve_scan_type(self, raw, expected_letter, expected_svc):
        letter, svc = PortScanner._resolve_scan_type(raw)
        assert letter == expected_letter
        assert svc == expected_svc

    @pytest.mark.parametrize("raw,expected", [
        ("", ""),
        ("top100", ""),
        ("top1000", "1-1000"),
        ("all", "1-65535"),
        ("80,443", "80,443"),
        ("22", "22"),
        ("1-1000", "1-1000"),
    ])
    def test_resolve_ports(self, raw, expected):
        assert PortScanner._resolve_ports(raw) == expected

    def test_resolved_ports_pass_schema_validation(self, setup_test_environment):
        """Values produced by _resolve_ports must all pass _reject_injected_args."""
        manager = _make_manager(settings.plugins_dir)
        safe_cases = ["", "80,443", "1-1000", "1-65535", "22"]
        for ports_value in safe_cases:
            # build_command raises if validation fails; no assertion needed beyond no-raise
            manager.build_command(
                "nmap",
                {"target": "192.168.1.1", "scan_type": "T", "ports": ports_value},
            )

    def test_old_top_ports_shorthand_would_have_injected(self):
        """Regression: the old '--top-ports 100' value fails the port validator."""
        from backend.secuscan.plugins import _PORT_SPEC_PATTERN
        assert not _PORT_SPEC_PATTERN.match("--top-ports 100")

    def test_old_dash_p_shorthand_would_have_injected(self):
        """Regression: the old '-p-' (all-ports flag) fails the port validator."""
        from backend.secuscan.plugins import _PORT_SPEC_PATTERN
        assert not _PORT_SPEC_PATTERN.match("-p-")
