"""
Unit tests for backend.secuscan.routes._escape_like SQL injection guard.

The _escape_like function escapes SQLite LIKE wildcards (% and _) to prevent
pattern injection via user-supplied search input.

Run with:
    python3 -m pytest testing/backend/unit/test_routes_escape_like.py -v --noconftest
"""

from __future__ import annotations

import pytest

from backend.secuscan.routes_escape_helpers import _escape_like


class TestEscapeLike:
    def test_normal_string_unchanged(self):
        assert _escape_like("hello world") == "hello world"

    def test_percent_sign_escaped(self):
        assert _escape_like("50% off") == "50\\% off"

    def test_underscore_escaped(self):
        assert _escape_like("user_name") == "user\\_name"

    def test_backslash_escaped_first(self):
        # Backslashes must be escaped first to avoid double-escaping
        assert _escape_like("path\\to\\file") == "path\\\\to\\\\file"

    def test_multiple_wildcards_all_escaped(self):
        assert _escape_like("50%_discount") == "50\\%\\_discount"

    def test_empty_string_returns_empty(self):
        assert _escape_like("") == ""

    def test_mixed_content(self):
        result = _escape_like("50% off for user_name")
        assert result == "50\\% off for user\\_name"

    def test_only_percent_sign(self):
        assert _escape_like("%") == "\\%"

    def test_only_underscore(self):
        assert _escape_like("_") == "\\_"

    def test_only_backslash(self):
        assert _escape_like("\\") == "\\\\"

    def test_preserves_non_wildcard_characters(self):
        assert _escape_like("abc123!@#") == "abc123!@#"
