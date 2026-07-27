"""
Unit tests for _parse_triage_response in backend/secuscan/triage_engine.

Imports the real production function to catch regressions in LLM response parsing.
"""

from __future__ import annotations

import pytest

from backend.secuscan.triage_engine import _parse_triage_response


# ---------------------------------------------------------------------------
# _parse_triage_response
# ---------------------------------------------------------------------------


class TestParseTriageResponseValidVerdicts:
    def test_true_positive(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": 0.9, "reasoning": "user input reaches SQL", "remediation": "use parameterized query"}'
        )
        assert result is not None
        assert result["triage_verdict"] == "true_positive"
        assert result["triage_confidence"] == 0.9
        assert result["triage_reasoning"] == "user input reaches SQL"
        assert result["triage_remediation"] == "use parameterized query"

    def test_false_positive(self):
        result = _parse_triage_response(
            '{"verdict": "false_positive", "confidence": 0.85, "reasoning": "already sanitized", "remediation": ""}'
        )
        assert result is not None
        assert result["triage_verdict"] == "false_positive"
        assert result["triage_confidence"] == 0.85

    def test_needs_review(self):
        result = _parse_triage_response(
            '{"verdict": "needs_review", "confidence": 0.6, "reasoning": "partial data flow", "remediation": "investigate context"}'
        )
        assert result is not None
        assert result["triage_verdict"] == "needs_review"


class TestParseTriageResponseVerdictNormalization:
    def test_verdict_case_insensitive(self):
        result = _parse_triage_response(
            '{"verdict": "TRUE_POSITIVE", "confidence": 0.8, "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_verdict"] == "true_positive"

    def test_verdict_whitespace_normalized(self):
        result = _parse_triage_response(
            '{"verdict": "  false_positive  ", "confidence": 0.8, "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_verdict"] == "false_positive"

    def test_verdict_missing_returns_none(self):
        result = _parse_triage_response('{"confidence": 0.8, "reasoning": "x", "remediation": "y"}')
        assert result is None

    def test_verdict_empty_string_returns_none(self):
        result = _parse_triage_response('{"verdict": "", "confidence": 0.8, "reasoning": "x", "remediation": "y"}')
        assert result is None


class TestParseTriageResponseInvalidVerdicts:
    def test_unrecognized_verdict_returns_none(self):
        result = _parse_triage_response(
            '{"verdict": "low", "confidence": 0.8, "reasoning": "x", "remediation": "y"}'
        )
        assert result is None

    def test_unrecognized_verdict_returns_none_explicit(self):
        result = _parse_triage_response(
            '{"verdict": "informational", "confidence": 0.8, "reasoning": "x", "remediation": "y"}'
        )
        assert result is None


class TestParseTriageResponseInvalidJson:
    def test_not_json_returns_none(self):
        result = _parse_triage_response("this is not json")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_triage_response("")
        assert result is None

    def test_whitespace_only_returns_none(self):
        result = _parse_triage_response("   \n  ")
        assert result is None

    def test_malformed_json_returns_none(self):
        result = _parse_triage_response('{"verdict": "true_positive" missing comma}')
        assert result is None


class TestParseTriageResponseMarkdownFenced:
    def test_markdown_fenced_json_accepted(self):
        result = _parse_triage_response(
            '```json\n{"verdict": "needs_review", "confidence": 0.7, "reasoning": "partial", "remediation": ""}\n```'
        )
        assert result is not None
        assert result["triage_verdict"] == "needs_review"
        assert result["triage_confidence"] == 0.7

    def test_markdown_fenced_without_json_label_accepted(self):
        result = _parse_triage_response(
            '```\n{"verdict": "false_positive", "confidence": 0.9, "reasoning": "safe", "remediation": ""}\n```'
        )
        assert result is not None
        assert result["triage_verdict"] == "false_positive"


class TestParseTriageResponseConfidence:
    def test_confidence_within_range(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": 0.75, "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_confidence"] == 0.75

    def test_confidence_below_zero_clamped(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": -0.5, "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_confidence"] == 0.0

    def test_confidence_above_one_clamped(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": 1.5, "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_confidence"] == 1.0

    def test_confidence_missing_defaults_to_half(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_confidence"] == 0.5

    def test_confidence_non_numeric_defaults_to_half(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": "high", "reasoning": "x", "remediation": "y"}'
        )
        assert result is not None
        assert result["triage_confidence"] == 0.5


class TestParseTriageResponseOptionalFields:
    def test_missing_reasoning_returns_empty_string(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": 0.8, "remediation": "fix it"}'
        )
        assert result is not None
        assert result["triage_reasoning"] == ""

    def test_missing_remediation_returns_empty_string(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": 0.8, "reasoning": "unreachable"}'
        )
        assert result is not None
        assert result["triage_remediation"] == ""

    def test_extra_fields_ignored(self):
        result = _parse_triage_response(
            '{"verdict": "true_positive", "confidence": 0.8, "reasoning": "x", "remediation": "y", "extra_field": "ignored"}'
        )
        assert result is not None
        assert "extra_field" not in result
