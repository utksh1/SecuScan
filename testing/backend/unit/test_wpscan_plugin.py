"""
Unit tests for plugins/wpscan/parser.py.
"""

import json
import pytest
from pathlib import Path

from plugins.wpscan.parser import _finding, parse


class TestFindingHelper:
    def test_returns_correct_keys(self):
        result = _finding("Test Title", "Test Category", "high", "Test description")
        assert "title" in result
        assert "category" in result
        assert "severity" in result
        assert "description" in result
        assert "remediation" in result
        assert "metadata" in result

    def test_remediation_is_set(self):
        result = _finding("Test", "Cat", "medium", "Desc")
        assert result["remediation"] == "Validate exposure and patch vulnerable components."

    def test_metadata_defaults_to_empty_dict(self):
        result = _finding("Test", "Cat", "low", "Desc")
        assert result["metadata"] == {}

    def test_metadata_passed_when_provided(self):
        meta = {"component": "my-plugin", "fixed_in": "1.2.3"}
        result = _finding("Test", "Cat", "high", "Desc", metadata=meta)
        assert result["metadata"] == meta

    def test_all_fields_present(self):
        result = _finding("Title", "Cat", "info", "Desc")
        assert result["title"] == "Title"
        assert result["category"] == "Cat"
        assert result["severity"] == "info"
        assert result["description"] == "Desc"


class TestParseJsonInput:
    @pytest.fixture
    def json_output(self):
        return {
            "target_url": "http://test.wordpress.local",
            "interesting_findings": [
                {"to_s": "WordPress version 6.0 detected", "references": {}}
            ],
            "plugins": {
                "plugin-a": {
                    "vulnerabilities": [
                        {"title": "Plugin A SQL Injection", "fixed_in": "2.0.0", "references": {}}
                    ]
                },
                "plugin-b": {"vulnerabilities": []}
            },
            "themes": {
                "theme-x": {"vulnerabilities": []}
            },
        }

    def test_parses_interesting_findings(self, json_output):
        result = parse(json.dumps(json_output))
        titles = [f["title"] for f in result["findings"]]
        assert any("WordPress version 6.0 detected" in t for t in titles)

    def test_parses_vulnerable_plugin(self, json_output):
        result = parse(json.dumps(json_output))
        descs = [f["description"] for f in result["findings"]]
        assert any("Plugin A SQL Injection" in d for d in descs)

    def test_vulnerable_plugin_has_high_severity(self, json_output):
        result = parse(json.dumps(json_output))
        high_findings = [f for f in result["findings"] if f["severity"] == "high"]
        assert len(high_findings) > 0
        assert any("plugin-a" in f["metadata"].get("component", "").lower() for f in high_findings)

    def test_non_vulnerable_plugin_not_reported(self, json_output):
        result = parse(json.dumps(json_output))
        titles = [f["title"] for f in result["findings"]]
        assert not any("plugin-b" in t.lower() for t in titles)

    def test_vulnerable_theme_is_reported(self, json_output):
        json_output["themes"]["theme-x"]["vulnerabilities"] = [
            {"title": "Theme X XSS", "fixed_in": "1.5", "references": {}}
        ]
        result = parse(json.dumps(json_output))
        titles = [f["title"] for f in result["findings"]]
        assert any("theme-x" in t.lower() for t in titles)
        descs = [f["description"] for f in result["findings"]]
        assert any("Theme X XSS" in d for d in descs)

    def test_vulnerable_theme_has_high_severity(self, json_output):
        json_output["themes"]["theme-x"]["vulnerabilities"] = [
            {"title": "Theme X CSRF", "fixed_in": "2.0", "references": {}}
        ]
        result = parse(json.dumps(json_output))
        high_findings = [f for f in result["findings"] if f["severity"] == "high"]
        assert len(high_findings) > 0

    def test_fixed_in_version_in_metadata(self, json_output):
        result = parse(json.dumps(json_output))
        vuln_findings = [f for f in result["findings"] if f["severity"] == "high"]
        assert len(vuln_findings) > 0
        fixed_in = vuln_findings[0]["metadata"].get("fixed_in")
        assert fixed_in == "2.0.0"

    def test_target_url_in_result(self, json_output):
        result = parse(json.dumps(json_output))
        assert result.get("target_url") == "http://test.wordpress.local"

    def test_count_reflects_total_findings(self, json_output):
        result = parse(json.dumps(json_output))
        assert result["count"] == len(result["findings"])

    def test_handles_empty_plugins_and_themes(self):
        output = json.dumps({
            "target_url": "http://test.local",
            "interesting_findings": [],
            "plugins": {},
            "themes": {},
        })
        result = parse(output)
        assert result["count"] == 0
        assert result["findings"] == []


class TestParsePlainTextInput:
    def test_parses_each_line_as_finding(self):
        plain = "[+] WordPress login page found\n[+] XMLRPC enabled\n[!] No plugins detected"
        result = parse(plain)
        assert result["count"] == 3
        assert len(result["findings"]) == 3

    def test_plain_text_finding_has_low_severity(self):
        plain = "[+] WordPress detected"
        result = parse(plain)
        assert result["findings"][0]["severity"] == "low"

    def test_plain_text_finding_has_correct_category(self):
        plain = "WordPress detected at root"
        result = parse(plain)
        assert result["findings"][0]["category"] == "CMS Security"

    def test_skips_empty_lines(self):
        plain = "Line 1\n\nLine 2\n   \nLine 3"
        result = parse(plain)
        assert result["count"] == 3

    def test_empty_input_returns_empty_findings(self):
        result = parse("")
        assert result["count"] == 0
        assert result["findings"] == []


class TestParseEdgeCases:
    def test_missing_interesting_findings_key(self):
        output = json.dumps({"plugins": {}, "themes": {}})
        result = parse(output)
        assert "count" in result

    def test_missing_plugins_key(self):
        output = json.dumps({"interesting_findings": [], "themes": {}})
        result = parse(output)
        assert "count" in result

    def test_none_vulnerabilities_in_plugin(self):
        output = json.dumps({
            "plugins": {"test": {"vulnerabilities": None}},
            "themes": {},
            "interesting_findings": [],
        })
        result = parse(output)
        assert result["count"] == 0

    def test_vuln_missing_title_defaults(self):
        output = json.dumps({
            "plugins": {"bad-plugin": {"vulnerabilities": [{}]}},
            "themes": {},
            "interesting_findings": [],
        })
        result = parse(output)
        assert any("bad-plugin" in f["title"].lower() for f in result["findings"])
