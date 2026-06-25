"""
Unit tests for Database.__init__ and Database.connection property guard.

Imports the real Database class from backend.secuscan.database so a regression
in the connection guard is caught by these tests.
"""
from backend.secuscan.database import Database


def test_database_init_sets_path():
    """Database.__init__ stores the db_path."""
    db = Database("/path/to/test.db")
    assert db.db_path == "/path/to/test.db"


def test_database_init_sets_connection_to_none():
    """Database.__init__ initializes _connection to None."""
    db = Database("/path/to/test.db")
    assert db._connection is None


def test_connection_property_raises_when_not_connected():
    """Database.connection raises RuntimeError when _connection is None."""
    db = Database("/path/to/test.db")
    try:
        db.connection
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Did you forget to await connect" in str(exc)


def test_connection_property_returns_mock_connection():
    """Database.connection returns the underlying aiosqlite connection when set."""
    import aiosqlite
    db = Database("/path/to/test.db")
    mock_conn = aiosqlite.connect(":memory:")
    db._connection = mock_conn
    assert db.connection is mock_conn
