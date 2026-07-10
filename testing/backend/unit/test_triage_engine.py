"""
Unit tests for backend/secuscan/triage_engine.py

Run with:
    ./testing/test_python.sh
or directly:
    python -m pytest testing/backend/unit/test_triage_engine.py -v
"""

from __future__ import annotations

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from backend.secuscan.triage_engine import (
    extract_code_context,
    is_eligible_for_triage,
    triage_finding,
    triage_findings,
)


def _mock_response(text: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _sast_finding(**overrides) -> dict:
    finding = {
        "title": "Possible SQL Injection",
        "category": "code security",
        "severity": "high",
        "description": "User input concatenated into query = build_sql(user_id)",
        "proof": "query = f\"SELECT * FROM users WHERE id={user_id}\"",
        "metadata": {"file": "app/db.py", "line": 42},
        "confidence": 0.4,
    }
    finding.update(overrides)
    return finding


class TestIsEligibleForTriage:
    def test_eligible_sast_finding(self):
        assert is_eligible_for_triage(_sast_finding()) is True

    def test_ineligible_wrong_category(self):
        finding = _sast_finding(category="attack surface")
        assert is_eligible_for_triage(finding) is False

    def test_ineligible_already_triaged(self):
        finding = _sast_finding(triage_verdict="true_positive")
        assert is_eligible_for_triage(finding) is False

    def test_ineligible_high_confidence_skips(self):
        finding = _sast_finding(confidence=0.95)
        assert is_eligible_for_triage(finding, min_confidence_to_skip=0.9) is False

    def test_eligible_respects_custom_categories(self):
        finding = _sast_finding(category="custom-sast-tool")
        assert is_eligible_for_triage(finding, eligible_categories=["custom-sast-tool"]) is True


class TestExtractCodeContext:
    def test_falls_back_to_proof_without_file(self):
        finding = _sast_finding(metadata={})
        context = extract_code_context(finding)
        assert context["snippet"] == finding["proof"]
        assert context["file"] == ""

    def test_reads_source_file_when_available(self, tmp_path):
        source = tmp_path / "db.py"
        source.write_text(
            textwrap.dedent(
                """\
                import sqlite3

                def build_sql(user_id):
                    # line 4
                    # line 5
                    query = f"SELECT * FROM users WHERE id={user_id}"
                    return query
                """
            )
        )
        finding = _sast_finding(metadata={"file": "db.py", "line": 6})
        context = extract_code_context(finding, repo_root=str(tmp_path))
        assert "SELECT * FROM users" in context["snippet"]
        assert context["file"] == "db.py"
        assert context["line"] == 6

    def test_missing_file_falls_back_gracefully(self):
        finding = _sast_finding(metadata={"file": "does/not/exist.py", "line": 10})
        context = extract_code_context(finding)
        assert context["snippet"] == finding["proof"]

    def test_extracts_variable_hints(self):
        finding = _sast_finding()
        context = extract_code_context(finding)
        assert "query" in context["variables"]


class TestTriageFinding:
    def test_returns_parsed_verdict(self):
        payload = (
            '{"verdict": "false_positive", "confidence": 0.87, '
            '"reasoning": "user_id is cast to int upstream", "remediation": ""}'
        )
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(payload)
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="test-key")
        assert result["triage_verdict"] == "false_positive"
        assert result["triage_confidence"] == 0.87
        assert "user_id" in result["triage_reasoning"]

    def test_tolerates_markdown_fenced_json(self):
        payload = '```json\n{"verdict": "true_positive", "confidence": 0.9, "reasoning": "x", "remediation": "y"}\n```'
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(payload)
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="key")
        assert result["triage_verdict"] == "true_positive"

    def test_returns_none_on_invalid_json(self):
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response("not json")
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="key")
        assert result is None

    def test_returns_none_on_unrecognized_verdict(self):
        payload = '{"verdict": "maybe", "confidence": 0.5, "reasoning": "x", "remediation": ""}'
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(payload)
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="key")
        assert result is None

    def test_returns_none_on_llm_exception(self):
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = RuntimeError("timeout")
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="key")
        assert result is None

    def test_returns_none_when_openai_not_installed(self):
        with patch("backend.secuscan.triage_engine.OpenAI", None):
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="key")
        assert result is None

    def test_clamps_out_of_range_confidence(self):
        payload = '{"verdict": "true_positive", "confidence": 4.2, "reasoning": "x", "remediation": "y"}'
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(payload)
            result = triage_finding(_sast_finding(), model="gpt-4o-mini", api_key="key")
        assert result["triage_confidence"] == 1.0


class TestTriageFindings:
    def test_annotates_eligible_findings_in_place(self):
        findings = [_sast_finding()]
        payload = '{"verdict": "false_positive", "confidence": 0.8, "reasoning": "sanitized", "remediation": ""}'
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(payload)
            result = triage_findings(findings, model="gpt-4o-mini", api_key="key")
        assert result[0]["triage_verdict"] == "false_positive"
        assert "AI triage" in result[0]["confidence_reason"]

    def test_skips_ineligible_findings(self):
        findings = [_sast_finding(category="attack surface")]
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            triage_findings(findings, model="gpt-4o-mini", api_key="key")
            mock_cls.assert_not_called()
        assert "triage_verdict" not in findings[0]

    def test_leaves_finding_unmodified_when_llm_fails(self):
        findings = [_sast_finding()]
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = RuntimeError("down")
            result = triage_findings(findings, model="gpt-4o-mini", api_key="key")
        assert "triage_verdict" not in result[0]

    def test_empty_list_returns_empty(self):
        assert triage_findings([], model="gpt-4o-mini", api_key="key") == []

    def test_non_dict_entries_are_skipped_safely(self):
        findings = [_sast_finding(), "not-a-dict"]  # type: ignore[list-item]
        payload = '{"verdict": "true_positive", "confidence": 0.7, "reasoning": "x", "remediation": "y"}'
        with patch("backend.secuscan.triage_engine.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = _mock_response(payload)
            result = triage_findings(findings, model="gpt-4o-mini", api_key="key")
        assert result[0]["triage_verdict"] == "true_positive"
        assert result[1] == "not-a-dict"


class TestFindingIntelligenceIntegration:
    """Confirm the opt-in hook in finding_intelligence stays inert by default."""

    def test_disabled_by_default_settings(self):
        from backend.secuscan.config import settings

        assert settings.triage_engine_enabled is False
        assert settings.triage_engine_api_key == ""
