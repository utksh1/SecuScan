"""
Unit tests for plugins/virtual-host-finder/parser.py.
"""

import importlib.util
from pathlib import Path

import pytest

# Import the parser module directly from the file without requiring __init__.py
_parser_path = Path(__file__).resolve().parents[3] / "plugins" / "virtual-host-finder" / "parser.py"
_spec = importlib.util.spec_from_file_location("plugins.virtual_host_finder.parser", str(_parser_path))
_parser_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parser_module)
parse = _parser_module.parse


class TestParseVirtualHostFinder:
    def test_parses_single_vhost(self):
        output = "virtual-host-1.example.com found at 192.168.1.100"
        result = parse(output)
        assert result["count"] == 1
        assert len(result["findings"]) == 1

    def test_parses_multiple_vhosts(self):
        output = "host1.example.com found\nhost2.example.com found"
        result = parse(output)
        assert result["count"] == 2
        assert len(result["findings"]) == 2

    def test_vhost_has_correct_title(self):
        output = "vhost.local found"
        result = parse(output)
        assert result["findings"][0]["title"] == "Virtual Hosts Finder Observation"

    def test_vhost_has_correct_category(self):
        output = "vhost.local found"
        result = parse(output)
        assert result["findings"][0]["category"] == "Recon"

    def test_vhost_has_remediation(self):
        output = "vhost.local found"
        result = parse(output)
        assert "remediation" in result["findings"][0]
        assert len(result["findings"][0]["remediation"]) > 0

    def test_metadata_contains_raw_line(self):
        output = "vhost.local found"
        result = parse(output)
        assert result["findings"][0]["metadata"]["raw_line"] == "vhost.local found"

    def test_description_equals_original_line(self):
        output = "some-vhost.example.com detected"
        result = parse(output)
        assert result["findings"][0]["description"] == "some-vhost.example.com detected"

    def test_count_matches_findings_length(self):
        output = "vhost1.example.com found\nvhost2.example.com found\nvhost3.example.com found"
        result = parse(output)
        assert result["count"] == len(result["findings"])


class TestSeverityClassification:
    def test_default_severity_is_info(self):
        output = "vhost.local"
        result = parse(output)
        assert result["findings"][0]["severity"] == "info"

    def test_vuln_keyword_triggers_low(self):
        output = "vhost.local vuln detected"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_vulnerable_keyword_triggers_low(self):
        output = "vhost.local is vulnerable"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_exposed_keyword_triggers_low(self):
        output = "vhost.local exposed"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_open_keyword_triggers_low(self):
        output = "vhost.local open"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_found_keyword_triggers_low(self):
        output = "vhost.local found"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_detected_keyword_triggers_low(self):
        output = "vhost.local detected"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_alive_keyword_triggers_low(self):
        output = "vhost.local alive"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_case_insensitive_matching(self):
        output = "VHOST.LOCAL VULN DETECTED"
        result = parse(output)
        assert result["findings"][0]["severity"] == "low"

    def test_multiple_vhosts_mixed_severity(self):
        output = "vhost1.local normal\nvhost2.local vuln"
        result = parse(output)
        assert result["findings"][0]["severity"] == "info"
        assert result["findings"][1]["severity"] == "low"


class TestItemsField:
    def test_items_contains_all_lines(self):
        output = "vhost1.example.com found\nvhost2.example.com found"
        result = parse(output)
        assert len(result["items"]) == 2
        assert "vhost1.example.com found" in result["items"]
        assert "vhost2.example.com found" in result["items"]

    def test_items_strips_empty_lines(self):
        output = "vhost1.example.com found\n\nvhost2.example.com found"
        result = parse(output)
        assert len(result["items"]) == 2

    def test_items_trims_whitespace(self):
        output = "  vhost.example.com found  \n"
        result = parse(output)
        assert "vhost.example.com found" in result["items"]


class TestLineLimits:
    def test_limits_to_200_lines(self):
        lines = [f"vhost-{i}.example.com found" for i in range(250)]
        output = "\n".join(lines)
        result = parse(output)
        assert result["count"] == 200
        assert len(result["items"]) == 200


class TestEdgeCases:
    def test_empty_input_returns_empty_findings(self):
        result = parse("")
        assert result["count"] == 0
        assert result["findings"] == []
        assert result["items"] == []

    def test_whitespace_only_returns_empty_findings(self):
        result = parse("   \n  \n  ")
        assert result["count"] == 0
        assert result["items"] == []

    def test_returns_info_when_no_keywords_present(self):
        output = "vhost1.example.com\nvhost2.example.com"
        result = parse(output)
        assert all(f["severity"] == "info" for f in result["findings"])

    def test_finding_shape_consistent(self):
        output = "vhost.example.com found"
        result = parse(output)
        f = result["findings"][0]
        assert "title" in f
        assert "category" in f
        assert "severity" in f
        assert "description" in f
        assert "remediation" in f
        assert "metadata" in f
