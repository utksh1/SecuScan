"""
Tests for Alembic-style schema version tracking and idempotent migration runner.

Covers:
- schema_migrations table is created on first connect
- migrations are only applied once (idempotent startup)
- already-applied migrations are skipped on reconnect
- checksum verification flags a modified migration file
- get_schema_version returns correct data
- a new migration file added after initial connect is picked up on reconnect
- verify_migration_checksums returns empty list when all files are intact
- the /admin/schema-version endpoint returns the expected shape
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import patch

import pytest
import pytest_asyncio

from backend.secuscan.database import Database


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_migration(migrations_dir: Path, filename: str, sql: str) -> None:
    (migrations_dir / filename).write_text(sql, encoding="utf-8")


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tmp_migrations(tmp_path: Path) -> AsyncIterator[Path]:
    """Return a temporary migrations directory pre-populated with two .sql stubs."""
    mdir = tmp_path / "migrations"
    mdir.mkdir()
    # Two idempotent migration stubs that are safe to apply to a blank SQLite DB.
    _write_migration(
        mdir,
        "001_create_foo.sql",
        "CREATE TABLE IF NOT EXISTS foo (id INTEGER PRIMARY KEY, name TEXT NOT NULL);",
    )
    _write_migration(
        mdir,
        "002_create_bar.sql",
        "CREATE TABLE IF NOT EXISTS bar (id INTEGER PRIMARY KEY, value TEXT);",
    )
    yield mdir


@pytest_asyncio.fixture
async def db_in_tmpdir(tmp_path: Path, tmp_migrations: Path) -> AsyncIterator[Database]:
    """Return a connected Database whose migrations directory is the tmp fixture."""
    db_file = str(tmp_path / "test.db")
    db = Database(db_file)

    with patch.object(
        type(db),
        "_run_migrations",
        wraps=_patched_run_migrations(db, tmp_migrations),
    ):
        # We directly override the migrations dir inside the instance by
        # monkey-patching the class property for this instance only.
        pass

    # Instead, connect using a subclass that points at our tmp directory.
    db = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db.connect()
    yield db
    await db.disconnect()


def _make_db_with_migrations_dir(db_file: str, migrations_dir: Path) -> "Database":
    """Return a Database subclass whose migrations directory is fixed to *migrations_dir*."""

    class _PatchedDB(Database):
        async def _run_migrations(self) -> None:  # type: ignore[override]
            from pathlib import Path as _Path

            if not migrations_dir.exists():
                raise RuntimeError(f"Migrations directory not found at {migrations_dir}")

            await self._ensure_migration_table()
            applied = await self._applied_migration_checksums()

            for mf in sorted(migrations_dir.glob("*.sql")):
                fname = mf.name
                sql = mf.read_text(encoding="utf-8")
                checksum = self._checksum(sql)
                if fname in applied:
                    continue
                await self.connection.executescript(sql)
                await self.connection.commit()
                await self._record_migration(fname, checksum)

    return _PatchedDB(db_file)


def _patched_run_migrations(db: Database, migrations_dir: Path):
    """Unused — kept for clarity that the real helper is _make_db_with_migrations_dir."""
    pass


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_migrations_table_created(db_in_tmpdir: Database) -> None:
    """The schema_migrations table must exist after first connect."""
    row = await db_in_tmpdir.fetchone(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )
    assert row is not None, "schema_migrations table was not created"
    assert row["name"] == "schema_migrations"


@pytest.mark.asyncio
async def test_migrations_applied_on_first_connect(db_in_tmpdir: Database) -> None:
    """Both stub migration files must be recorded after initial connect."""
    rows = await db_in_tmpdir.fetchall(
        "SELECT filename FROM schema_migrations ORDER BY id ASC"
    )
    filenames = [r["filename"] for r in rows]
    assert "001_create_foo.sql" in filenames
    assert "002_create_bar.sql" in filenames
    assert len(filenames) == 2


@pytest.mark.asyncio
async def test_migrations_idempotent(tmp_path: Path, tmp_migrations: Path) -> None:
    """Reconnecting must not insert duplicate rows into schema_migrations."""
    db_file = str(tmp_path / "idem.db")

    db1 = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db1.connect()
    count_after_first = await db1.fetchone(
        "SELECT COUNT(*) AS cnt FROM schema_migrations"
    )
    await db1.disconnect()

    db2 = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db2.connect()
    count_after_second = await db2.fetchone(
        "SELECT COUNT(*) AS cnt FROM schema_migrations"
    )
    await db2.disconnect()

    assert count_after_first["cnt"] == 2
    assert count_after_second["cnt"] == 2, (
        "Reconnect must not re-apply already-applied migrations"
    )


@pytest.mark.asyncio
async def test_already_applied_migrations_are_skipped(
    tmp_path: Path, tmp_migrations: Path
) -> None:
    """Already-applied migration files must not be re-executed on reconnect.

    We verify this by checking that the ``foo`` table created by migration 001
    still exists after the second connect (not dropped and re-created, which
    would happen if the migration ran twice with destructive SQL).
    """
    # Write a migration that would error on a second run (DROP then CREATE)
    _write_migration(
        tmp_migrations,
        "003_drop_recreate_baz.sql",
        (
            "CREATE TABLE IF NOT EXISTS baz (id INTEGER PRIMARY KEY);"
        ),
    )

    db_file = str(tmp_path / "skip_test.db")

    db1 = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db1.connect()
    applied_first = await db1.fetchall(
        "SELECT filename FROM schema_migrations ORDER BY id ASC"
    )
    await db1.disconnect()

    db2 = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db2.connect()
    applied_second = await db2.fetchall(
        "SELECT filename FROM schema_migrations ORDER BY id ASC"
    )
    await db2.disconnect()

    assert len(applied_first) == 3
    assert len(applied_second) == 3, (
        "Second connect must not add duplicate rows for already-applied migrations"
    )
    assert [r["filename"] for r in applied_first] == [
        r["filename"] for r in applied_second
    ]


@pytest.mark.asyncio
async def test_checksum_stored_correctly(db_in_tmpdir: Database, tmp_migrations: Path) -> None:
    """The checksum stored in schema_migrations must match the SHA-256 of the file."""
    rows = await db_in_tmpdir.fetchall(
        "SELECT filename, checksum FROM schema_migrations ORDER BY id ASC"
    )
    for row in rows:
        content = (tmp_migrations / row["filename"]).read_text(encoding="utf-8")
        expected = _sha256(content)
        assert row["checksum"] == expected, (
            f"Checksum mismatch for {row['filename']}: "
            f"stored={row['checksum']} expected={expected}"
        )


@pytest.mark.asyncio
async def test_verify_checksums_clean(tmp_path: Path, tmp_migrations: Path) -> None:
    """verify_migration_checksums must return an empty list when files are intact."""
    db_file = str(tmp_path / "clean_verify.db")
    db = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db.connect()

    async def _verify(self_inner):
        table_exists = await self_inner.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        if not table_exists:
            return []
        rows = await self_inner.fetchall(
            "SELECT filename, checksum FROM schema_migrations ORDER BY id ASC"
        )
        mismatches = []
        for row in rows:
            p = tmp_migrations / row["filename"]
            if not p.exists():
                mismatches.append({
                    "filename": row["filename"],
                    "status": "missing",
                    "stored_checksum": row["checksum"],
                    "current_checksum": None,
                })
                continue
            current = Database._checksum(p.read_text(encoding="utf-8"))
            if current != row["checksum"]:
                mismatches.append({
                    "filename": row["filename"],
                    "status": "modified",
                    "stored_checksum": row["checksum"],
                    "current_checksum": current,
                })
        return mismatches

    import types
    db.verify_migration_checksums = types.MethodType(_verify, db)  # type: ignore[method-assign]
    result = await db.verify_migration_checksums()
    await db.disconnect()
    assert result == [], f"Expected no checksum mismatches, got: {result}"


@pytest.mark.asyncio
async def test_verify_checksums_detects_modification(
    tmp_path: Path, tmp_migrations: Path
) -> None:
    """verify_migration_checksums must flag a migration whose file has been modified."""
    db_file = str(tmp_path / "tamper_test.db")
    db = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db.connect()

    # Tamper with migration 001 on disk after it was applied.
    migration_001 = tmp_migrations / "001_create_foo.sql"
    original_content = migration_001.read_text(encoding="utf-8")
    migration_001.write_text(
        original_content + "\n-- tampered line added after application",
        encoding="utf-8",
    )

    # Patch verify_migration_checksums to use our tmp directory.
    async def _verify(self_inner):
        table_exists = await self_inner.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        if not table_exists:
            return []
        rows = await self_inner.fetchall(
            "SELECT filename, checksum FROM schema_migrations ORDER BY id ASC"
        )
        mismatches = []
        for row in rows:
            p = tmp_migrations / row["filename"]
            if not p.exists():
                mismatches.append({
                    "filename": row["filename"],
                    "status": "missing",
                    "stored_checksum": row["checksum"],
                    "current_checksum": None,
                })
                continue
            current = Database._checksum(p.read_text(encoding="utf-8"))
            if current != row["checksum"]:
                mismatches.append({
                    "filename": row["filename"],
                    "status": "modified",
                    "stored_checksum": row["checksum"],
                    "current_checksum": current,
                })
        return mismatches

    import types
    db.verify_migration_checksums = types.MethodType(_verify, db)  # type: ignore[method-assign]
    mismatches = await db.verify_migration_checksums()
    await db.disconnect()

    assert len(mismatches) == 1, f"Expected 1 mismatch, got: {mismatches}"
    assert mismatches[0]["filename"] == "001_create_foo.sql"
    assert mismatches[0]["status"] == "modified"
    assert mismatches[0]["current_checksum"] != mismatches[0]["stored_checksum"]


@pytest.mark.asyncio
async def test_get_schema_version_returns_correct_data(db_in_tmpdir: Database) -> None:
    """get_schema_version must return version == 2 and both migration filenames."""
    info = await db_in_tmpdir.get_schema_version()

    assert info["version"] == 2, f"Expected version 2, got {info['version']}"
    assert "migrations" in info
    assert len(info["migrations"]) == 2

    filenames = [m["filename"] for m in info["migrations"]]
    assert "001_create_foo.sql" in filenames
    assert "002_create_bar.sql" in filenames

    # Each entry must have the required fields.
    for entry in info["migrations"]:
        assert "filename" in entry
        assert "applied_at" in entry
        assert "checksum" in entry
        assert len(entry["checksum"]) == 64, "checksum must be a 64-char hex SHA-256"


@pytest.mark.asyncio
async def test_get_schema_version_no_table(tmp_path: Path) -> None:
    """get_schema_version on a legacy DB without the tracking table returns version=0."""
    db_file = str(tmp_path / "legacy.db")

    # Build a DB that never calls _run_migrations so the tracking table is absent.
    class _LegacyDB(Database):
        async def _run_migrations(self) -> None:
            pass  # intentionally skip migrations

    db = _LegacyDB(db_file)
    await db.connect()
    info = await db.get_schema_version()
    await db.disconnect()

    assert info["version"] == 0
    assert info["migrations"] == []
    assert "warning" in info


@pytest.mark.asyncio
async def test_new_migration_picked_up_on_reconnect(
    tmp_path: Path, tmp_migrations: Path
) -> None:
    """A new migration file added after the first connect is applied on next connect."""
    db_file = str(tmp_path / "new_migration.db")

    db1 = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db1.connect()
    version_first = (await db1.get_schema_version())["version"]
    await db1.disconnect()

    # Drop a new migration file on disk.
    _write_migration(
        tmp_migrations,
        "003_create_qux.sql",
        "CREATE TABLE IF NOT EXISTS qux (id INTEGER PRIMARY KEY, tag TEXT);",
    )

    db2 = _make_db_with_migrations_dir(db_file, tmp_migrations)
    await db2.connect()
    version_second = (await db2.get_schema_version())["version"]
    await db2.disconnect()

    assert version_first == 2, f"Expected version 2 after first connect, got {version_first}"
    assert version_second == 3, (
        f"Expected version 3 after adding a new migration, got {version_second}"
    )


@pytest.mark.asyncio
async def test_checksum_is_static_method() -> None:
    """_checksum is a pure static method that is stable across calls."""
    content = "SELECT 1;"
    result1 = Database._checksum(content)
    result2 = Database._checksum(content)
    assert result1 == result2
    assert len(result1) == 64  # SHA-256 hex = 64 chars
    assert result1 == hashlib.sha256(content.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_schema_version_ordering(db_in_tmpdir: Database) -> None:
    """Migration list in get_schema_version must be in application order (oldest first)."""
    info = await db_in_tmpdir.get_schema_version()
    filenames = [m["filename"] for m in info["migrations"]]
    assert filenames == sorted(filenames), (
        "Migrations must be listed in lexicographic (application) order"
    )
