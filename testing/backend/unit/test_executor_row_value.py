"""
Unit tests for backend.secuscan.executor._row_value.

_row_value reads a dict/sqlite row key with a default for backward-compatible
mocks.  This is a pure helper that can be unit-tested without any external
dependencies.
executor.py re-exports it so existing call sites keep working unchanged.
"""

from backend.secuscan.executor import _row_value


class TestRowValue:
    def test_returns_value_when_key_exists_in_dict(self):
        row = {"tool_name": "nmap", "status": "completed"}
        assert _row_value(row, "tool_name") == "nmap"
        assert _row_value(row, "status") == "completed"

    def test_returns_default_when_key_is_absent(self):
        row = {"tool_name": "nmap"}
        assert _row_value(row, "status", default="unknown") == "unknown"
        assert _row_value(row, "missing_key") is None

    def test_returns_default_when_row_is_none(self):
        assert _row_value(None, "key") is None
        assert _row_value(None, "key", default="fallback") == "fallback"

    def test_returns_default_when_row_is_not_dict(self):
        assert _row_value("not a dict", "key") is None
        assert _row_value([], "key") is None
        assert _row_value(42, "key") is None

    def test_default_is_none_by_default(self):
        row = {"other_key": "value"}
        assert _row_value(row, "missing_key") is None

    def test_preserves_default_type(self):
        assert _row_value({}, "key", default=0) == 0
        assert _row_value({}, "key", default=False) is False
        assert _row_value({}, "key", default=[]) == []

    def test_nested_dict_value_access(self):
        row = {"meta": {"nested": "value"}}
        # row.get("meta") returns the nested dict
        assert _row_value(row, "meta") == {"nested": "value"}
