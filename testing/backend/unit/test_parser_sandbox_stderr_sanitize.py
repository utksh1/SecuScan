"""
Unit tests for _sanitize_stderr in backend/secuscan/parser_sandbox.py.

The function strips absolute file paths and Python line-number references from
stderr output before logging, preventing internal topology from leaking into
operator-facing diagnostic logs.
"""

from __future__ import annotations

import pytest

from backend.secuscan.parser_sandbox import _sanitize_stderr


class TestSanitizeStderrPaths:
    """Tests for path replacement in _sanitize_stderr."""

    def test_replaces_unix_absolute_path(self):
        """Unix-style absolute paths are replaced with [PATH]."""
        stderr = "Error in /home/user/project/parsers/sqli.py at line 42"
        result = _sanitize_stderr(stderr)
        assert "/home/user/project/parsers/sqli.py" not in result
        assert "[PATH]" in result

    def test_replaces_windows_absolute_path(self):
        """Windows absolute paths are replaced with [PATH]."""
        stderr = "Error in C:\\Users\\admin\\parsers\\xss.py at line 10"
        result = _sanitize_stderr(stderr)
        assert "C:\\Users\\admin\\parsers\\xss.py" not in result
        assert "[PATH]" in result

    def test_replaces_multiple_paths(self):
        """Multiple absolute paths in the same string are all replaced."""
        stderr = "ImportError in /a/b/c.py and ValueError in /x/y/z.py"
        result = _sanitize_stderr(stderr)
        assert "/a/b/c.py" not in result
        assert "/x/y/z.py" not in result
        assert result.count("[PATH]") == 2

    def test_replaces_paths_starting_with_slash(self):
        """Paths that start with / are replaced even if technically relative-ish."""
        stderr = "Error in /parsers/sqli.py"
        result = _sanitize_stderr(stderr)
        # /parsers has 7 chars after / so it matches the absolute-path pattern
        assert "/parsers/sqli.py" not in result

    def test_preserves_single_segment_paths(self):
        """Single-segment paths like /abc (fewer than 3 chars after /) are not replaced."""
        stderr = "Error in /ab"
        result = _sanitize_stderr(stderr)
        # /ab has only 2 chars after / which is below the {3,} minimum
        assert "/ab" in result


class TestSanitizeStderrLineNumbers:
    """Tests for line-number replacement in _sanitize_stderr."""

    def test_replaces_line_number_lowercase(self):
        """'line N' (lowercase) is replaced with [LINE]."""
        stderr = "SyntaxError at line 42"
        result = _sanitize_stderr(stderr)
        assert "line 42" not in result
        assert "[LINE]" in result

    def test_replaces_line_number_uppercase(self):
        """'Line N' (capitalized) is replaced with [LINE]."""
        stderr = "SyntaxError at Line 100"
        result = _sanitize_stderr(stderr)
        assert "Line 100" not in result
        assert "[LINE]" in result

    def test_replaces_multiple_line_numbers(self):
        """Multiple line number references are all replaced."""
        stderr = "Error at line 10 and line 20"
        result = _sanitize_stderr(stderr)
        assert "line 10" not in result
        assert "line 20" not in result
        assert result.count("[LINE]") == 2

    def test_replaces_line_numbers_case_insensitive(self):
        """Line number replacement is case-insensitive (matches LINE, Line, line)."""
        stderr = "line 1 LINE 2 Line 3"
        result = _sanitize_stderr(stderr)
        assert "line 1" not in result
        assert "LINE 2" not in result
        assert "Line 3" not in result
        assert result.count("[LINE]") == 3


class TestSanitizeStderrMixed:
    """Tests for mixed content with both paths and line numbers."""

    def test_replaces_both_paths_and_line_numbers(self):
        """Both paths and line numbers in the same string are replaced."""
        stderr = "Error in /home/user/file.py at line 42"
        result = _sanitize_stderr(stderr)
        assert "/home/user/file.py" not in result
        assert "line 42" not in result
        assert "[PATH]" in result
        assert "[LINE]" in result

    def test_replaces_paths_before_line_numbers(self):
        """Replacement order is path first, then line numbers."""
        # Both patterns match "line 42" differently; this tests the order is consistent
        stderr = "Error at line 1: /a/b/c.py"
        result = _sanitize_stderr(stderr)
        assert "/a/b/c.py" not in result
        assert "line 1" not in result


class TestSanitizeStderrNoMatch:
    """Tests for input that contains no paths or line numbers."""

    def test_returns_unchanged_when_no_paths_or_lines(self):
        """Input with no paths or line numbers is returned unchanged."""
        stderr = "Connection refused to remote host"
        result = _sanitize_stderr(stderr)
        assert result == stderr

    def test_returns_empty_string(self):
        """Empty string input returns empty string."""
        result = _sanitize_stderr("")
        assert result == ""


class TestSanitizeStderrTruncation:
    """Tests for max_chars truncation."""

    def test_truncates_to_default_500_chars(self):
        """Output is truncated to max_chars default (500)."""
        stderr = "x" * 1000
        result = _sanitize_stderr(stderr)
        assert len(result) == 500

    def test_respects_custom_max_chars(self):
        """Custom max_chars parameter controls truncation length."""
        stderr = "y" * 200
        result = _sanitize_stderr(stderr, max_chars=100)
        assert len(result) == 100

    def test_truncation_applies_after_replacement(self):
        """Truncation happens after path and line-number replacement."""
        # Create a string longer than 500 with paths
        stderr = ("/home/user/file.py " * 100).strip()
        result = _sanitize_stderr(stderr, max_chars=200)
        assert len(result) == 200
        # Paths should still be replaced
        assert "/home/user/file.py" not in result

    def test_max_chars_of_zero(self):
        """max_chars=0 returns empty string."""
        result = _sanitize_stderr("some text", max_chars=0)
        assert result == ""
