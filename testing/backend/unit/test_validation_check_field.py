"""
Unit tests for _check_field helper in backend/secuscan/validation.py

Covers:
- String values: at max length (pass), exceeding max length (reject), under limit (pass)
- List values: at max array length (pass), exceeding max length (reject)
- List items: exceeding field length (reject), within limit (pass)
- Nested dicts: recursive validation
- Non-string/non-list types: pass-through
- Edge cases: empty string, empty list
- Error messages do not echo back field values
"""

from __future__ import annotations

import pytest

from backend.secuscan.validation import _check_field


# ---------------------------------------------------------------------------
# string value tests
# ---------------------------------------------------------------------------


class TestCheckFieldString:
    def test_string_at_max_length_passes(self):
        """A string at exactly the max allowed length (1000 chars) passes."""
        ok, code, msg = _check_field("field", "x" * 1000)
        assert ok is True
        assert code == 0
        assert msg == ""

    def test_string_exceeding_max_length_rejected(self):
        """A string exceeding the max allowed length is rejected with 400."""
        ok, code, msg = _check_field("field", "x" * 1001)
        assert ok is False
        assert code == 400
        assert "exceeds" in msg
        assert "1000" in msg

    def test_string_under_limit_passes(self):
        """A short string passes without error."""
        ok, code, msg = _check_field("field", "short value")
        assert ok is True
        assert code == 0
        assert msg == ""

    def test_empty_string_passes(self):
        """An empty string is within the max length and passes."""
        ok, code, msg = _check_field("field", "")
        assert ok is True
        assert code == 0

    def test_long_but_under_limit_passes(self):
        """A string close to but under the limit passes."""
        ok, code, msg = _check_field("field", "y" * 999)
        assert ok is True


# ---------------------------------------------------------------------------
# list value tests
# ---------------------------------------------------------------------------


class TestCheckFieldList:
    def test_list_at_max_array_length_passes(self):
        """A list at exactly the max array length (50 items) passes."""
        ok, code, msg = _check_field("field", ["x"] * 50)
        assert ok is True
        assert code == 0
        assert msg == ""

    def test_list_exceeding_max_array_length_rejected(self):
        """A list exceeding the max array length is rejected with 400."""
        ok, code, msg = _check_field("field", ["x"] * 51)
        assert ok is False
        assert code == 400
        assert "too many items" in msg
        assert "50" in msg

    def test_list_with_item_exceeding_max_field_length_rejected(self):
        """A list containing a string exceeding max field length is rejected."""
        ok, code, msg = _check_field("urls", ["x" * 1001])
        assert ok is False
        assert code == 400
        assert "index 0" in msg
        assert "1000" in msg

    def test_list_with_item_at_max_field_length_passes(self):
        """A list containing strings at exactly max length passes."""
        ok, code, msg = _check_field("urls", ["x" * 1000])
        assert ok is True

    def test_list_with_items_under_limit_passes(self):
        """A list with short items passes."""
        ok, code, msg = _check_field("urls", ["http://a.com", "https://b.com"])
        assert ok is True

    def test_empty_list_passes(self):
        """An empty list is within the max array length and passes."""
        ok, code, msg = _check_field("field", [])
        assert ok is True


# ---------------------------------------------------------------------------
# nested dict tests
# ---------------------------------------------------------------------------


class TestCheckFieldNestedDict:
    def test_nested_dict_short_values_pass(self):
        """Nested dict values within limits pass."""
        value = {"host": "example.com", "port": "443"}
        ok, code, msg = _check_field("config", value)
        assert ok is True
        assert code == 0

    def test_nested_dict_with_long_string_rejected(self):
        """Nested dict string values exceeding limit are rejected with dotted key."""
        value = {"host": "x" * 1001}
        ok, code, msg = _check_field("config", value)
        assert ok is False
        assert code == 400
        # The key in the error message should reference the nested key
        assert "config.host" in msg

    def test_nested_dict_with_long_list_rejected(self):
        """Nested dict with a list exceeding max length is rejected."""
        value = {"ips": ["1.1.1.1"] * 51}
        ok, code, msg = _check_field("config", value)
        assert ok is False
        assert code == 400
        assert "config.ips" in msg


# ---------------------------------------------------------------------------
# non-string/non-list types
# ---------------------------------------------------------------------------


class TestCheckFieldNonStringList:
    def test_int_value_passes(self):
        """Integer values pass through without validation."""
        ok, code, msg = _check_field("field", 42)
        assert ok is True
        assert code == 0

    def test_float_value_passes(self):
        """Float values pass through without validation."""
        ok, code, msg = _check_field("field", 3.14)
        assert ok is True

    def test_none_value_passes(self):
        """None values pass through without validation."""
        ok, code, msg = _check_field("field", None)
        assert ok is True

    def test_bool_value_passes(self):
        """Boolean values pass through without validation."""
        ok, code, msg = _check_field("field", True)
        assert ok is True
        ok, code, msg = _check_field("field", False)
        assert ok is True


# ---------------------------------------------------------------------------
# error message safety
# ---------------------------------------------------------------------------


class TestCheckFieldErrorMessageSafety:
    def test_error_message_does_not_echo_value(self):
        """The error message does not include the field value itself."""
        # Build a string that would exceed the limit
        long_value = "a" * 1001
        ok, code, msg = _check_field("api_key", long_value)
        assert ok is False
        assert code == 400
        # The message contains the field name but not the value
        assert "api_key" in msg
        # The message does NOT echo back the long_value
        assert "a" * 100 not in msg

    def test_error_message_for_list_item_does_not_echo_item(self):
        """The error message for a long list item does not echo the item."""
        long_item = "https://mysite.com/admin/" + ("x" * 985)
        ok, code, msg = _check_field("urls", [long_item])
        assert ok is False
        assert code == 400
        # The field name appears in quotes in the error message
        assert "'urls'" in msg
        assert "index 0" in msg
        assert "mysite.com" not in msg
