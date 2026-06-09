"""
Unit tests for backend/secuscan/ai_summary.py

Run with:
    ./testing/test_python.sh
or directly:
    python -m pytest testing/backend/unit/test_ai_summary.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.secuscan.ai_summary import _build_prompt, generate_summary


SAMPLE_FINDINGS = [
    {"title": "SQL Injection in login form",       "severity": "critical", "category": "injection"},
    {"title": "Reflected XSS in search parameter", "severity": "high",     "category": "xss"},
    {"title": "Missing X-Frame-Options header",    "severity": "medium",   "category": "headers"},
    {"title": "Outdated jQuery version",            "severity": "low",      "category": "components"},
    {"title": "Server version disclosed",           "severity": "info",     "category": "information-disclosure"},
]


def _mock_response(text: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestBuildPrompt:
    def test_includes_total_count(self):
        assert "Total findings: 5" in _build_prompt(SAMPLE_FINDINGS)

    def test_includes_severity_counts(self):
        prompt = _build_prompt(SAMPLE_FINDINGS)
        assert "1 critical" in prompt
        assert "1 high" in prompt
        assert "1 medium" in prompt

    def test_top_findings_contains_critical_and_high(self):
        prompt = _build_prompt(SAMPLE_FINDINGS)
        assert "SQL Injection" in prompt
        assert "Reflected XSS" in prompt

    def test_low_and_info_not_in_top_findings_section(self):
        top_section = _build_prompt(SAMPLE_FINDINGS).split("Most critical findings:")[1]
        assert "Outdated jQuery" not in top_section
        assert "Server version" not in top_section

    def test_empty_findings_produces_valid_prompt(self):
        prompt = _build_prompt([])
        assert "Total findings: 0" in prompt
        assert "none in critical/high range" in prompt

    def test_no_hostnames_or_ips_in_prompt(self):
        prompt = _build_prompt([{
            "title": "Open redirect", "severity": "high", "category": "redirect",
            "target": "http://internal-db.corp:5432", "host": "10.0.0.1",
        }])
        assert "10.0.0.1" not in prompt
        assert "internal-db.corp" not in prompt

    def test_category_distribution_present(self):
        prompt = _build_prompt(SAMPLE_FINDINGS)
        assert any(cat in prompt for cat in ("injection", "xss", "headers"))


class TestGenerateSummary:
    def test_returns_summary_string(self):
        expected = "The scan found 5 findings including a critical SQL injection."
        with patch("backend.secuscan.ai_summary.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(expected)
            result = generate_summary(SAMPLE_FINDINGS, "gpt-4o-mini", "test-key")
        assert result == expected

    def test_strips_whitespace(self):
        with patch("backend.secuscan.ai_summary.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response("  Summary.  ")
            result = generate_summary(SAMPLE_FINDINGS, "gpt-4o-mini", "key")
        assert result == "Summary."

    def test_passes_base_url_to_client(self):
        with patch("backend.secuscan.ai_summary.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response("ok")
            generate_summary(
                SAMPLE_FINDINGS, model="llama3", api_key="ollama",
                base_url="http://localhost:11434/v1",
            )
            mock_cls.assert_called_once_with(
                api_key="ollama", base_url="http://localhost:11434/v1", timeout=15.0
            )

    def test_returns_empty_string_on_llm_exception(self):
        with patch("backend.secuscan.ai_summary.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = RuntimeError("conn refused")
            assert generate_summary(SAMPLE_FINDINGS, "gpt-4o-mini", "key") == ""

    def test_returns_empty_string_for_empty_findings(self):
        with patch("backend.secuscan.ai_summary.OpenAI") as mock_cls:
            result = generate_summary([], "gpt-4o-mini", "key")
        assert result == ""
        mock_cls.assert_not_called()

    def test_returns_empty_string_when_openai_none(self):
        with patch("backend.secuscan.ai_summary.OpenAI", None):
            result = generate_summary(SAMPLE_FINDINGS, "gpt-4o-mini", "key")
        assert result == ""


class TestReportGeneratorAiSummary:
    def _task(self):
        return {
            "id": "task-ai-test",
            "tool_name": "http_inspector",
            "plugin_id": "http_inspector",
            "target": "https://example.com",
            "status": "completed",
            "created_at": "2026-06-01T10:00:00",
        }

    def _result(self):
        return {
            "structured": {
                "findings": [{
                    "title": "Exposed admin panel",
                    "category": "Exposure",
                    "severity": "high",
                    "description": "Admin reachable without auth.",
                    "remediation": "Restrict access.",
                    "proof": "HTTP 200 /admin",
                    "cve": "CVE-2026-0001",
                }]
            }
        }

    def test_html_report_generates_without_ai_summary(self):
        from backend.secuscan.reporting import ReportGenerator
        html = ReportGenerator.generate_html_report(self._task(), self._result())
        assert "Exposed admin panel" in html
        assert "Executive Overview" in html
        assert "AI Executive Summary" not in html

    def test_pdf_report_generates_without_ai_summary(self):
        from backend.secuscan.reporting import ReportGenerator
        pdf_bytes = ReportGenerator.generate_pdf_report(self._task(), self._result())
        assert pdf_bytes.startswith(b"%PDF")

    def test_html_report_contains_ai_summary_when_enabled(self):
        from backend.secuscan.reporting import ReportGenerator
        summary_text = "Risk is high. Address the admin panel exposure immediately."
        with patch.object(ReportGenerator, "_get_ai_summary", return_value=summary_text):
            html = ReportGenerator.generate_html_report(self._task(), self._result())
        assert "AI Executive Summary" in html
        assert "Risk is high" in html

    def test_pdf_report_contains_ai_summary_when_enabled(self):
        from backend.secuscan.reporting import ReportGenerator
        summary_text = "Critical SQL injection found. Patch immediately."
        with patch.object(ReportGenerator, "_get_ai_summary", return_value=summary_text):
            html_src = ReportGenerator._generate_pdf_html_report(self._task(), self._result())
        assert "AI Executive Summary" in html_src
        assert "Critical SQL injection found" in html_src

    def test_get_ai_summary_returns_empty_when_disabled(self):
        from backend.secuscan.reporting import ReportGenerator
        with patch.object(ReportGenerator, "_get_ai_summary", return_value="") as mock_method:
            html = ReportGenerator.generate_html_report(self._task(), self._result())
        assert "AI Executive Summary" not in html

    def test_get_ai_summary_returns_empty_when_no_api_key(self):
        from backend.secuscan.reporting import ReportGenerator
        with patch("backend.secuscan.config.settings") as ms:
            ms.ai_summary_enabled = True
            ms.ai_summary_api_key = ""
            result = ReportGenerator._get_ai_summary([{"title": "x", "severity": "high"}])
        assert result == ""

    def test_sarif_report_unchanged(self):
        from backend.secuscan.reporting import ReportGenerator
        import json
        sarif_json = ReportGenerator.generate_sarif_report(self._task(), self._result())
        sarif = json.loads(sarif_json)
        assert sarif["version"] == "2.1.0"
        assert "ai_summary" not in str(sarif_json)