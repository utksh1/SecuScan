"""
Unit tests for internal helpers in backend/secuscan/triage_engine.py.

Covers:
- _build_triage_prompt: prompt contains finding fields and instruction structure
- _extract_variable_hints: extracts Python variable names from code snippets
- Both functions are import-safe (no FastAPI/database dependencies)
"""

from __future__ import annotations

import pytest

from backend.secuscan.triage_engine import (
    _build_triage_prompt,
    _extract_variable_hints,
)


# ---------------------------------------------------------------------------
# _build_triage_prompt
# ---------------------------------------------------------------------------

class TestBuildTriagePrompt:
    def test_prompt_contains_finding_title(self):
        finding = {"title": "SQL Injection in login"}
        context = {"snippet": "query = f'", "file": "app.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "SQL Injection in login" in prompt

    def test_prompt_contains_category(self):
        finding = {"title": "XSS", "category": "code security"}
        context = {"snippet": "innerHTML = x", "file": "x.js", "line": 10, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "code security" in prompt

    def test_prompt_contains_severity(self):
        finding = {"title": "Issue", "severity": "high"}
        context = {"snippet": "code", "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "high" in prompt

    def test_prompt_contains_description(self):
        finding = {"title": "Issue", "description": "User input concatenated into SQL query"}
        context = {"snippet": "query = x", "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "User input concatenated into SQL query" in prompt

    def test_prompt_contains_file_and_line(self):
        finding = {"title": "Issue"}
        context = {"snippet": "x = 1", "file": "app/routes.py", "line": 42, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "app/routes.py" in prompt
        assert "42" in prompt

    def test_prompt_contains_variables(self):
        finding = {"title": "Issue"}
        context = {"snippet": "x = 1", "file": "f.py", "line": 1, "variables": ["query", "user_input"]}
        prompt = _build_triage_prompt(finding, context)
        assert "query" in prompt
        assert "user_input" in prompt

    def test_prompt_contains_snippet(self):
        finding = {"title": "Issue"}
        context = {"snippet": "def vulnerable(): pass", "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "def vulnerable(): pass" in prompt

    def test_prompt_contains_verdict_instruction(self):
        finding = {"title": "Issue"}
        context = {"snippet": "x = 1", "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "true_positive" in prompt
        assert "false_positive" in prompt
        assert "needs_review" in prompt

    def test_prompt_contains_confidence_instruction(self):
        finding = {"title": "Issue"}
        context = {"snippet": "x = 1", "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "confidence" in prompt.lower()

    def test_prompt_contains_remediation_instruction(self):
        finding = {"title": "Issue"}
        context = {"snippet": "x = 1", "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "remediation" in prompt.lower()

    def test_prompt_handles_missing_finding_fields(self):
        finding = {}
        context = {"snippet": "code", "file": "", "line": 0, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should not crash with KeyError

    def test_prompt_handles_none_context_variables(self):
        finding = {"title": "Issue"}
        context = {"snippet": "x", "file": "f.py", "line": 1, "variables": None}
        prompt = _build_triage_prompt(finding, context)
        assert "(none identified)" in prompt

    def test_prompt_handles_none_snippet(self):
        finding = {"title": "Issue"}
        context = {"snippet": None, "file": "f.py", "line": 1, "variables": []}
        prompt = _build_triage_prompt(finding, context)
        assert "(no source snippet available)" in prompt

    def test_prompt_returns_string(self):
        finding = {"title": "Test", "category": "cat", "severity": "low", "description": "desc"}
        context = {"snippet": "x=1", "file": "f.py", "line": 1, "variables": []}
        assert isinstance(_build_triage_prompt(finding, context), str)


# ---------------------------------------------------------------------------
# _extract_variable_hints
# ---------------------------------------------------------------------------

class TestExtractVariableHints:
    def test_extracts_assignment_targets(self):
        finding = {"proof": "query = f'SELECT * FROM {user_id}'"}
        hints = _extract_variable_hints(finding)
        assert "query" in hints

    def test_extracts_from_multiple_assignments(self):
        finding = {"proof": "user_id = req.args.get('id'); query = f'WHERE id={user_id}'"}
        hints = _extract_variable_hints(finding)
        assert "user_id" in hints
        assert "query" in hints

    def test_extracts_from_description_field(self):
        finding = {"description": "Variable data = user controlled input flows to query = db.execute(sql)"}
        hints = _extract_variable_hints(finding)
        assert "data" in hints
        assert "query" in hints

    def test_extracts_from_title_field(self):
        finding = {"title": "SSRF: url = requests.get(target)"}
        hints = _extract_variable_hints(finding)
        assert "url" in hints

    def test_deduplicates_in_order(self):
        finding = {"proof": "x = 1; y = 2; x = 3"}
        hints = _extract_variable_hints(finding)
        assert hints.count("x") == 1
        # First occurrence preserved
        assert hints[0] == "x"

    def test_caps_at_10_variables(self):
        proof = " = ".join(f"var{i} = {i}" for i in range(20))
        finding = {"proof": proof}
        hints = _extract_variable_hints(finding)
        assert len(hints) <= 10

    def test_returns_empty_list_for_no_matches(self):
        finding = {"proof": "no assignments here"}
        hints = _extract_variable_hints(finding)
        assert hints == []

    def test_ignores_non_python_identifiers(self):
        finding = {"proof": "123abc = 1; _ = 2"}
        hints = _extract_variable_hints(finding)
        assert "123abc" not in hints

    def test_handles_empty_finding(self):
        hints = _extract_variable_hints({})
        assert isinstance(hints, list)

    def test_handles_none_values(self):
        finding = {"proof": None, "description": None, "title": None}
        hints = _extract_variable_hints(finding)
        assert isinstance(hints, list)

    def test_extraction_is_deterministic(self):
        finding = {"proof": "x = 1; y = 2; z = 3"}
        a = _extract_variable_hints(finding)
        b = _extract_variable_hints(finding)
        assert a == b
