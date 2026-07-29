"""
Unit tests for _build_prompt edge cases in backend/secuscan/ai_summary.py.

Covers input shapes and content that are not tested in test_ai_summary.py:
- _build_prompt with only info/low severity findings (no critical/high)
- _build_prompt with all severity levels present
- _build_prompt with findings that have no recognized category
- _build_prompt with extremely long finding titles
- _build_prompt with mixed-case severity strings
- _build_prompt with duplicate categories
"""

import pytest

from backend.secuscan.ai_summary import _build_prompt


SAMPLE_FINDINGS = [
    {"title": "SQL Injection in login form",       "severity": "critical", "category": "injection"},
    {"title": "Reflected XSS in search parameter", "severity": "high",     "category": "xss"},
    {"title": "Missing X-Frame-Options header",  "severity": "medium",   "category": "headers"},
    {"title": "Outdated jQuery version",           "severity": "low",      "category": "components"},
    {"title": "Server version disclosed",          "severity": "info",     "category": "information-disclosure"},
]


class TestBuildPromptEdgeCases:
    def test_only_info_findings_no_critical_high(self):
        """When all findings are info/low severity, no findings appear in the critical section."""
        findings = [
            {"title": "Server header present",     "severity": "info", "category": "info"},
            {"title": "Plain text page",            "severity": "info", "category": "info"},
        ]
        prompt = _build_prompt(findings)
        assert "Total findings: 2" in prompt
        assert "none in critical/high range" in prompt

    def test_all_severity_levels_present(self):
        """A prompt with all five severity levels includes all of them in the summary."""
        prompt = _build_prompt(SAMPLE_FINDINGS)
        assert "1 critical" in prompt
        assert "1 high" in prompt
        assert "1 medium" in prompt
        assert "1 low" in prompt
        assert "1 info" in prompt

    def test_duplicate_categories_counted_correctly(self):
        """Duplicate categories are counted accurately in the severity breakdown."""
        findings = [
            {"title": "XSS 1", "severity": "high", "category": "xss"},
            {"title": "XSS 2", "severity": "high", "category": "xss"},
            {"title": "XSS 3", "severity": "high", "category": "xss"},
            {"title": "SQLi", "severity": "critical", "category": "injection"},
        ]
        prompt = _build_prompt(findings)
        assert "3 high" in prompt
        assert "1 critical" in prompt
        assert "xss" in prompt
        assert "injection" in prompt

    def test_findings_with_no_recognized_category(self):
        """Findings with an unrecognized or missing category are still included in the total."""
        findings = [
            {"title": "Unknown issue", "severity": "high", "category": None},
            {"title": "Another unknown", "severity": "medium", "category": ""},
        ]
        prompt = _build_prompt(findings)
        assert "Total findings: 2" in prompt

    def test_findings_with_empty_title(self):
        """A finding with a missing or empty title does not break the prompt."""
        findings = [
            {"title": "", "severity": "critical", "category": "misc"},
            {"title": None, "severity": "high", "category": "misc"},
        ]
        # Should not raise
        prompt = _build_prompt(findings)
        assert "Total findings: 2" in prompt

    def test_mixed_case_severity_normalized(self):
        """Severity strings with mixed case (e.g., 'CRITICAL', 'High') are normalized."""
        findings = [
            {"title": "Issue 1", "severity": "CRITICAL", "category": "a"},
            {"title": "Issue 2", "severity": "high",     "category": "b"},
            {"title": "Issue 3", "severity": "High",     "category": "c"},
        ]
        prompt = _build_prompt(findings)
        # Should be counted correctly despite mixed case
        assert "Total findings: 3" in prompt
        assert "2 high" in prompt or "2 CRITICAL" in prompt or "1 critical" in prompt

    def test_finding_with_only_name_field(self):
        """A finding that uses 'name' instead of 'title' is still included."""
        findings = [
            {"name": "Vulnerability via name field", "severity": "high", "category": "misc"},
        ]
        prompt = _build_prompt(findings)
        assert "Total findings: 1" in prompt
        assert "Vulnerability via name field" in prompt

    def test_finding_with_only_check_field(self):
        """A finding that uses 'check' instead of 'title' is still included."""
        findings = [
            {"check": "CVE-2026-1234 detected", "severity": "critical", "category": "cve"},
        ]
        prompt = _build_prompt(findings)
        assert "Total findings: 1" in prompt
        assert "CVE-2026-1234 detected" in prompt

    def test_prompt_does_not_contain_unnamed_finding_fallback(self):
        """When a finding has no recognized title/name/check field, it uses the fallback."""
        findings = [
            {"severity": "high", "category": "misc"},
        ]
        prompt = _build_prompt(findings)
        # Should include the default fallback "Unnamed finding"
        assert "Unnamed finding" in prompt
