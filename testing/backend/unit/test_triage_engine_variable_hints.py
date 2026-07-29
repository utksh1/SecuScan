"""
Unit tests for backend.secuscan.triage_engine._extract_variable_hints.

Run with:
    python3 -m pytest testing/backend/unit/test_triage_engine_variable_hints.py -v --noconftest
"""

from __future__ import annotations

import pytest

from backend.secuscan.triage_engine import _extract_variable_hints


def _finding(**overrides) -> dict:
    base = {
        "title": "SQL Injection",
        "proof": "query = f\"SELECT * FROM users WHERE id={user_id}\"",
        "description": "User input concatenated into SQL query",
    }
    base.update(overrides)
    return base


class TestExtractVariableHints:
    def test_extracts_from_proof(self):
        # Only matches VAR = patterns, not f-string interpolations
        finding = _finding(proof="query = user_input; result = safe_value")
        result = _extract_variable_hints(finding)
        assert "query" in result
        assert "result" in result

    def test_extracts_from_description(self):
        finding = _finding(
            title="",
            proof="",
            description="The vulnerable param = user_data flows unsanitized into sink = eval()",
        )
        result = _extract_variable_hints(finding)
        assert "param" in result
        assert "sink" in result

    def test_extracts_from_title(self):
        finding = _finding(
            title="Command Injection: cmd_arg = user_input is passed to subprocess",
            proof="",
            description="",
        )
        result = _extract_variable_hints(finding)
        assert "cmd_arg" in result

    def test_deduplication_preserves_order(self):
        finding = _finding(
            title="XSS in var",
            proof="var = user_input; other_var = var",
            description="var appears multiple times",
        )
        result = _extract_variable_hints(finding)
        # var should appear only once (first occurrence)
        assert result.count("var") == 1
        assert "other_var" in result

    def test_cap_at_10_results(self):
        # Each proof line has a unique var
        lines = [f"var{i} = input()" for i in range(15)]
        finding = _finding(title="", proof="; ".join(lines), description="")
        result = _extract_variable_hints(finding)
        assert len(result) == 10

    def test_empty_finding_returns_empty_list(self):
        result = _extract_variable_hints({})
        assert result == []

    def test_no_matches_returns_empty_list(self):
        finding = _finding(title="No variables here", proof="just text", description="no code")
        result = _extract_variable_hints(finding)
        assert result == []

    def test_extracts_var_names_followed_by_equals(self):
        finding = _finding(
            title="",
            proof="query = user_input; result = sanitize(data); flag = True",
            description="",
        )
        result = _extract_variable_hints(finding)
        assert "query" in result
        assert "result" in result
        assert "flag" in result

    def test_none_values_handled_gracefully(self):
        finding = {"title": None, "proof": None, "description": "var = value"}
        result = _extract_variable_hints(finding)
        assert "var" in result
