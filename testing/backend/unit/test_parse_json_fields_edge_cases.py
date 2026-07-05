"""
Additional unit tests for parse_json_fields edge cases in
backend.secuscan.routes_json_helpers.

These complement the existing 6 tests in test_routes_json_helpers.py which
cover the happy path. These tests cover edge cases: empty field list,
whitespace JSON, falsy parsed values, and empty rows list.
"""

import pytest
from backend.secuscan.routes_json_helpers import parse_json_fields


class TestParseJsonFieldsEdgeCases:
    def test_empty_fields_list_returns_rows_unchanged(self):
        rows = [{"name": "test", "value": "123"}]
        result = parse_json_fields(rows, [])
        assert result == rows
        assert result[0]["name"] == "test"
        assert result[0]["value"] == "123"

    def test_whitespace_only_json_string_preserved(self):
        rows = [{"field": "   "}]
        result = parse_json_fields(rows, ["field"])
        assert result[0]["field"] == "   "

    def test_valid_json_array_parsed(self):
        rows = [{"items": '["a", "b", "c"]'}]
        result = parse_json_fields(rows, ["items"])
        assert result[0]["items"] == ["a", "b", "c"]

    def test_valid_json_number_parsed(self):
        rows = [{"count": "42"}]
        result = parse_json_fields(rows, ["count"])
        assert result[0]["count"] == 42

    def test_valid_json_boolean_true_parsed(self):
        rows = [{"flag": "true"}]
        result = parse_json_fields(rows, ["flag"])
        assert result[0]["flag"] is True

    def test_valid_json_boolean_false_parsed(self):
        rows = [{"flag": "false"}]
        result = parse_json_fields(rows, ["flag"])
        assert result[0]["flag"] is False

    def test_valid_json_null_parsed(self):
        rows = [{"val": "null"}]
        result = parse_json_fields(rows, ["val"])
        assert result[0]["val"] is None

    def test_valid_json_object_parsed(self):
        rows = [{"meta": '{"source": "scan"}'}]
        result = parse_json_fields(rows, ["meta"])
        assert result[0]["meta"] == {"source": "scan"}

    def test_falsy_integer_zero_preserved_after_parse(self):
        rows = [{"count": "0"}]
        result = parse_json_fields(rows, ["count"])
        assert result[0]["count"] == 0

    def test_falsy_boolean_false_preserved(self):
        rows = [{"active": "false"}]
        result = parse_json_fields(rows, ["active"])
        assert result[0]["active"] is False

    def test_mixed_rows_some_valid_json_some_not(self):
        rows = [
            {"field": '{"ok": true}'},
            {"field": "not-json"},
            {"field": "  invalid json  "},
            {"other": "data"},
        ]
        result = parse_json_fields(rows, ["field"])
        assert result[0]["field"] == {"ok": True}
        assert result[1]["field"] == "not-json"
        assert result[2]["field"] == "  invalid json  "
        assert result[3] == {"other": "data"}

    def test_empty_rows_list_returns_empty(self):
        result = parse_json_fields([], ["field"])
        assert result == []

    def test_field_not_in_row_skipped(self):
        rows = [{"name": "test", "other_field": '{"x":1}'}]
        result = parse_json_fields(rows, ["missing_field", "other_field"])
        assert result[0]["other_field"] == {"x": 1}
        assert "missing_field" not in result[0]
