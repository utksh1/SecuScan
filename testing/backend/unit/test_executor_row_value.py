"""Unit tests for _row_value in backend/secuscan/executor.py."""

import pytest

from backend.secuscan.executor_helpers import _row_value


class RowLike:
    """Duck-typed sqlite.Row."""
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


class TestRowValue:
    def test_dict_existing_key(self):
        row = {"name": "test", "value": 42}
        assert _row_value(row, "name") == "test"
        assert _row_value(row, "value") == 42

    def test_dict_missing_key_returns_default(self):
        row = {"name": "test"}
        assert _row_value(row, "missing") is None
        assert _row_value(row, "missing", "fallback") == "fallback"
        assert _row_value(row, "missing", 0) == 0

    def test_none_row_returns_default(self):
        assert _row_value(None, "key") is None
        assert _row_value(None, "key", "default") == "default"

    def test_row_like_existing_key(self):
        row = RowLike({"name": "test", "count": 99})
        assert _row_value(row, "name") == "test"
        assert _row_value(row, "count") == 99

    def test_row_like_missing_key_returns_default(self):
        row = RowLike({"name": "test"})
        assert _row_value(row, "missing") is None
        assert _row_value(row, "missing", "fallback") == "fallback"

    def test_row_like_raises_keyerror_returns_default(self):
        """KeyError from row-like is caught and default is returned."""
        class BadRow:
            def __getitem__(self, key):
                raise KeyError(key)
        row = BadRow()
        assert _row_value(row, "any") is None
        assert _row_value(row, "any", "default") == "default"

    def test_default_explicit_none(self):
        row = {"key": None}
        assert _row_value(row, "key", "fallback") is None

    def test_default_with_various_types(self):
        row = {"a": 1, "b": "str", "c": []}
        assert _row_value(row, "a", 0) == 1
        assert _row_value(row, "b", "x") == "str"
        assert _row_value(row, "c", []) == []
        assert _row_value(row, "d", None) is None
