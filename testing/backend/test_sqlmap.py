"""
Unit tests for plugins/sqlmap/parser.py.
"""

import importlib.util
from pathlib import Path

import pytest

# Import the parser module directly from the file without requiring __init__.py
_parser_path = Path(__file__).resolve().parents[2] / "plugins" / "sqlmap" / "parser.py"
_spec = importlib.util.spec_from_file_location("plugins.sqlmap.parser", str(_parser_path))
_parser_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parser_module)
parse = _parser_module.parse


class TestParseVulnerabilityWithParameter:
    def test_detects_vulnerability_with_parameter_match(self):
        output = "Parameter: id (GET)\nGET parameter 'id' is vulnerable."
        result = parse(output)
        assert len(result["findings"]) == 1
        assert result["findings"][0]["title"] == "SQL Injection Vulnerability: id"

    def test_finding_has_critical_severity(self):
        output = "Parameter: id (GET)\nis vulnerable"
        result = parse(output)
        assert result["findings"][0]["severity"] == "critical"

    def test_finding_category_is_injection(self):
        output = "Parameter: id (GET)\nis vulnerable"
        result = parse(output)
        assert result["findings"][0]["category"] == "Injection"

    def test_finding_has_remediation(self):
        output = "Parameter: id (GET)\nis vulnerable"
        result = parse(output)
        assert len(result["findings"][0]["remediation"]) > 0

    def test_metadata_contains_parameter_name(self):
        output = "Parameter: cat (GET)\nis vulnerable"
        result = parse(output)
        assert result["findings"][0]["metadata"]["parameter"] == "cat"

    def test_metadata_type_field_captures_method_group(self):
        # Documents current parser behavior: captures the HTTP method (GET),
        # not the injection technique. Not a bug fix target for this PR.
        output = "Parameter: cat (GET)\nis vulnerable"
        result = parse(output)
        assert result["findings"][0]["metadata"]["type"] == "GET"

    def test_description_mentions_parameter_name(self):
        output = "Parameter: id (GET)\nis vulnerable"
        result = parse(output)
        assert "id" in result["findings"][0]["description"]


class TestParseVulnerabilityWithoutParameterMatch:
    def test_fallback_finding_when_no_parameter_line(self):
        output = "the target is vulnerable to sql injection"
        # No "Parameter: X (Y)" line present, but "is vulnerable" not in this string
        # so use exact phrase the parser checks for:
        output = "the application is vulnerable but no parameter line given"
        result = parse(output)
        assert len(result["findings"]) == 1
        assert result["findings"][0]["title"] == "Unspecified SQL Injection Vulnerability"

    def test_fallback_finding_has_no_metadata_key(self):
        output = "the application is vulnerable but no parameter line given"
        result = parse(output)
        assert "metadata" not in result["findings"][0]


class TestMetadataExtraction:
    def test_extracts_dbms(self):
        output = "back-end DBMS: MySQL >= 5.0.12"
        result = parse(output)
        assert result["metadata"]["dbms"] == "MySQL >= 5.0.12"

    def test_extracts_tech_stack(self):
        output = "web application technology: Apache 2.4.41, PHP 7.4.3"
        result = parse(output)
        assert result["metadata"]["tech_stack"] == "Apache 2.4.41, PHP 7.4.3"

    def test_extracts_both_dbms_and_tech_stack_together(self):
        output = (
            "Parameter: id (GET)\n"
            "is vulnerable\n"
            "back-end DBMS: PostgreSQL\n"
            "web application technology: Nginx 1.18.0\n"
        )
        result = parse(output)
        assert result["metadata"]["dbms"] == "PostgreSQL"
        assert result["metadata"]["tech_stack"] == "Nginx 1.18.0"

    def test_no_metadata_when_lines_absent(self):
        output = "Parameter: id (GET)\nis vulnerable"
        result = parse(output)
        assert result["metadata"] == {}


class TestEdgeCases:
    def test_empty_input_returns_empty_findings(self):
        result = parse("")
        assert result["findings"] == []
        assert result["metadata"] == {}

    def test_whitespace_only_input_returns_empty_findings(self):
        result = parse("   \n  \n  ")
        assert result["findings"] == []
        assert result["metadata"] == {}

    def test_malformed_garbage_input_does_not_crash(self):
        output = "asdf ###!!! random noise 12345 not sqlmap output at all"
        result = parse(output)
        assert isinstance(result, dict)
        assert result["findings"] == []
        assert result["metadata"] == {}

    def test_non_matching_lines_ignored(self):
        output = "Starting sqlmap scan\nsome irrelevant log line\nFinished scan"
        result = parse(output)
        assert result["findings"] == []
        assert result["metadata"] == {}

    def test_result_always_has_findings_and_metadata_keys(self):
        result = parse("anything")
        assert "findings" in result
        assert "metadata" in result