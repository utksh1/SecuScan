"""
Unit tests for backend/secuscan/routes_json_helpers _json_payload edge cases.

_json_payload returns JSON-encoded values with fallback handling. Existing tests
cover the primary cases; this file adds edge case coverage for bool, float,
nested structures, and error conditions.

Run with:
    python3 -m pytest testing/backend/unit/test_routes_json_payload.py -v --noconftest
"""

from __future__ import annotations

import json

import pytest

from backend.secuscan.routes_json_helpers import _json_payload


class TestJsonPayloadBoolValues:
    """Tests for bool value handling."""

    def test_bool_true_serialises_to_true(self):
        """_json_payload with value=True must produce valid JSON with true."""
        result = _json_payload(True, "{}")
        parsed = json.loads(result)
        assert parsed is True

    def test_bool_false_serialises_to_false(self):
        """_json_payload with value=False must produce valid JSON with false."""
        result = _json_payload(False, "{}")
        parsed = json.loads(result)
        assert parsed is False

    def test_bool_value_replaces_none(self):
        """_json_payload with None value must use fallback, not bool."""
        result = _json_payload(None, '{"fallback": "used"}')
        parsed = json.loads(result)
        assert parsed == {"fallback": "used"}


class TestJsonPayloadFloatValues:
    """Tests for float value handling."""

    def test_float_positive_serialises_correctly(self):
        """_json_payload with a positive float must produce correct JSON."""
        result = _json_payload(3.14159, "{}")
        parsed = json.loads(result)
        assert parsed == 3.14159

    def test_float_negative_serialises_correctly(self):
        """_json_payload with a negative float must produce correct JSON."""
        result = _json_payload(-273.15, "{}")
        parsed = json.loads(result)
        assert parsed == -273.15

    def test_float_zero_serialises_correctly(self):
        """_json_payload with 0.0 must produce correct JSON."""
        result = _json_payload(0.0, "{}")
        parsed = json.loads(result)
        assert parsed == 0.0

    def test_float_scientific_notation_serialises_correctly(self):
        """_json_payload with scientific notation float must serialise correctly."""
        result = _json_payload(1.23e-10, "{}")
        parsed = json.loads(result)
        assert parsed == 1.23e-10


class TestJsonPayloadNestedStructures:
    """Tests for nested dict/list handling."""

    def test_nested_dict_serialises_correctly(self):
        """_json_payload with a nested dict must produce correct JSON."""
        value = {"outer": {"inner": {"key": "value"}}, "list": [1, 2, 3]}
        result = _json_payload(value, "{}")
        parsed = json.loads(result)
        assert parsed == value

    def test_nested_list_serialises_correctly(self):
        """_json_payload with a nested list must produce correct JSON."""
        value = [[1, 2], [3, 4], {"nested": "dict"}]
        result = _json_payload(value, "{}")
        parsed = json.loads(result)
        assert parsed == value

    def test_mixed_nested_structure(self):
        """_json_payload with a mixed nested structure must serialise correctly."""
        value = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False},
            ],
            "count": 2,
        }
        result = _json_payload(value, "{}")
        parsed = json.loads(result)
        assert parsed == value


class TestJsonPayloadNoneHandling:
    """Tests for None value handling."""

    def test_none_value_uses_fallback(self):
        """_json_payload with None must use the fallback JSON string."""
        result = _json_payload(None, '{"default": true}')
        parsed = json.loads(result)
        assert parsed == {"default": True}

    def test_none_value_with_object_fallback(self):
        """_json_payload with None and an object fallback must parse correctly."""
        result = _json_payload(None, '{"tasks": [], "enabled": false}')
        parsed = json.loads(result)
        assert parsed == {"tasks": [], "enabled": False}


class TestJsonPayloadInvalidFallback:
    """Tests for invalid fallback JSON handling."""

    def test_invalid_fallback_raises_json_decode_error(self):
        """_json_payload with invalid fallback JSON must raise JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            _json_payload(None, "not-valid-json{")

