"""
Integration tests: audit_log table schema migration and append-only behavior.
"""

import json
import aiosqlite
import pytest
import pytest_asyncio

from backend.secuscan.database import Database


# ---------------------------------------------------------------------------
# Migration: old -> new schema
# ---------------------------------------------------------------------------

# The full schema's CREATE INDEX statements reference columns like task_id,
# scan_id, etc. The legacy table below includes all columns EXCEPT the ones
# the ALTER TABLE migration is responsible for adding (scan_id, target, actor, metadata).

_LEGACY_AUDIT_LOG_TABLE = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        plugin_id TEXT,
        timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now')),
        severity TEXT NOT NULL DEFAULT 'info',
        user_id TEXT,
        ip_address TEXT,
        message TEXT NOT NULL DEFAULT '',
        context_json TEXT,
        task_id TEXT,
        scan_id TEXT
    );
"""


@pytest.mark.asyncio
async def test_audit_log_migration_adds_missing_columns(tmp_path):
    """An existing audit_log table with an old schema gets new columns added."""
    db_path = str(tmp_path / "legacy.db")

    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(_LEGACY_AUDIT_LOG_TABLE)
        await conn.commit()

    db = Database(db_path)
    await db.connect()

    columns = await db.fetchall("PRAGMA table_info(audit_log)")
    col_names = {c["name"] for c in columns}

    for expected in ("scan_id", "target", "actor", "metadata"):
        assert expected in col_names, f"Column '{expected}' should have been added by migration"

    await db.disconnect()


@pytest.mark.asyncio
async def test_existing_data_preserved_after_migration(tmp_path):
    """Data in existing audit_log rows survives schema migration."""
    db_path = str(tmp_path / "legacy2.db")

    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(f"""
            {_LEGACY_AUDIT_LOG_TABLE}
            INSERT INTO audit_log (event_type, severity, message)
            VALUES ('scan_created', 'info', 'legacy entry');
        """)
        await conn.commit()

    db = Database(db_path)
    await db.connect()

    rows = await db.fetchall("SELECT event_type, message FROM audit_log ORDER BY id")
    assert len(rows) == 1
    assert rows[0]["event_type"] == "scan_created"
    assert rows[0]["message"] == "legacy entry"

    await db.disconnect()


# ---------------------------------------------------------------------------
# Append-only: verify rows survive task deletion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_is_append_only_via_api(tmp_path):
    """Audit log rows survive task deletion via the API (append-only contract)."""
    from backend.secuscan.database import init_db, get_db
    from backend.secuscan import database as db_module

    db_path = str(tmp_path / "append_only.db")
    await init_db(db_path)
    db = await get_db()

    await db.execute(
        "INSERT INTO audit_log (event_type, severity, message, task_id) "
        "VALUES ('test_event', 'info', 'test entry', 'task-1')",
    )

    rows = await db.fetchall("SELECT id, event_type FROM audit_log WHERE task_id = ?", ("task-1",))
    assert len(rows) == 1, "Audit entry should have been inserted"
    assert rows[0]["event_type"] == "test_event"

    await db.disconnect()
    db_module.db = None


# ---------------------------------------------------------------------------
# log_event writes correct shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_event_writes_all_columns(tmp_path):
    """Verify log_event (from audit.py) inserts into all expected columns."""
    from backend.secuscan.database import init_db, get_db
    from backend.secuscan import database as db_module
    from backend.secuscan.audit import AuditEventType, log_event
    from backend.secuscan.request_context import set_request_id

    await init_db(str(tmp_path / "log_event.db"))
    db = await get_db()

    set_request_id("req-migration-test")
    await log_event(
        AuditEventType.SCAN_CREATED,
        scan_id="migration-scan",
        plugin_id="test_plugin",
        target="127.0.0.1",
        actor="tester",
        metadata={"extra": "data"},
    )

    rows = await db.fetchall(
        "SELECT event_type, scan_id, plugin_id, target, actor, metadata, "
        "severity, message, context_json, task_id "
        "FROM audit_log"
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["event_type"] == "scan_created"
    assert row["scan_id"] == "migration-scan"
    assert row["plugin_id"] == "test_plugin"
    assert row["target"] == "127.0.0.1"
    assert row["actor"] == "tester"

    meta = json.loads(row["metadata"])
    assert meta["extra"] == "data"
    assert meta["request_id"] == "req-migration-test"

    await db.disconnect()
    db_module.db = None
