"""
Unit tests for backend/secuscan/database.py Database helper methods.

Covers the basic data access methods not tested by existing test files:
  - Database.execute: run a write query and return cursor
  - Database.fetchone: fetch a single row as dict
  - Database.fetchall: fetch all rows as list of dicts
  - Database.executescript: run a schema/migration script

Tests use a real temporary SQLite database via aiosqlite.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

from backend.secuscan.database import Database


def _make_db(tmp_path):
    """Create and connect a Database backed by a temporary file. Returns (db, cleanup)."""
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    
    async def setup():
        await database.connect()
        return database
    
    return database, setup


class TestExecute:
    @pytest.mark.asyncio
    async def test_insert_returns_cursor_with_rowcount(self, tmp_path):
        """INSERT returns a cursor with rowcount = 1."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            cursor = await db.execute(
                "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                ("test_event", "info", "test message"),
            )
            assert cursor.rowcount == 1
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_update_returns_cursor_with_rowcount(self, tmp_path):
        """UPDATE returns a cursor with rowcount = number of affected rows."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.execute(
                "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                ("update_test", "info", "before"),
            )
            cursor = await db.execute(
                "UPDATE audit_log SET message = ? WHERE event_type = ?",
                ("after", "update_test"),
            )
            assert cursor.rowcount == 1
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_delete_returns_cursor_with_rowcount(self, tmp_path):
        """DELETE returns a cursor with rowcount = number of deleted rows."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.execute(
                "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                ("delete_test", "info", "to_delete"),
            )
            cursor = await db.execute(
                "DELETE FROM audit_log WHERE event_type = ?", ("delete_test",)
            )
            assert cursor.rowcount == 1
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_zero_rowcount(self, tmp_path):
        """UPDATE on non-matching rows returns rowcount = 0."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            cursor = await db.execute(
                "UPDATE audit_log SET message = ? WHERE event_type = ?",
                ("nomatch", "this_event_type_does_not_exist"),
            )
            assert cursor.rowcount == 0
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_zero_rowcount(self, tmp_path):
        """DELETE on non-matching rows returns rowcount = 0."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            cursor = await db.execute(
                "DELETE FROM audit_log WHERE event_type = ?",
                ("this_event_type_does_not_exist",),
            )
            assert cursor.rowcount == 0
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_execute_commits_transaction(self, tmp_path):
        """execute must auto-commit so subsequent reads see the change."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.execute(
                "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                ("commit_test", "warning", "visible?"),
            )
            row = await db.fetchone(
                "SELECT message FROM audit_log WHERE event_type = ?", ("commit_test",)
            )
            assert row is not None
            assert row["message"] == "visible?"
        finally:
            await db.disconnect()




class TestFetchone:
    @pytest.mark.asyncio
    async def test_returns_dict_for_existing_row(self, tmp_path):
        """fetchone returns a dict for a matching row."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.execute(
                "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                ("fetchone_test", "error", "found"),
            )
            row = await db.fetchone(
                "SELECT * FROM audit_log WHERE event_type = ?", ("fetchone_test",)
            )
            assert row is not None
            assert isinstance(row, dict)
            assert row["event_type"] == "fetchone_test"
            assert row["severity"] == "error"
            assert row["message"] == "found"
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_row(self, tmp_path):
        """fetchone returns None when no row matches."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            row = await db.fetchone(
                "SELECT * FROM audit_log WHERE event_type = ?",
                ("nonexistent_event_type_xyz",),
            )
            assert row is None
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_column_access_is_case_insensitive(self, tmp_path):
        """sqlite Row is case-insensitive when accessing columns.

        Note: dict(row) normalizes keys to lowercase, but the Row object
        itself is case-insensitive for column access.
        """
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.execute(
                "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                ("case_test", "info", "lower"),
            )
            # dict(row) normalizes keys to lowercase (sqlite canonical form)
            row = await db.fetchone(
                "SELECT EVENT_TYPE, Severity, MESSAGE FROM audit_log WHERE event_type = ?",
                ("case_test",),
            )
            assert row["event_type"] == "case_test"
            # dict() normalizes all keys to lowercase
            assert "EVENT_TYPE" not in row  # dict keys are lowercase
            assert "event_type" in row
        finally:
            await db.disconnect()


class TestFetchall:
    @pytest.mark.asyncio
    async def test_returns_empty_list_for_no_matches(self, tmp_path):
        """fetchall returns an empty list when no rows match."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            rows = await db.fetchall(
                "SELECT * FROM audit_log WHERE event_type = ?", ("nonexistent",)
            )
            assert isinstance(rows, list)
            assert len(rows) == 0
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_returns_all_matching_rows(self, tmp_path):
        """fetchall returns all matching rows as dicts."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            for i in range(3):
                await db.execute(
                    "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                    (f"fetchall_test_{i}", "info", f"row {i}"),
                )
            rows = await db.fetchall(
                "SELECT * FROM audit_log WHERE event_type LIKE ? ORDER BY event_type",
                ("fetchall_test_%",),
            )
            assert len(rows) == 3
            for row in rows:
                assert isinstance(row, dict)
                assert "fetchall_test" in row["event_type"]
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_aggregate_query_returns_single_row(self, tmp_path):
        """fetchall with COUNT(*) returns a single row."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            for i in range(2):
                await db.execute(
                    "INSERT INTO audit_log (event_type, severity, message) VALUES (?, ?, ?)",
                    (f"all_rows_test_{i}", "info", "all"),
                )
            rows = await db.fetchall(
                "SELECT COUNT(*) AS cnt FROM audit_log WHERE event_type LIKE 'all_rows_test_%'"
            )
            assert len(rows) == 1
            assert rows[0]["cnt"] == 2
        finally:
            await db.disconnect()


class TestExecutescript:
    @pytest.mark.asyncio
    async def test_creates_table_and_inserts_rows(self, tmp_path):
        """executescript runs a multi-statement SQL script."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.executescript(
                "CREATE TABLE test_script_table (id INTEGER PRIMARY KEY, name TEXT); "
                "INSERT INTO test_script_table (name) VALUES ('from_script');"
            )
            row = await db.fetchone(
                "SELECT name FROM test_script_table WHERE id = 1"
            )
            assert row["name"] == "from_script"
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_executescript_commits_changes(self, tmp_path):
        """executescript must auto-commit so changes are visible."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            await db.executescript(
                "CREATE TABLE test_script_commit (id INTEGER PRIMARY KEY, val TEXT);"
            )
            rows = await db.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_script_commit'"
            )
            assert len(rows) == 1
            assert rows[0]["name"] == "test_script_commit"
        finally:
            await db.disconnect()


class TestDatabaseErrorHandling:
    @pytest.mark.asyncio
    async def test_fetchone_with_syntax_error_raises(self, tmp_path):
        """SQL syntax errors propagate as exceptions."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            with pytest.raises(Exception):
                await db.fetchone("SELECT * FORM nonexistent_table")
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_execute_with_syntax_error_raises(self, tmp_path):
        """SQL syntax errors in execute propagate as exceptions."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            with pytest.raises(Exception):
                await db.execute("INSRT INTO audit_log (x) VALUES (1)")
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_fetchall_with_invalid_query_raises(self, tmp_path):
        """Invalid queries in fetchall propagate as exceptions."""
        db, setup = _make_db(tmp_path)
        await setup()
        try:
            with pytest.raises(Exception):
                await db.fetchall("SELEC * FORM audit_log")
        finally:
            await db.disconnect()



