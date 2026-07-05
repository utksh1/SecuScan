"""
Unit tests for Database.execute, Database.execute_no_commit, Database.fetchone,
and Database.fetchall in backend.secuscan.database.

Uses an in-memory SQLite database to test SQL execution and result mapping
without needing the full application context.
"""

import pytest
import pytest_asyncio
from backend.secuscan.database import Database


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite database, connected and schema created."""
    db = Database(":memory:")
    await db.connect()
    await db.connection.executescript("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL,
            in_stock BOOLEAN NOT NULL DEFAULT 1
        );
    """)
    yield db
    await db.disconnect()


@pytest.mark.asyncio
class TestDatabaseExecute:
    async def test_insert_and_rowcount(self, db):
        cursor = await db.execute(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            ("Widget", 9.99),
        )
        assert cursor.rowcount == 1

    async def test_update_and_rowcount(self, db):
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Gadget", 19.99))
        cursor = await db.execute(
            "UPDATE products SET price = ? WHERE name = ?",
            (29.99, "Gadget"),
        )
        assert cursor.rowcount == 1

    async def test_delete_and_rowcount(self, db):
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Thing", 5.0))
        cursor = await db.execute("DELETE FROM products WHERE name = ?", ("Thing",))
        assert cursor.rowcount == 1

    async def test_delete_nonexistent_rowcount_is_zero(self, db):
        cursor = await db.execute("DELETE FROM products WHERE name = ?", ("DoesNotExist",))
        assert cursor.rowcount == 0


@pytest.mark.asyncio
class TestDatabaseExecuteNoCommit:
    async def test_execute_no_commit_rowcount_returned(self, db):
        """execute_no_commit returns the cursor so callers can inspect rowcount."""
        cursor = await db.execute_no_commit(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            ("NoCommit", 3.5),
        )
        assert cursor.rowcount == 1

    async def test_execute_no_commit_can_be_rolled_back(self, db):
        await db.execute_no_commit(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            ("RollbackMe", 2.0),
        )
        await db.rollback()
        result = await db.fetchone("SELECT * FROM products WHERE name = ?", ("RollbackMe",))
        assert result is None


@pytest.mark.asyncio
class TestDatabaseFetchone:
    async def test_returns_single_row(self, db):
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Alpha", 1.0))
        result = await db.fetchone("SELECT * FROM products WHERE name = ?", ("Alpha",))
        assert result is not None
        assert result["name"] == "Alpha"
        assert result["price"] == 1.0

    async def test_returns_none_for_no_match(self, db):
        result = await db.fetchone("SELECT * FROM products WHERE name = ?", ("NoMatch",))
        assert result is None

    async def test_boolean_column_coerced_from_int(self, db):
        await db.execute("INSERT INTO products (name, price, in_stock) VALUES (?, ?, ?)",
                         ("Beta", 2.0, 0))
        result = await db.fetchone("SELECT * FROM products WHERE name = ?", ("Beta",))
        assert result["in_stock"] == 0

    async def test_empty_table_returns_none(self, db):
        result = await db.fetchone("SELECT * FROM products LIMIT 1")
        assert result is None


@pytest.mark.asyncio
class TestDatabaseFetchall:
    async def test_returns_all_rows(self, db):
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("A", 1.0))
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("B", 2.0))
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("C", 3.0))
        results = await db.fetchall("SELECT * FROM products ORDER BY name")
        assert len(results) == 3
        assert results[0]["name"] == "A"
        assert results[1]["name"] == "B"
        assert results[2]["name"] == "C"

    async def test_returns_empty_list_for_no_match(self, db):
        results = await db.fetchall("SELECT * FROM products WHERE name = ?", ("NoMatch",))
        assert results == []

    async def test_empty_table_returns_empty_list(self, db):
        results = await db.fetchall("SELECT * FROM products")
        assert results == []

    async def test_parameter_binding_multiple_placeholders(self, db):
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("P1", 10.0))
        await db.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("P2", 20.0))
        results = await db.fetchall(
            "SELECT * FROM products WHERE price > ? ORDER BY price",
            (15.0,),
        )
        assert len(results) == 1
        assert results[0]["name"] == "P2"
