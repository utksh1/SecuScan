from __future__ import annotations
import os
import aiosqlite


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    plugin_id TEXT NOT NULL,
    parameters TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    duration_seconds REAL,
    summary TEXT,
    structured_json TEXT,
    consent_acknowledged INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    task_id TEXT,
    plugin_id TEXT,
    details TEXT
);
"""


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()

    async def insert_task(self, task_row: dict) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO tasks (id, plugin_id, parameters, status, created_at, consent_acknowledged) VALUES (?,?,?,?,?,?)",
                (
                    task_row["id"],
                    task_row["plugin_id"],
                    task_row["parameters"],
                    task_row["status"],
                    task_row["created_at"],
                    1 if task_row.get("consent_acknowledged") else 0,
                ),
            )
            await conn.commit()

    async def mark_started(self, task_id: str, started_at: str) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET started_at=?, status=? WHERE id=?",
                (started_at, "running", task_id),
            )
            await conn.commit()

    async def mark_completed(self, task_id: str, completed_at: str, duration_seconds: float, summary: str, structured_json: str) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET completed_at=?, duration_seconds=?, status=?, summary=?, structured_json=? WHERE id=?",
                (completed_at, duration_seconds, "completed", summary, structured_json, task_id),
            )
            await conn.commit()

    async def mark_failed(self, task_id: str, completed_at: str, summary: str) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE tasks SET completed_at=?, status=?, summary=? WHERE id=?",
                (completed_at, "failed", summary, task_id),
            )
            await conn.commit()

    async def get_task(self, task_id: str):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def list_tasks(self):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT id, plugin_id, status, created_at, completed_at, summary FROM tasks ORDER BY created_at DESC") as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]


