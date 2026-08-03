from backend.secuscan.executor import _row_value


class FakeSqliteRow:
    """Duck-typed stand-in for sqlite3.Row: supports __getitem__ by key,
    but is not a dict, so it exercises the try/except branch of _row_value."""

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


def test_dict_with_existing_key_returns_value():
    assert _row_value({"status": "completed"}, "status", "unknown") == "completed"


def test_dict_with_missing_key_returns_default():
    assert _row_value({"status": "completed"}, "duration", 0) == 0


def test_none_row_returns_default():
    assert _row_value(None, "status", "unknown") == "unknown"


def test_sqlite_row_like_object_with_existing_key():
    row = FakeSqliteRow({"status": "completed", "duration": 42})
    assert _row_value(row, "status", "unknown") == "completed"
    assert _row_value(row, "duration", 0) == 42


def test_sqlite_row_like_object_with_missing_key_raises_keyerror_caught_returns_default():
    row = FakeSqliteRow({"status": "completed"})
    # Accessing a missing key raises KeyError internally (dict lookup),
    # which _row_value must catch and fall back to the default.
    assert _row_value(row, "nonexistent_field", "fallback") == "fallback"


def test_various_default_values_used_correctly():
    assert _row_value({}, "missing", None) is None
    assert _row_value({}, "missing", 0) == 0
    assert _row_value({}, "missing", "") == ""
    assert _row_value({}, "missing", []) == []
    assert _row_value({}, "missing", "{}") == "{}"

    row = FakeSqliteRow({})
    assert _row_value(row, "missing", None) is None
    assert _row_value(row, "missing", "{}") == "{}"