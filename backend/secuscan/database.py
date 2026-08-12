import asyncio
import contextlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional, List, Dict, AsyncIterator

import aiosqlite
from .config import settings
from .risk_scoring import compute_risk_score, compute_risk_factors


class Database:
    db_path: str
    _connection: Optional[aiosqlite.Connection]

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None
        self._in_transaction: bool = False

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError(
                "Database not connected. Did you forget to await connect()?"
            )
        return self._connection

    async def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = await aiosqlite.connect(self.db_path)
        self._connection = conn
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await self._create_schema()
        await self._ensure_schema_migrations_table()
        await self._validate_schema_version()
        await self._run_migrations()

    async def disconnect(self):
        conn = self._connection
        if conn is not None:
            await conn.close()
            self._connection = None

    async def _create_schema(self):
        await self.connection.executescript(
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
            "execution_context_json": "TEXT NOT NULL DEFAULT '{}'",
            "preset": "TEXT",
            "safe_mode": "BOOLEAN NOT NULL DEFAULT 1",
            "phase_timestamps_json": "TEXT NOT NULL DEFAULT '{}'"
        }

        for col_name, col_type in needed_cols.items():
            if col_name not in existing_cols:
                try:
                    await self.execute(
                        f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"
                    )
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
            "validated": "BOOLEAN NOT NULL DEFAULT 0",
            "validation_method": "TEXT",
            "confidence_reason": "TEXT",
            "finding_kind": "TEXT NOT NULL DEFAULT 'observation'",
            "finding_group_id": "TEXT",
            "asset_id": "TEXT",
            "first_seen_at": "TIMESTAMP",
            "last_seen_at": "TIMESTAMP",
            "occurrence_count": "INTEGER NOT NULL DEFAULT 1",
            "corroborating_sources_json": "TEXT NOT NULL DEFAULT '[]'",
            "evidence_count": "INTEGER NOT NULL DEFAULT 0",
            "analyst_status": "TEXT NOT NULL DEFAULT 'new'",
            "retest_status": "TEXT NOT NULL DEFAULT 'not_requested'",
            "evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "asset_refs_json": "TEXT NOT NULL DEFAULT '[]'",
            "service_fingerprint": "TEXT",
            "cpe": "TEXT",
            "references_json": "TEXT NOT NULL DEFAULT '[]'",
            "asset_exposure": "TEXT",
            "risk_score": "REAL",
            "risk_factors_json": "TEXT NOT NULL DEFAULT '[]'",
            # Per-user ownership for BOLA prevention (issue #401).
            "owner_id": "TEXT NOT NULL DEFAULT 'default'",
        }
        for col_name, col_type in risk_cols.items():
            if col_name not in existing_finding_cols:
                try:
                    await self.execute(
                        f"ALTER TABLE findings ADD COLUMN {col_name} {col_type}"
                    )
                    print(f"Added missing column {col_name} to findings table.")
                except Exception as e:
                    print(f"Failed to add column {col_name}: {e}")

        asset_service_columns = await self.fetchall("PRAGMA table_info(asset_services)")
        existing_asset_service_cols = {col["name"] for col in asset_service_columns}
        asset_service_needed = {
            "asset_id": "TEXT",
            "ip": "TEXT",
            "title": "TEXT",
            "banner": "TEXT",
            "cert_subject": "TEXT",
            "cert_san_json": "TEXT NOT NULL DEFAULT '[]'",
            "cert_expiry": "TEXT",
            "service_fingerprint": "TEXT",
        }
        for col_name, col_type in asset_service_needed.items():
            if col_name not in existing_asset_service_cols:
                try:
                    await self.execute(
                        f"ALTER TABLE asset_services ADD COLUMN {col_name} {col_type}"
                    )
                    print(f"Added missing column {col_name} to asset_services table.")
                except Exception as e:
                    print(f"Failed to add column {col_name} to asset_services: {e}")

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

        # Vault table migration: ensure owner_id exists
        vault_columns = await self.fetchall(
            "PRAGMA table_info(credential_vault)"
            )
        existing_vault_cols = {col["name"] for col in vault_columns}
        vault_schema = await self.fetchone(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='credential_vault'"
            )

        if "owner_id" not in existing_vault_cols:
            try:
                await self.execute(
                    "ALTER TABLE credential_vault "
                    "ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default'"
                    )
                print("Added missing column 'owner_id' to credential_vault table.")
            except Exception as e:
                print(f"Failed to add 'owner_id' to credential_vault: {e}")

        if vault_schema:
            ddl = vault_schema["sql"]
            has_composite = "UNIQUE(owner_id, name)" in ddl
            if not has_composite:
                await self.connection.executescript(
                    """CREATE TABLE credential_vault_new (
                await self.connection.commit()

        # Workflows table migration: ensure owner_id and composite unique exist
        workflows_columns = await self.fetchall("PRAGMA table_info(workflows)")
        existing_wf_cols = {col["name"] for col in workflows_columns}
        if "owner_id" not in existing_wf_cols:
            try:
                await self.execute(
                    "ALTER TABLE workflows ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default'"
                )
                existing_wf_cols.add("owner_id")
                print("Added missing column 'owner_id' to workflows table.")
            except Exception as e:
                print(f"Failed to add 'owner_id' to workflows: {e}")

        # which blocks same-named workflows across owners.  SQLite cannot
        wf_schema = await self.fetchone(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='workflows'"
        )
        if wf_schema and "owner_id" in existing_wf_cols:
            ddl = wf_schema["sql"]
            # Check for the old inline UNIQUE constraint on name
            has_old_unique = "name TEXT NOT NULL UNIQUE" in ddl
            has_composite = "UNIQUE(owner_id, name)" in ddl
            if has_old_unique or not has_composite:
                old_fk = await self.fetchone("PRAGMA foreign_keys")
                if old_fk:
                    await self.execute("PRAGMA foreign_keys = OFF")
                try:
                    await self.connection.executescript("""
                    await self.connection.commit()
                    print(
                        "Replaced workflows UNIQUE(name) constraint with UNIQUE(owner_id, name)."
                    )
                finally:
                    if old_fk:
                        await self.execute("PRAGMA foreign_keys = ON")

        # Workflows table migration: ensure schedule_timezone exists
        if "schedule_timezone" not in existing_wf_cols:
            try:
                await self.execute(
                    "ALTER TABLE workflows ADD COLUMN schedule_timezone TEXT"
                )
                print("Added missing column 'schedule_timezone' to workflows table.")
            except Exception as e:
                print(f"Failed to add 'schedule_timezone' to workflows: {e}")

        # Notification rules table migration: ensure owner_id exists
        notif_columns = await self.fetchall("PRAGMA table_info(notification_rules)")
        existing_notif_cols = {col["name"] for col in notif_columns}
        if "owner_id" not in existing_notif_cols:
            try:
                await self.execute(
                    "ALTER TABLE notification_rules ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default'"
                )
                print("Added missing column 'owner_id' to notification_rules table.")
            except Exception as e:
                print(f"Failed to add 'owner_id' to notification_rules: {e}")

        # Notification history table migration: ensure owner_id exists (BOLA fix, issue #1483)
        notif_hist_columns = await self.fetchall("PRAGMA table_info(notification_history)")
        existing_notif_hist_cols = {col["name"] for col in notif_hist_columns}
        if "owner_id" not in existing_notif_hist_cols:
            try:
                await self.execute(
                    "ALTER TABLE notification_history ADD COLUMN owner_id TEXT"
                )
                # Backfill owner_id from notification_rules for existing rows
                await self.execute(
                    "UPDATE notification_history SET owner_id = ("
                    "SELECT nr.owner_id FROM notification_rules nr "
                    "WHERE nr.id = notification_history.rule_id"
                    ") WHERE owner_id IS NULL"
                )
                print("Added missing column 'owner_id' to notification_history table.")
            except Exception as e:
                print(f"Failed to add 'owner_id' to notification_history: {e}")

        # Owner indexes must run after ALTER TABLE backfills owner_id on legacy DBs.
        await self.connection.executescript(
            )


    async def _ensure_schema_migrations_table(self):
        await self.connection.execute(
        )
        await self.connection.commit()

    async def _applied_migrations(self) -> set[str]:
        rows = await self.fetchall(
            "SELECT version FROM schema_migrations"
        )
        return {row["version"] for row in rows}

    async def _validate_schema_version(self):
        applied = await self._applied_migrations()

        available = {
            migration.name
            for migration in (Path(__file__).parent / "migrations").glob("*.sql")
        }

        unknown = applied - available

        if unknown:
            raise RuntimeError(
                "Database schema is newer than this application. "
                f"Unknown migration(s): {', '.join(sorted(unknown))}"
            )

    async def _record_migration(self, version: str):
        await self.execute(
            (version,),
        )


    async def _run_migrations(self):
        migrations_dir = Path(__file__).parent / "migrations"

        if not migrations_dir.exists():
            raise RuntimeError(
                f"Migrations directory not found at {migrations_dir} — "
                "ensure the backend package is installed correctly."
            )

        applied = await self._applied_migrations()

        for migration_file in sorted(migrations_dir.glob("*.sql")):
            migration_name = migration_file.name

            if migration_name in applied:
                continue

            sql = migration_file.read_text(encoding="utf-8")

            try:
                await self.connection.executescript(sql)
                await self._record_migration(migration_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Migration {migration_name} failed — startup aborted: {exc}"
                ) from exc

        await self._backfill_risk_scores()

    async def _backfill_risk_scores(self):
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

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator["Database"]:
        if self._in_transaction:
            yield self
        else:
            await self.begin()
            try:
                yield self
                await self.commit()
            except Exception:
                await self.rollback()
                raise

    async def execute(self, query: str, params: tuple = ()):
        cursor = await self.connection.execute(query, params)
        if not self._in_transaction:
            await self.connection.commit()
        return cursor

    async def execute_no_commit(self, query: str, params: tuple = ()):
        cursor = await self.connection.execute(query, params)
        return cursor

    async def begin(self):
        if self._in_transaction:
            return
        await self.connection.execute("BEGIN")
        self._in_transaction = True

    async def commit(self):
        if not self._in_transaction:
            return
        await self.connection.commit()
        self._in_transaction = False

    async def rollback(self):
        if not self._in_transaction:
            return
        await self.connection.rollback()
        self._in_transaction = False

    async def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        async with await self.connection.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        async with await self.connection.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def executescript(self, script: str):
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
        from .request_context import get_request_id

        request_id = request_id or get_request_id()

        context = context or {}
        context["request_id"] = request_id

        await self.execute(
            (
                event_type,
                severity,
                message,
                json.dumps(context),
                task_id,
                plugin_id,
            ),
        )

    async def snapshot_workflow_version(
        self,
        workflow_id: str,
        name: str,
        schedule_seconds: Optional[int],
        enabled: bool,
        steps: List[Dict],
        created_by: str = "system",
        schedule_timezone: Optional[str] = None,
    ) -> Dict:
        version_id = json.dumps(None)
        row = await self.fetchone(
            "SELECT MAX(version_number) AS max_v FROM workflow_versions WHERE workflow_id = ?",
            (workflow_id,),
        )
        next_version = (row["max_v"] or 0) + 1 if row else 1
        version_id = __import__("uuid").uuid4().hex
        definition = {
            "name": name,
            "schedule_seconds": schedule_seconds,
            "schedule_timezone": schedule_timezone,
            "enabled": enabled,
            "steps": steps,
        }
        await self.execute(
            "INSERT INTO workflow_versions (id, workflow_id, version_number, definition_json, created_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (version_id, workflow_id, next_version, json.dumps(definition), created_by),
        )
        return {
            "id": version_id,
            "workflow_id": workflow_id,
            "version_number": next_version,
            "definition": definition,
            "created_by": created_by,
        }

    async def get_workflow_versions(self, workflow_id: str) -> List[Dict]:
        rows = await self.fetchall(
            "SELECT id, workflow_id, version_number, definition_json, created_at, created_by "
            "FROM workflow_versions WHERE workflow_id = ? ORDER BY version_number DESC",
            (workflow_id,),
        )
        result = []
        for row in rows:
            try:
                defn = json.loads(row["definition_json"])
            except (json.JSONDecodeError, TypeError):
                defn = {}
            result.append(
                {
                    "id": row["id"],
                    "workflow_id": row["workflow_id"],
                    "version_number": row["version_number"],
                    "definition": defn,
                    "created_at": row["created_at"],
                    "created_by": row["created_by"],
                }
            )
        return result

    async def get_workflow_version(
        self, workflow_id: str, version_number: int
    ) -> Optional[Dict]:
        row = await self.fetchone(
            "SELECT id, workflow_id, version_number, definition_json, created_at, created_by "
            "FROM workflow_versions WHERE workflow_id = ? AND version_number = ?",
            (workflow_id, version_number),
        )
        if row is None:
            return None
        try:
            defn = json.loads(row["definition_json"])
        except (json.JSONDecodeError, TypeError):
            defn = {}
        return {
            "id": row["id"],
            "workflow_id": row["workflow_id"],
            "version_number": row["version_number"],
            "definition": defn,
            "created_at": row["created_at"],
            "created_by": row["created_by"],
        }

    async def record_workflow_run(
        self,
        workflow_id: str,
        version_id: Optional[str],
        version_number: Optional[int],
        task_ids: List[str],
        triggered_by: str = "manual",
    ) -> str:
        run_id = __import__("uuid").uuid4().hex
        await self.execute(
            "INSERT INTO workflow_runs "
            "(id, workflow_id, version_id, version_number, triggered_by, status, task_ids_json) "
            "VALUES (?, ?, ?, ?, ?, 'queued', ?)",
            (
                run_id,
                workflow_id,
                version_id,
                version_number,
                triggered_by,
                json.dumps(task_ids),
            ),
        )
        return run_id

    async def finalize_workflow_run(
        self, run_id: str, status: str, error_message: Optional[str] = None
    ) -> None:
        await self.execute(
            "UPDATE workflow_runs SET status = ?, completed_at = datetime('now'), error_message = ? "
            "WHERE id = ?",
            (status, error_message, run_id),
        )

    async def check_workflow_run_tasks(self, run_id: str) -> Optional[str]:
        run_row = await self.fetchone(
            "SELECT task_ids_json FROM workflow_runs WHERE id = ?", (run_id,)
        )
        if run_row is None:
            return None
        try:
            task_ids = json.loads(run_row["task_ids_json"] or "[]")
        except (json.JSONDecodeError, TypeError):
            task_ids = []
        if not task_ids:
            return "completed"
        statuses = []
        for tid in task_ids:
            row = await self.fetchone("SELECT status FROM tasks WHERE id = ?", (tid,))
            if row:
                statuses.append(row["status"])
        if not statuses:
            return None
        in_progress = {"queued", "running"}
        if any(s in in_progress for s in statuses):
            return None
        if all(s == "completed" for s in statuses):
            return "completed"
        if any(s == "cancelled" for s in statuses):
            return "cancelled"
        return "failed"

    async def get_workflow_runs(
        self, workflow_id: str, limit: int = 50, offset: int = 0
    ) -> Dict:
        count_row = await self.fetchone(
            "SELECT COUNT(*) AS total FROM workflow_runs WHERE workflow_id = ?",
            (workflow_id,),
        )
        total = count_row["total"] if count_row else 0
        rows = await self.fetchall(
            "SELECT * FROM workflow_runs WHERE workflow_id = ? "
            "ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (workflow_id, limit, offset),
        )
        entries = []
        for row in rows:
            try:
                task_ids = json.loads(row["task_ids_json"] or "[]")
            except (json.JSONDecodeError, TypeError):
                task_ids = []
            entries.append(
                {
                    "id": row["id"],
                    "workflow_id": row["workflow_id"],
                    "version_id": row["version_id"],
                    "version_number": row["version_number"],
                    "triggered_by": row["triggered_by"],
                    "status": row["status"],
                    "task_ids": task_ids,
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "error_message": row["error_message"],
                }
            )
        return {"total": total, "runs": entries}


db: Optional[Database] = None


async def init_db(db_path: Optional[str] = None) -> Database:
    global db

    path = db_path or f"{settings.data_dir}/secuscan.db"

    db_instance = Database(path)
    await db_instance.connect()

    db = db_instance
    return db_instance


async def get_db() -> Database:
    if db is None:
        raise RuntimeError("Database not initialized")

    return db
