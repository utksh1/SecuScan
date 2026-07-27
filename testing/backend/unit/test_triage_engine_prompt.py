"""
Unit tests for _build_triage_prompt in backend/secuscan/triage_engine.

Imports the real production function so any regression in prompt construction
is caught by these tests.
"""

from __future__ import annotations

import pytest

from backend.secuscan.triage_engine import _build_triage_prompt


# ---------------------------------------------------------------------------
# _build_triage_prompt
# ---------------------------------------------------------------------------


class TestBuildTriagePromptNormalFinding:
    def test_full_finding(self):
        """A fully-populated finding produces a well-formed prompt."""
        finding = {
            "title": "SQL Injection in login",
            "category": "sqli",
            "severity": "critical",
            "description": "User input not sanitized",
        }
        context = {
            "snippet": "query = 'SELECT * FROM users WHERE id = ' + user_id",
            "variables": ["user_id"],
            "file": "auth.py",
            "line": "42",
        }
        prompt = _build_triage_prompt(finding, context)
        assert "Finding: SQL Injection in login" in prompt
        assert "Category: sqli" in prompt
        assert "Severity: critical" in prompt
        assert "query = 'SELECT * FROM users WHERE id = '" in prompt
        assert "Variables referenced near the flagged line: user_id" in prompt
        assert "File: auth.py (line 42)" in prompt
        assert '"verdict":' in prompt

    def test_finding_title_none(self):
        """None title falls back to 'Untitled finding'."""
        finding = {"title": None, "category": "xss", "severity": "high"}
        context = {"snippet": "document.write(userInput)", "variables": [], "file": "app.js", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "Finding: Untitled finding" in prompt

    def test_finding_title_missing(self):
        """Missing title falls back to 'Untitled finding'."""
        finding = {"category": "xss", "severity": "high"}
        context = {"snippet": "document.write(userInput)", "variables": [], "file": "app.js", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "Finding: Untitled finding" in prompt

    def test_finding_category_none(self):
        """None category defaults to 'unknown'."""
        finding = {"title": "Bug", "category": None, "severity": "low"}
        context = {"snippet": "x", "variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "Category: unknown" in prompt

    def test_finding_severity_none(self):
        """None severity defaults to 'unknown'."""
        finding = {"title": "Bug", "category": "misc", "severity": None}
        context = {"snippet": "x", "variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "Severity: unknown" in prompt

    def test_finding_description_empty(self):
        """Empty description shows '(none provided)'."""
        finding = {"title": "Bug", "category": "misc", "severity": "info", "description": ""}
        context = {"snippet": "x", "variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "Description: (none provided)" in prompt

    def test_context_snippet_none(self):
        """None snippet falls back to '(no source snippet available)'."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"snippet": None, "variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "(no source snippet available)" in prompt

    def test_context_snippet_missing(self):
        """Missing snippet falls back to '(no source snippet available)'."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "(no source snippet available)" in prompt

    def test_context_variables_empty(self):
        """Empty variables list shows '(none identified)'."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"snippet": "x = 1", "variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "Variables referenced near the flagged line: (none identified)" in prompt

    def test_context_variables_multiple(self):
        """Multiple variables are joined with commas."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"snippet": "x", "variables": ["user_id", "password", "token"], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "user_id, password, token" in prompt

    def test_context_file_none(self):
        """None file shows '(unknown file)'."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"snippet": "x", "variables": [], "file": None, "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert "File: (unknown file)" in prompt

    def test_context_line_none(self):
        """None line shows '?'."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"snippet": "x", "variables": [], "file": "f", "line": None}
        prompt = _build_triage_prompt(finding, context)
        assert "line ?" in prompt

    def test_special_characters_in_snippet(self):
        """Special characters in snippet are preserved verbatim."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {
            "snippet": 'query = "SELECT * FROM t WHERE x = \'" + y + "\'"',
            "variables": [],
            "file": "f",
            "line": "1",
        }
        prompt = _build_triage_prompt(finding, context)
        assert 'query = "SELECT * FROM t WHERE x = \'" + y + "\'"' in prompt

    def test_prompt_contains_required_response_format(self):
        """Prompt specifies the three required response keys."""
        finding = {"title": "Bug", "category": "misc", "severity": "info"}
        context = {"snippet": "x", "variables": [], "file": "f", "line": "1"}
        prompt = _build_triage_prompt(finding, context)
        assert '"verdict":' in prompt
        assert '"confidence":' in prompt
        assert '"reasoning":' in prompt
        assert '"remediation":' in prompt
        assert '"true_positive"' in prompt
        assert '"false_positive"' in prompt
        assert '"needs_review"' in prompt
