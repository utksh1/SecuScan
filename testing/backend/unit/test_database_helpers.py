"""Tests for database.py Database class initialization and error paths."""

import pytest

from backend.secuscan.database import Database


class TestDatabaseInitialization:
    """Database must be correctly initialized with the given db_path."""

    def test_database_accepts_memory_path(self):
        db = Database(":memory:")
        assert db.db_path == ":memory:"

    def test_database_accepts_file_path(self):
        db = Database("/tmp/test_secuscan.db")
        assert db.db_path == "/tmp/test_secuscan.db"

    def test_connection_is_none_before_connect(self):
        db = Database(":memory:")
        assert db._connection is None

    def test_in_transaction_is_false_initially(self):
        db = Database(":memory:")
        assert db._in_transaction is False


class TestDatabaseConnectionProperty:
    """Database.connection must raise RuntimeError when not connected."""

    def test_connection_raises_runtime_error_when_not_connected(self):
        db = Database(":memory:")
        with pytest.raises(RuntimeError) as exc_info:
            _ = db.connection
        assert "not connected" in str(exc_info.value).lower()

    def test_connection_error_message_is_actionable(self):
        db = Database(":memory:")
        with pytest.raises(RuntimeError) as exc_info:
            _ = db.connection
        msg = str(exc_info.value)
        # Should mention that connect() needs to be called
        assert len(msg) > 10


class TestDatabaseState:
    """Database internal state management."""

    def test_multiple_instances_are_independent(self):
        db1 = Database(":memory:")
        db2 = Database("/tmp/other.db")
        assert db1.db_path == ":memory:"
        assert db2.db_path == "/tmp/other.db"
        assert db1._connection is None
        assert db2._connection is None
        assert db1._in_transaction is False
        assert db2._in_transaction is False
