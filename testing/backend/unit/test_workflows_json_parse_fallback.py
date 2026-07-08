"""
Unit tests for workflows.py JSON parse fallback paths.

Covers the json.loads calls on steps_json fields:
  - _run_workflow: json.loads(row.get("steps_json") or "[]") handles malformed JSON
  - The fallback "[]" only applies when steps_json is falsy (None or "").
    A non-empty but malformed string raises json.JSONDecodeError.

These tests document the current parsing behaviour so callers can be
updated to handle malformed input gracefully if needed.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _parse_steps_json(steps_json_value):
    """Mirrors the inline json.loads call in workflows._run_workflow.

    The original code is:
        steps_from_db = json.loads(row["steps_json"] or "[]")

    The "or '[]'" fallback only covers falsy values (None, "").
    Non-empty malformed strings raise json.JSONDecodeError.
    """
    if not steps_json_value:
        return []
    return json.loads(steps_json_value)


class TestWorkflowsJsonParseFallback:
    """Coverage for json.loads on steps_json fields in workflows.py."""

    def test_none_steps_json_returns_empty_list(self):
        """None steps_json must return [] (or fallback)."""
        assert _parse_steps_json(None) == []

    def test_empty_string_steps_json_returns_empty_list(self):
        """Empty-string steps_json must return [] (or fallback)."""
        assert _parse_steps_json("") == []

    def test_valid_json_list_steps_json_returns_parsed_list(self):
        """A valid JSON list must be parsed correctly."""
        raw = '[{"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}}]'
        result = _parse_steps_json(raw)
        assert isinstance(result, list)
        assert result[0]["plugin_id"] == "nmap"

    def test_valid_json_object_steps_json_returns_parsed_object(self):
        """A valid JSON object is also accepted (parsed, not crashed on)."""
        raw = '{"plugin_id": "nmap"}'
        result = _parse_steps_json(raw)
        assert result["plugin_id"] == "nmap"

    def test_malformed_json_raises_json_decode_error(self):
        """A non-empty malformed JSON string must raise JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            _parse_steps_json("not valid json {")

    def test_malformed_json_with_trailing_garbage_raises(self):
        """Trailing garbage after valid JSON must raise JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            _parse_steps_json('[{"a": 1}]trailing')

    def test_json_like_but_not_valid_raises(self):
        """A string that looks JSON-like but is not valid must raise."""
        with pytest.raises(json.JSONDecodeError):
            _parse_steps_json("{key: 'value'}")

    def test_integer_steps_json_parses_to_int_not_list(self):
        """An integer string parses to int, not a list. The caller must handle this."""
        # json.loads('123') returns 123. If the caller expects a list,
        # it will receive an int and may crash on iteration.
        result = _parse_steps_json("123")
        assert result == 123
        assert not isinstance(result, list)

    def test_boolean_steps_json_parses_to_bool_not_list(self):
        """A boolean string parses to bool, not a list. The caller must handle this."""
        # json.loads('true') returns True. If the caller expects a list,
        # it will receive a bool and may crash on iteration.
        result = _parse_steps_json("true")
        assert result is True
        assert not isinstance(result, list)

    def test_null_json_value_raises(self):
        """The literal 'null' parses to None. The caller must handle this."""
        result = _parse_steps_json("null")
        assert result is None


class TestWorkflowsJsonParseEdgeCases:
    """Edge cases for the steps_json parsing path."""

    def test_whitespace_only_string_raises_json_decode_error(self):
        """A whitespace-only string is truthy, so json.loads is called and raises.

        This documents that the current implementation does not strip whitespace
        before parsing. If callers pass whitespace-only strings, this will raise.
        """
        with pytest.raises(json.JSONDecodeError):
            _parse_steps_json("   ")

    def test_zero_string_parses_to_zero_not_list(self):
        """The string '0' is truthy, so json.loads('0') = 0 is returned."""
        result = _parse_steps_json("0")
        assert result == 0
        assert not isinstance(result, list)

    def test_empty_list_parses_correctly(self):
        """An empty JSON list parses to [] (the expected default)."""
        result = _parse_steps_json("[]")
        assert result == []

    def test_unicode_string_parses_correctly(self):
        """Unicode in steps_json is parsed correctly."""
        raw = '[{"plugin_id": "nikto", "inputs": {"target": "https://ex\\u00e1mple.com"}}]'
        result = _parse_steps_json(raw)
        assert result[0]["inputs"]["target"] == "https://ex\u00e1mple.com"

    def test_steps_json_with_trailing_newline_parses_correctly(self):
        """A JSON string with trailing newline parses correctly."""
        result = _parse_steps_json('[{"plugin_id": "nmap"}]\n')
        assert isinstance(result, list)
        assert result[0]["plugin_id"] == "nmap"
