"""
Unit tests for PortScanner input-resolution static helpers in
backend/secuscan/scanners/port_scanner.py.

Covers:
- _resolve_scan_type: normalises scan type spec to nmap plugin SELECT value (S/T/U)
- _resolve_ports: normalises port shorthand to nmap port range string

run() and _parse_nmap_output() perform real I/O and are NOT tested here.
"""

import pytest

from backend.secuscan.scanners.port_scanner import PortScanner


# ---------------------------------------------------------------------------
# _resolve_scan_type
# ---------------------------------------------------------------------------


class TestResolveScanType:
    def test_bare_S(self):
        assert PortScanner._resolve_scan_type("S") == "S"

    def test_bare_T(self):
        assert PortScanner._resolve_scan_type("T") == "T"

    def test_bare_U(self):
        assert PortScanner._resolve_scan_type("U") == "U"

    def test_lowercase_s(self):
        assert PortScanner._resolve_scan_type("s") == "S"
        assert PortScanner._resolve_scan_type("t") == "T"
        assert PortScanner._resolve_scan_type("u") == "U"

    def test_dash_prefixed_sT(self):
        assert PortScanner._resolve_scan_type("-sT") == "T"

    def test_dash_prefixed_sS(self):
        assert PortScanner._resolve_scan_type("-sS") == "S"

    def test_dash_prefixed_sU(self):
        assert PortScanner._resolve_scan_type("-sU") == "U"

    def test_dash_prefixed_uppercase(self):
        assert PortScanner._resolve_scan_type("-ST") == "T"

    def test_bare_sT_no_dash(self):
        assert PortScanner._resolve_scan_type("sT") == "T"

    def test_bare_sS_no_dash(self):
        assert PortScanner._resolve_scan_type("sS") == "S"

    def test_empty_string_defaults_to_T(self):
        assert PortScanner._resolve_scan_type("") == "T"

    def test_none_defaults_to_T(self):
        assert PortScanner._resolve_scan_type(None) == "T"

    def test_whitespace_stripped(self):
        assert PortScanner._resolve_scan_type("  T  ") == "T"

    def test_invalid_scan_type_raises(self):
        with pytest.raises(ValueError, match="Invalid scan_type"):
            PortScanner._resolve_scan_type("X")

    def test_invalid_dash_prefix_raises(self):
        with pytest.raises(ValueError, match="Invalid scan_type"):
            PortScanner._resolve_scan_type("-sX")

    def test_invalid_bare_letter_raises(self):
        with pytest.raises(ValueError, match="Invalid scan_type"):
            PortScanner._resolve_scan_type("V")

    def test_multi_char_non_strippable_raises(self):
        with pytest.raises(ValueError, match="Invalid scan_type"):
            PortScanner._resolve_scan_type("scan")

    def test_partial_dash_strip_raises(self):
        with pytest.raises(ValueError, match="Invalid scan_type"):
            PortScanner._resolve_scan_type("-s")


# ---------------------------------------------------------------------------
# _resolve_ports
# ---------------------------------------------------------------------------


class TestResolvePorts:
    def test_none_returns_empty_string(self):
        assert PortScanner._resolve_ports(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert PortScanner._resolve_ports("") == ""

    def test_top100_returns_empty_string(self):
        # top100 maps to empty string to use plugin default (top-100 ports)
        assert PortScanner._resolve_ports("top100") == ""

    def test_top1000_returns_one_to_1000(self):
        assert PortScanner._resolve_ports("top1000") == "1-1000"

    def test_all_returns_one_to_65535(self):
        assert PortScanner._resolve_ports("all") == "1-65535"

    def test_single_port_passthrough(self):
        assert PortScanner._resolve_ports("80") == "80"
        assert PortScanner._resolve_ports("443") == "443"
        assert PortScanner._resolve_ports("8080") == "8080"

    def test_port_range_passthrough(self):
        assert PortScanner._resolve_ports("1-1000") == "1-1000"
        assert PortScanner._resolve_ports("22-1024") == "22-1024"

    def test_comma_separated_ports_passthrough(self):
        assert PortScanner._resolve_ports("22,80,443") == "22,80,443"

    def test_comma_separated_ranges_passthrough(self):
        assert PortScanner._resolve_ports("22,80-90,443,8000-8100") == "22,80-90,443,8000-8100"

    def test_whitespace_not_stripped_raises(self):
        # _resolve_ports does NOT strip whitespace; raw input must be exact
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports("  80  ")

    def test_invalid_non_numeric_raises(self):
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports("http")

    def test_invalid_mixed_format_raises(self):
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports("80-abc")

    def test_range_order_not_validated_by_function(self):
        # The function uses a regex that accepts "100-80" as a valid port spec.
        # Range-order validation is the caller's responsibility.
        assert PortScanner._resolve_ports("100-80") == "100-80"

    def test_range_order_reversed_accepted(self):
        assert PortScanner._resolve_ports("1024-22") == "1024-22"

    def test_invalid_single_value_letters_raises(self):
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports("abc")

    def test_invalid_topxxx_raises(self):
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports("top50")

    def test_negative_port_raises(self):
        with pytest.raises(ValueError, match="Invalid port specification"):
            PortScanner._resolve_ports("-1")