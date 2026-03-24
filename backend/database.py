"""
SQLite database access for SecuScan.
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional, List, Dict

import aiosqlite
from .config import settings


class Database:
    """SQLite database manager with an async-friendly interface."""

    db_path: str
    _connection: Optional[aiosqlite.Connection]

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the active database connection, raising an error if it's not connected."""
        if self._connection is None:
            raise RuntimeError("Database not connected. Did you forget to await connect()?")
        return self._connection

    async def connect(self):
        """Establish database connection and ensure schema exists."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = await aiosqlite.connect(self.db_path)
        self._connection = conn
        conn.row_factory = aiosqlite.Row
        await self._create_schema()

    async def disconnect(self):
        """Close the current database connection."""
        conn = self._connection
        if conn is not None:
            await conn.close()
            self._connection = None

    async def _create_schema(self):
        """Create the application schema using SQLite dialect."""
        await self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                plugin_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                target TEXT NOT NULL,
                inputs_json TEXT NOT NULL DEFAULT '{}',
                preset TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                consent_granted BOOLEAN NOT NULL DEFAULT 0,
                safe_mode BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                exit_code INTEGER,
                structured_json TEXT,
                raw_output_path TEXT,
                error_message TEXT,
                container_id TEXT,
                cpu_seconds REAL,
                memory_peak_mb REAL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_target ON tasks(target);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_plugin ON tasks(plugin_id);

            CREATE TABLE IF NOT EXISTS plugins (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                category TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                checksum TEXT,
                signature TEXT,
                installed_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                last_updated TIMESTAMP,
                last_used TIMESTAMP,
                binary_path TEXT,
                docker_image TEXT,
                python_packages_json TEXT
            );

            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                target TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL DEFAULT 'service',
                description TEXT NOT NULL DEFAULT '',
                risk_level TEXT NOT NULL DEFAULT 'low',
                status TEXT NOT NULL DEFAULT 'active',
                last_scanned TIMESTAMP,
                scan_count INTEGER NOT NULL DEFAULT 0,
                open_ports TEXT NOT NULL DEFAULT '[]',
                technologies TEXT NOT NULL DEFAULT '[]',
                services TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                plugin_id TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                target TEXT NOT NULL,
                description TEXT NOT NULL,
                remediation TEXT NOT NULL DEFAULT '',
                cvss REAL,
                cve TEXT,
                discovered_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS attack_surface_entries (
                id TEXT PRIMARY KEY,
                asset_id TEXT REFERENCES assets(id) ON DELETE SET NULL,
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                risk TEXT NOT NULL DEFAULT 'info',
                source TEXT NOT NULL DEFAULT '',
                last_seen TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'technical',
                generated_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL DEFAULT 'ready',
                findings INTEGER NOT NULL DEFAULT 0,
                assets INTEGER NOT NULL DEFAULT 0,
                pages INTEGER NOT NULL DEFAULT 0,
                file_path TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                message TEXT NOT NULL,
                context_json TEXT,
                task_id TEXT,
                plugin_id TEXT
            );

            CREATE TABLE IF NOT EXISTS presets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                plugin_id TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                last_used TIMESTAMP,
                use_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(plugin_id, name)
            );
            """
        )

    async def execute(self, query: str, params: tuple = ()):
        """Execute a write query."""
        await self.connection.execute(query, params)
        await self.connection.commit()

    async def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one row."""
        async with self.connection.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows."""
        async with self.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def executescript(self, script: str):
        """Execute a schema or migration script."""
        await self.connection.executescript(script)
        await self.connection.commit()

    async def log_audit(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        context: Optional[dict] = None,
        task_id: Optional[str] = None,
        plugin_id: Optional[str] = None,
    ):
        """Log an audit event."""
        await self.execute(
            """
            INSERT INTO audit_log (event_type, severity, message, context_json, task_id, plugin_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                severity,
                message,
                json.dumps(context) if context else None,
                task_id,
                plugin_id,
            ),
        )


db: Optional[Database] = None


async def init_db(db_path: Optional[str] = None) -> Database:
    """Initialize the global database connection."""
    global db
    # Fallback to config path if not provided
    path = db_path or settings.data_dir + "/secuscan.db"
    db_instance = Database(path)
    await db_instance.connect()
    db = db_instance
    return db_instance


async def get_db() -> Database:
    """Get the global database instance."""
    if db is None:
        raise RuntimeError("Database not initialized")
    return db
