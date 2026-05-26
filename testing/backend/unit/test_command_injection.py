"""
Security tests for command argument injection prevention (issue #201).

Verifies that:
- Flag injection via `ports`, `scan_type`, and other fields is blocked
- SELECT fields reject values outside their declared option list
- INTEGER fields reject non-integer strings
- Pattern-validated STRING fields reject non-matching input
- PortScanner input normalisation produces schema-compliant values
- Valid inputs are accepted unchanged
"""

import pytest
from unittest.mock import MagicMock
from typing import Any, Dict, List, Optional

from backend.secuscan.plugins import PluginManager, _PORT_SPEC_PATTERN
from backend.secuscan.models import PluginMetadata, PluginField, PluginFieldType
from backend.secuscan.scanners.port_scanner import PortScanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin(**extra_fields) -> PluginMetadata:
    """Build a minimal PluginMetadata with caller-supplied field list."""
    base = {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "test",
        "category": "test",
        "engine": {"type": "cli", "binary": "echo"},
        "command_template": ["{target}"],
        "safety": {"level": "safe"},
        "output": {"format": "text", "parser": "none"},
        "fields": [],
        "presets": {},
    }
    base.update(extra_fields)
    return PluginMetadata(**base)


def _make_manager() -> PluginManager:
    return PluginManager(plugins_dir="/nonexistent")


def _nmap_like_plugin() -> PluginMetadata:
    """Minimal replica of the nmap plugin field schema used in validation tests."""
    return _make_plugin(
        id="nmap",
        fields=[
            PluginField(
                id="target",
                label="Target",
                type=PluginFieldType.STRING,
                validation={"pattern": r"^[a-zA-Z0-9.\-]+$", "message": "Invalid target"},
            ),
            PluginField(
                id="scan_type",
                label="Scan Type",
                type=PluginFieldType.SELECT,
                options=[{"value": "S"}, {"value": "T"}, {"value": "U"}],
            ),
            PluginField(
                id="ports",
                label="Ports",
                type=PluginFieldType.STRING,
            ),
            PluginField(
                id="timeout",
                label="Timeout",
                type=PluginFieldType.INTEGER,
            ),
            PluginField(
                id="service_detection",
                label="Service detection",
                type=PluginFieldType.BOOLEAN,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# _reject_injected_args
# ---------------------------------------------------------------------------

class TestRejectInjectedArgs:
    def setup_method(self):
        self.mgr = _make_manager()

    def test_ports_valid_numeric(self):
        self.mgr._reject_injected_args("ports", "22,80,443")

    def test_ports_valid_range(self):
        self.mgr._reject_injected_args("ports", "1-1000")

    def test_ports_empty_ok(self):
        self.mgr._reject_injected_args("ports", "")

    def test_ports_flag_injection_rejected(self):
        with pytest.raises(ValueError, match="port specification"):
            self.mgr._reject_injected_args("ports", "--script=evil.nse")

    def test_ports_space_injection_rejected(self):
        with pytest.raises(ValueError, match="port specification"):
            self.mgr._reject_injected_args("ports", "80 --script malware")

    def test_string_leading_dash_rejected(self):
        with pytest.raises(ValueError, match="must not begin with '-'"):
            self.mgr._reject_injected_args("wordlist", "--dump-header /etc/passwd")

    def test_string_value_ok(self):
        self.mgr._reject_injected_args("wordlist", "/usr/share/wordlists/common.txt")

    def test_target_with_valid_hostname_ok(self):
        self.mgr._reject_injected_args("target", "example.com")


# ---------------------------------------------------------------------------
# _validate_inputs_against_schema
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def setup_method(self):
        self.mgr = _make_manager()
        self.plugin = _nmap_like_plugin()

    def _validate(self, inputs: Dict[str, Any]) -> None:
        self.mgr._validate_inputs_against_schema(self.plugin, inputs)

    # SELECT field
    def test_select_valid_value_accepted(self):
        self._validate({"scan_type": "T"})

    def test_select_invalid_value_rejected(self):
        with pytest.raises(ValueError, match="not in allowed values"):
            self._validate({"scan_type": "-sV"})

    def test_select_injection_rejected(self):
        with pytest.raises(ValueError, match="not in allowed values"):
            self._validate({"scan_type": "T --script malware"})

    # INTEGER field
    def test_integer_valid(self):
        self._validate({"timeout": 30})
        self._validate({"timeout": "30"})

    def test_integer_string_rejected(self):
        with pytest.raises(ValueError, match="expects an integer"):
            self._validate({"timeout": "thirty"})

    def test_integer_flag_rejected(self):
        with pytest.raises(ValueError, match="expects an integer"):
            self._validate({"timeout": "--evil"})

    # BOOLEAN field
    def test_boolean_true_accepted(self):
        self._validate({"service_detection": True})
        self._validate({"service_detection": "true"})

    def test_boolean_invalid_rejected(self):
        with pytest.raises(ValueError, match="expects a boolean"):
            self._validate({"service_detection": "yes"})

    # Pattern-validated STRING field (target)
    def test_target_valid(self):
        self._validate({"target": "example.com"})
        self._validate({"target": "192.168.1.1"})

    def test_target_invalid_pattern_rejected(self):
        with pytest.raises(ValueError, match="Invalid target"):
            self._validate({"target": "$(evil)"})

    # ports STRING field — custom logic
    def test_ports_valid(self):
        self._validate({"ports": "22,80,443"})
        self._validate({"ports": "1-1000"})

    def test_ports_flag_injection_rejected(self):
        with pytest.raises(ValueError, match="port specification"):
            self._validate({"ports": "--script=vuln"})

    # None/empty values are skipped (defaults handled later)
    def test_none_value_skipped(self):
        self._validate({"scan_type": None})

    def test_empty_string_skipped(self):
        self._validate({"ports": ""})

    # Unknown fields are silently ignored
    def test_unknown_field_rejected(self):
        with pytest.raises(ValueError, match="Unknown field"):
            self._validate({"unknown_field": "--evil"})

    def test_unknown_field_empty_value_rejected(self):
        with pytest.raises(ValueError, match="Unknown field"):
            self._validate({"not_in_schema": ""})


# ---------------------------------------------------------------------------
# PortScanner input normalisation
# ---------------------------------------------------------------------------

class TestPortScannerResolveScanType:
    @pytest.mark.parametrize("raw,expected", [
        ("T", "T"),
        ("S", "S"),
        ("U", "U"),
        ("-sT", "T"),
        ("-sS", "S"),
        ("-sU", "U"),
        ("sT", "T"),
        (None, "T"),
        ("", "T"),
    ])
    def test_resolve_scan_type_valid(self, raw, expected):
        assert PortScanner._resolve_scan_type(raw) == expected

    @pytest.mark.parametrize("raw", [
        "-sV",           # -sV is a version-detection flag, not a scan-type
        "V",             # V is not a valid scan-type letter
        "X",
        "TCP",
        "--script=evil",
        "T; rm -rf /",
    ])
    def test_resolve_scan_type_invalid_raises(self, raw):
        with pytest.raises(ValueError, match="Invalid scan_type"):
            PortScanner._resolve_scan_type(raw)


class TestPortScannerResolvePorts:
    @pytest.mark.parametrize("raw,expected", [
        ("", ""),
        (None, ""),
        ("top100", ""),
        ("top1000", "1-1000"),
        ("all", "1-65535"),
        ("22,80,443", "22,80,443"),
        ("1-1000", "1-1000"),
        ("22,80,1000-2000", "22,80,1000-2000"),
    ])
    def test_resolve_ports_valid(self, raw, expected):
        assert PortScanner._resolve_ports(raw) == expected

    @pytest.mark.parametrize("raw", [
        "--script=evil.nse",
        "--top-ports 100",
        "-p 80",
        "80 --script",
        "1--2",          # repeated hyphens
        "--",
        ",,",
        ",80",           # leading comma
        "80,",           # trailing comma
    ])
    def test_resolve_ports_invalid_raises(self, raw):
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports(raw)


# ---------------------------------------------------------------------------
# Port spec pattern
# ---------------------------------------------------------------------------

class TestPortSpecPattern:
    @pytest.mark.parametrize("value,should_match", [
        ("22", True),
        ("22,80,443", True),
        ("1-1000", True),
        ("1-65535", True),
        ("22,80,1000-2000", True),
        # invalid
        ("", False),
        ("--script=evil", False),
        ("80 --script", False),
        ("22;whoami", False),
        ("$(id)", False),
        ("--", False),        # repeated hyphens
        ("1--2", False),      # double hyphen in range
        (",,", False),        # empty comma-separated entries
        (",80", False),       # leading comma
        ("80,", False),       # trailing comma
        ("-80", False),       # leading hyphen
    ])
    def test_pattern(self, value, should_match):
        assert bool(_PORT_SPEC_PATTERN.match(value)) == should_match
