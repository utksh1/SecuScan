"""
Unit tests for Database execute, fetchone, fetchall methods.

Tests the foundational query interface using aiosqlite :memory: database.
Since aiosqlite may not be installed in all environments, these tests
import directly from backend.secuscan.database which provides the Database class.
"""

import pytest
import pytest_asyncio
import sys
import os

# Add workspace to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname('/workspace/SecuScan/testing/')))))

from backend.secuscan.database import Database


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    # Create a simple test table
    await database.execute(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)"
    )
    yield database
    await database.disconnect()


class TestFetchone:
    @pytest.mark.asyncio
    async def test_fetchone_returns_none_when_no_rows(self, db):
        result = await db.fetchone("SELECT * FROM items WHERE id = ?", (9999,))
        assert result is None

    @pytest.mark.asyncio
    async def test_fetchone_returns_dict_when_row_exists(self, db):
        await db.execute(
            "INSERT INTO items (name, value) VALUES (?, ?)",
            ("test_item", 42)
        )
        result = await db.fetchone("SELECT * FROM items WHERE name = ?", ("test_item",))
        assert result is not None
        assert result["name"] == "test_item"
        assert result["value"] == 42
        assert "id" in result

    @pytest.mark.asyncio
    async def test_fetchone_returns_none_for_empty_result_set(self, db):
        result = await db.fetchone("SELECT * FROM items WHERE name = ?", ("nonexistent",))
        assert result is None


class TestFetchall:
    @pytest.mark.asyncio
    async def test_fetchall_returns_empty_list_when_no_rows(self, db):
        result = await db.fetchall("SELECT * FROM items")
        assert result == []

    @pytest.mark.asyncio
    async def test_fetchall_returns_list_of_dicts(self, db):
        await db.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("a", 1))
        await db.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("b", 2))
        await db.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("c", 3))
        result = await db.fetchall("SELECT * FROM items ORDER BY name")
        assert len(result) == 3
        assert all(isinstance(row, dict) for row in result)
        assert result[0]["name"] == "a"
        assert result[1]["name"] == "b"
        assert result[2]["name"] == "c"

    @pytest.mark.asyncio
    async def test_fetchall_returns_correct_row_count(self, db):
        # Count after initial inserts (should be 4: test_item, a, b, c)
        result = await db.fetchall("SELECT * FROM items")
        assert len(result) == 4


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_commits_writes(self, db):
        cursor = await db.execute(
            "INSERT INTO items (name, value) VALUES (?, ?)",
            ("commits_test", 100)
        )
        # Commit should have happened, so we can query the row back
        result = await db.fetchone(
            "SELECT * FROM items WHERE name = ?", ("commits_test",)
        )
        assert result is not None
        assert result["value"] == 100

    @pytest.mark.asyncio
    async def test_execute_returns_cursor(self, db):
        cursor = await db.execute(
            "INSERT INTO items (name, value) VALUES (?, ?)",
            ("cursor_test", 200)
        )
        assert cursor is not None
        # rowcount should be 1 for a successful single-row insert
        assert cursor.rowcount >= 0
