import sqlite3

import pytest

from backend.secuscan.database import Database


@pytest.mark.asyncio
async def test_legacy_workflows_table_migrates_to_owner_scoped_names(tmp_path):
    db_path = tmp_path / "legacy_workflows.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                schedule_seconds INTEGER,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                steps_json TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                last_run_at TIMESTAMP
            );
            INSERT INTO workflows (id, name, steps_json)
            VALUES ('wf-legacy', 'daily-scan', '[]');
            """
        )
        conn.commit()
    finally:
        conn.close()

    db = Database(str(db_path))
    await db.connect()
    try:
        await db.execute(
            """
            INSERT INTO workflows (id, name, owner_id, steps_json)
            VALUES (?, ?, ?, ?)
            """,
            ("wf-owner-a", "shared-name", "owner-a", "[]"),
        )
        await db.execute(
            """
            INSERT INTO workflows (id, name, owner_id, steps_json)
            VALUES (?, ?, ?, ?)
            """,
            ("wf-owner-b", "shared-name", "owner-b", "[]"),
        )

        rows = await db.fetchall(
            "SELECT id, owner_id FROM workflows WHERE name = ? ORDER BY owner_id",
            ("shared-name",),
        )
        assert rows == [
            {"id": "wf-owner-a", "owner_id": "owner-a"},
            {"id": "wf-owner-b", "owner_id": "owner-b"},
        ]
    finally:
        await db.disconnect()
