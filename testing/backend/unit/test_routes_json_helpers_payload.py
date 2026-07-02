"""
Unit tests for _json_payload helper in backend.secuscan.routes.

Tests the JSON serialization helper used by notification, vault, and
scan-task routes to safely serialize Python values to JSON strings.
"""

import pytest
from backend.secuscan.routes_json_helpers import _json_payload


class TestJsonPayload:
    def test_dict_value_serialized(self):
        result = _json_payload({"key": "val"}, "[]")
        assert result == '{"key": "val"}'

    def test_list_value_serialized(self):
        result = _json_payload(["a", "b", "c"], "[]")
        assert result == '["a", "b", "c"]'

    def test_string_value_serialized(self):
        result = _json_payload("hello world", "[]")
        assert result == '"hello world"'

    def test_none_value_returns_json_parsed_from_fallback(self):
        result = _json_payload(None, '{"default": true}')
        assert result == '{"default": true}'

    def test_none_value_with_invalid_fallback_raises(self):
        with pytest.raises(Exception):
            _json_payload(None, "not-valid-json")

    def test_integer_value_serialized(self):
        result = _json_payload(42, "[]")
        assert result == "42"

    def test_boolean_true_serialized(self):
        result = _json_payload(True, "[]")
        assert result == "true"

    def test_boolean_false_serialized(self):
        result = _json_payload(False, "[]")
        assert result == "false"

    def test_empty_dict_serialized(self):
        result = _json_payload({}, "[]")
        assert result == "{}"

    def test_empty_list_serialized(self):
        result = _json_payload([], "[]")
        assert result == "[]"

    def test_nested_structure_serialized(self):
        data = {"items": [1, 2, {"nested": True}], "count": 2}
        result = _json_payload(data, "{}")
        assert '"items"' in result
        assert '"nested": true' in result
        assert '"count": 2' in result

    def test_fallback_only_used_when_none(self):
        result = _json_payload(0, '{"fallback": true}')
        # 0 is not None, so json.dumps is used
        assert result == "0"
        assert "fallback" not in result
