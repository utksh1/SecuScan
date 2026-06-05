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
from .risk_scoring import compute_risk_score, compute_risk_factors


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
        await self._run_migrations()

    async def disconnect(self):
        """Close the current database connection."""
        conn = self._connection
        if conn is not None:
            await conn.close()
            self._connection = None

    async def _create_schema(self):
        """Create the application schema using SQLite dialect and handle migrations."""
        await self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
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
                command_used TEXT,
                error_message TEXT,
                container_id TEXT,
                cpu_seconds REAL,
                memory_peak_mb REAL
            );

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

            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                plugin_id TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                target TEXT NOT NULL,
                description TEXT NOT NULL,
                remediation TEXT NOT NULL DEFAULT '',
                proof TEXT,
                cvss REAL,
                cve TEXT,
                discovered_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );


            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'technical',
                generated_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL DEFAULT 'ready',
                findings INTEGER NOT NULL DEFAULT 0,
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

            CREATE TABLE IF NOT EXISTS credential_vault (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                encrypted_value TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                schedule_seconds INTEGER,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                steps_json TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                last_run_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS notification_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                severity_threshold TEXT NOT NULL,
                channel_type TEXT NOT NULL,
                target_url_or_email TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS notification_history (
                id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL REFERENCES notification_rules(id) ON DELETE CASCADE,
                finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                error_message TEXT,
                sent_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            -- Tasks indexes (existing)
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_target ON tasks(target);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_plugin ON tasks(plugin_id);
            -- Composite index for dashboard running tasks query
            CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at DESC);

            -- Findings indexes (new)
            CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
            CREATE INDEX IF NOT EXISTS idx_findings_task_id ON findings(task_id);
            CREATE INDEX IF NOT EXISTS idx_findings_discovered_at ON findings(discovered_at DESC);
            CREATE INDEX IF NOT EXISTS idx_findings_plugin_id ON findings(plugin_id);
            CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target);
            -- Composite index for severity counting by task
            CREATE INDEX IF NOT EXISTS idx_findings_task_severity ON findings(task_id, severity);

            -- Reports indexes (new)
            CREATE INDEX IF NOT EXISTS idx_reports_task_id ON reports(task_id);
            CREATE INDEX IF NOT EXISTS idx_reports_generated_at ON reports(generated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

            -- Audit log indexes (new)
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
            CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_log(task_id);

            -- Workflows index (existing)
            CREATE INDEX IF NOT EXISTS idx_workflows_enabled ON workflows(enabled);
            CREATE INDEX IF NOT EXISTS idx_notification_rules_active ON notification_rules(is_active);
            CREATE INDEX IF NOT EXISTS idx_notification_rules_severity ON notification_rules(severity_threshold);
            CREATE INDEX IF NOT EXISTS idx_notification_history_rule_id ON notification_history(rule_id);
            CREATE INDEX IF NOT EXISTS idx_notification_history_finding_id ON notification_history(finding_id);
            CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at ON notification_history(sent_at DESC);
            """
        )

        # Migration logic: ensure latest columns exist in 'tasks' table
        tasks_columns = await self.fetchall("PRAGMA table_info(tasks)")
        existing_cols = {col["name"] for col in tasks_columns}
        
        needed_cols = {
            # Per-user ownership for BOLA prevention (issue #401). NOT NULL with a
            # constant default backfills every existing row to the shared default
            # owner, preserving single-user deployments' access to their history.
            "owner_id": "TEXT NOT NULL DEFAULT 'default'",
            "exit_code": "INTEGER",
            "scan_phase": "TEXT",
            "structured_json": "TEXT",
            "raw_output_path": "TEXT",
            "command_used": "TEXT",
            "error_message": "TEXT",
            "container_id": "TEXT",
            "cpu_seconds": "REAL",
            "memory_peak_mb": "REAL",
            "inputs_json": "TEXT NOT NULL DEFAULT '{}'",
            "preset": "TEXT",
            "safe_mode": "BOOLEAN NOT NULL DEFAULT 1"
        }

        for col_name, col_type in needed_cols.items():
            if col_name not in existing_cols:
                try:
                    await self.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
                    print(f"Added missing column {col_name} to tasks table.")
                except Exception as e:
                    print(f"Failed to add column {col_name}: {e}")

        # Findings table migration
        findings_columns = await self.fetchall("PRAGMA table_info(findings)")
        existing_finding_cols = {col["name"] for col in findings_columns}
        if "proof" not in existing_finding_cols:
            try:
                await self.execute("ALTER TABLE findings ADD COLUMN proof TEXT")
                print("Added missing column 'proof' to findings table.")
            except Exception as e:
                print(f"Failed to add 'proof' to findings: {e}")
        risk_cols = {
            "exploitability": "REAL",
            "confidence": "REAL",
            "asset_exposure": "TEXT",
            "risk_score": "REAL",
            "risk_factors_json": "TEXT NOT NULL DEFAULT '[]'",
            # Per-user ownership for BOLA prevention (issue #401).
            "owner_id": "TEXT NOT NULL DEFAULT 'default'",
        }
        for col_name, col_type in risk_cols.items():
            if col_name not in existing_finding_cols:
                try:
                    await self.execute(f"ALTER TABLE findings ADD COLUMN {col_name} {col_type}")
                    print(f"Added missing column {col_name} to findings table.")
                except Exception as e:
                    print(f"Failed to add column {col_name}: {e}")

        # Reports table migration: ensure owner_id exists (issue #401)
        reports_columns = await self.fetchall("PRAGMA table_info(reports)")
        existing_report_cols = {col["name"] for col in reports_columns}
        if "owner_id" not in existing_report_cols:
            try:
                await self.execute(
                    "ALTER TABLE reports ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default'"
                )
                print("Added missing column 'owner_id' to reports table.")
            except Exception as e:
                print(f"Failed to add 'owner_id' to reports: {e}")

        # Owner indexes must run after ALTER TABLE backfills owner_id on legacy DBs.
        await self.connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_id);
            CREATE INDEX IF NOT EXISTS idx_findings_owner ON findings(owner_id);
            CREATE INDEX IF NOT EXISTS idx_reports_owner ON reports(owner_id);
            """
        )

    async def _run_migrations(self):
        migrations_dir = Path(__file__).parent / "migrations"

        if not migrations_dir.exists():
            raise RuntimeError(
            f"Migrations directory not found at {migrations_dir} — "
            "ensure the backend package is installed correctly."
        )

        for migration_file in sorted(migrations_dir.glob("*.sql")):
            sql = migration_file.read_text(encoding="utf-8")
            try:
                await self.connection.executescript(sql)
            except Exception as exc:
                raise RuntimeError(
                    f"Migration {migration_file.name} failed — startup aborted: {exc}"
                ) from exc

        await self._backfill_risk_scores()

    async def _backfill_risk_scores(self):
        """Compute risk scores for existing findings that have none."""
        from datetime import datetime, timezone
        rows = await self.fetchall(
            "SELECT id, severity, exploitability, confidence, asset_exposure, discovered_at, risk_score FROM findings WHERE risk_score IS NULL"
        )
        if not rows:
            return
        for row in rows:
            discovered = None
            if row.get("discovered_at"):
                try:
                    discovered = datetime.fromisoformat(row["discovered_at"])
                except (ValueError, TypeError):
                    discovered = datetime.now(timezone.utc)
            score = compute_risk_score(
                severity=row["severity"],
                exploitability=row.get("exploitability"),
                asset_exposure=row.get("asset_exposure"),
                discovered_at=discovered,
                confidence=row.get("confidence"),
            )
            factors = compute_risk_factors(
                severity=row["severity"],
                exploitability=row.get("exploitability"),
                asset_exposure=row.get("asset_exposure"),
                discovered_at=discovered,
                confidence=row.get("confidence"),
                risk_score=score,
            )
            await self.execute(
                "UPDATE findings SET risk_score = ?, risk_factors_json = ? WHERE id = ?",
                (score, json.dumps(factors), row["id"]),
            )
        print(f"Backfilled risk scores for {len(rows)} existing finding(s).")

    async def execute(self, query: str, params: tuple = ()):
        """Execute a write query."""
        await self.connection.execute(query, params)
        await self.connection.commit()

    async def execute_no_commit(self, query: str, params: tuple = ()):
        """Execute a write query without committing (for use inside transactions)."""
        await self.connection.execute(query, params)

    async def begin(self):
        """Begin a transaction."""
        await self.connection.execute("BEGIN")

    async def commit(self):
        """Commit the current transaction."""
        await self.connection.commit()

    async def rollback(self):
        """Roll back the current transaction."""
        await self.connection.rollback()

    async def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one row."""
        async with await self.connection.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows."""
        async with await self.connection.execute(query, params) as cursor:
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
        request_id: Optional[str] = None,
    ):
        """Log an audit event."""

        from .request_context import get_request_id

        request_id = request_id or get_request_id()

        context = context or {}
        context["request_id"] = request_id

        await self.execute(
            """
            INSERT INTO audit_log (
                event_type,
                severity,
                message,
                context_json,
                task_id,
                plugin_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                severity,
                message,
                json.dumps(context),
                task_id,
                plugin_id,
            ),
        )


db: Optional[Database] = None


async def init_db(db_path: Optional[str] = None) -> Database:
    """Initialize the global database connection."""
    global db

    path = db_path or f"{settings.data_dir}/secuscan.db"

    db_instance = Database(path)
    await db_instance.connect()

    db = db_instance
    return db_instance


async def get_db() -> Database:
    """Get the global database instance."""
    if db is None:
        raise RuntimeError("Database not initialized")

    return db