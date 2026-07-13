"""
SQLite database access for SecuScan.
"""

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
    """SQLite database manager with an async-friendly interface."""

    db_path: str
    _connection: Optional[aiosqlite.Connection]

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None
        self._in_transaction: bool = False

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the active database connection, raising an error if it's not connected."""
        if self._connection is None:
            raise RuntimeError(
                "Database not connected. Did you forget to await connect()?"
            )
        return self._connection

    async def connect(self):
        """Establish database connection and ensure schema exists."""
        # Ensure data directory exists
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
                execution_context_json TEXT NOT NULL DEFAULT '{}',
                preset TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                scan_phase TEXT,
                phase_timestamps_json TEXT NOT NULL DEFAULT '{}',
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
                exploitability REAL,
                confidence REAL,
                validated BOOLEAN NOT NULL DEFAULT 0,
                validation_method TEXT,
                confidence_reason TEXT,
                finding_kind TEXT NOT NULL DEFAULT 'observation',
                finding_group_id TEXT,
                asset_id TEXT,
                first_seen_at TIMESTAMP,
                last_seen_at TIMESTAMP,
                occurrence_count INTEGER NOT NULL DEFAULT 1,
                corroborating_sources_json TEXT NOT NULL DEFAULT '[]',
                evidence_count INTEGER NOT NULL DEFAULT 0,
                analyst_status TEXT NOT NULL DEFAULT 'new',
                retest_status TEXT NOT NULL DEFAULT 'not_requested',
                evidence_json TEXT NOT NULL DEFAULT '[]',
                asset_refs_json TEXT NOT NULL DEFAULT '[]',
                service_fingerprint TEXT,
                cpe TEXT,
                references_json TEXT NOT NULL DEFAULT '[]',
                asset_exposure TEXT,
                risk_score REAL,
                risk_factors_json TEXT NOT NULL DEFAULT '[]',
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

            CREATE TABLE IF NOT EXISTS target_policies (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                description TEXT,
                allow_public_targets BOOLEAN NOT NULL DEFAULT 0,
                allow_exploit_validation BOOLEAN NOT NULL DEFAULT 0,
                allow_authenticated_scan BOOLEAN NOT NULL DEFAULT 0,
                default_validation_mode TEXT NOT NULL DEFAULT 'proof',
                allowed_targets_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS credential_profiles (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                username_secret_name TEXT,
                password_secret_name TEXT,
                extra_headers_json TEXT NOT NULL DEFAULT '{}',
                login_recipe_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS session_profiles (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                cookie_secret_name TEXT,
                extra_headers_json TEXT NOT NULL DEFAULT '{}',
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS crawl_runs (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
                plugin_id TEXT NOT NULL,
                target TEXT NOT NULL,
                seed_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                summary_json TEXT NOT NULL DEFAULT '{}',
                pages_json TEXT NOT NULL DEFAULT '[]',
                forms_json TEXT NOT NULL DEFAULT '[]',
                scripts_json TEXT NOT NULL DEFAULT '[]',
                params_json TEXT NOT NULL DEFAULT '[]',
                api_hints_json TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS asset_services (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'default',
                task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
                plugin_id TEXT NOT NULL,
                target TEXT NOT NULL,
                asset_id TEXT,
                host TEXT NOT NULL,
                ip TEXT,
                port INTEGER,
                protocol TEXT,
                service TEXT,
                product TEXT,
                version TEXT,
                cpe TEXT,
                confidence REAL,
                title TEXT,
                banner TEXT,
                cert_subject TEXT,
                cert_san_json TEXT NOT NULL DEFAULT '[]',
                cert_expiry TEXT,
                service_fingerprint TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
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
                owner_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                UNIQUE(owner_id, name)
                );



CREATE INDEX IF NOT EXISTS idx_credential_vault_owner
ON credential_vault(owner_id);

            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT 'default',
                schedule_seconds INTEGER,
                schedule_timezone TEXT,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                steps_json TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                last_run_at TIMESTAMP,
                UNIQUE(owner_id, name)
            );

            CREATE TABLE IF NOT EXISTS workflow_versions (
                id              TEXT PRIMARY KEY,
                workflow_id     TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                version_number  INTEGER NOT NULL,
                definition_json TEXT NOT NULL,
                created_at      TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                created_by      TEXT NOT NULL DEFAULT 'system',
                UNIQUE(workflow_id, version_number)
            );

            CREATE INDEX IF NOT EXISTS idx_wf_versions_workflow ON workflow_versions(workflow_id, version_number DESC);

            CREATE TABLE IF NOT EXISTS workflow_runs (
                id              TEXT PRIMARY KEY,
                workflow_id     TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                version_id      TEXT REFERENCES workflow_versions(id) ON DELETE SET NULL,
                version_number  INTEGER,
                triggered_by    TEXT NOT NULL DEFAULT 'manual',
                status          TEXT NOT NULL DEFAULT 'queued',
                task_ids_json   TEXT NOT NULL DEFAULT '[]',
                started_at      TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                completed_at    TIMESTAMP,
                error_message   TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_wf_runs_workflow   ON workflow_runs(workflow_id, started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_wf_runs_status     ON workflow_runs(status);
            CREATE INDEX IF NOT EXISTS idx_wf_runs_version_id ON workflow_runs(version_id);

            CREATE TABLE IF NOT EXISTS notification_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT 'default',
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

            -- Per-owner webhook fired on scan completion/failure (issue #1615).
            -- Distinct from notification_rules, which fires per-finding above a
            -- severity threshold; this fires once per scan regardless of severity.
            CREATE TABLE IF NOT EXISTS scan_webhook_settings (
                owner_id TEXT PRIMARY KEY,
                webhook_url TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );

            -- Tasks indexes (existing)
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_target ON tasks(target);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_plugin ON tasks(plugin_id);
            -- Composite index for dashboard running tasks query
            CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at DESC);
            -- Owner scoping (BOLA prevention, issue #401)
            CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_execution_context ON tasks(owner_id, plugin_id, created_at DESC);

            -- Findings indexes (new)
            CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
            CREATE INDEX IF NOT EXISTS idx_findings_task_id ON findings(task_id);
            CREATE INDEX IF NOT EXISTS idx_findings_discovered_at ON findings(discovered_at DESC);
            CREATE INDEX IF NOT EXISTS idx_findings_plugin_id ON findings(plugin_id);
            CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target);
            -- Composite index for severity counting by task
            CREATE INDEX IF NOT EXISTS idx_findings_task_severity ON findings(task_id, severity);
            -- Owner scoping (BOLA prevention, issue #401)
            CREATE INDEX IF NOT EXISTS idx_findings_owner ON findings(owner_id);
            CREATE INDEX IF NOT EXISTS idx_findings_cpe ON findings(cpe);
            CREATE INDEX IF NOT EXISTS idx_findings_validated ON findings(validated);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_findings_group_id ON findings(owner_id, finding_group_id);
            CREATE INDEX IF NOT EXISTS idx_findings_asset_id ON findings(owner_id, asset_id);

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
            CREATE INDEX IF NOT EXISTS idx_target_policies_owner ON target_policies(owner_id);
            CREATE INDEX IF NOT EXISTS idx_credential_profiles_owner ON credential_profiles(owner_id);
            CREATE INDEX IF NOT EXISTS idx_session_profiles_owner ON session_profiles(owner_id);
            CREATE INDEX IF NOT EXISTS idx_crawl_runs_task_id ON crawl_runs(task_id);
            CREATE INDEX IF NOT EXISTS idx_crawl_runs_owner_created ON crawl_runs(owner_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_asset_services_task_id ON asset_services(task_id);
            CREATE INDEX IF NOT EXISTS idx_asset_services_owner_created ON asset_services(owner_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_asset_services_asset_id ON asset_services(owner_id, asset_id);
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
                        id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL DEFAULT 'default',
                        name TEXT NOT NULL,
                        encrypted_value TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                        updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                        UNIQUE(owner_id, name)
                        );


            INSERT INTO credential_vault_new
            (
                id,
                owner_id,
                name,
                encrypted_value,
                created_at,
                updated_at
            )
            SELECT
                id,
                COALESCE(owner_id, 'default'),
                name,
                encrypted_value,
                created_at,
                updated_at
            FROM credential_vault;

            DROP TABLE credential_vault;
            ALTER TABLE credential_vault_new
            RENAME TO credential_vault;
        """)
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

        # On legacy databases the old CREATE TABLE had UNIQUE on name alone,
        # which blocks same-named workflows across owners.  SQLite cannot
        # ALTER TABLE … DROP CONSTRAINT, so we must recreate the table.
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
                        CREATE TABLE workflows_new (
                            id TEXT PRIMARY KEY,
                            name TEXT NOT NULL,
                            owner_id TEXT NOT NULL DEFAULT 'default',
                            schedule_seconds INTEGER,
                            enabled BOOLEAN NOT NULL DEFAULT 1,
                            steps_json TEXT NOT NULL DEFAULT '[]',
                            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                            last_run_at TIMESTAMP,
                            UNIQUE(owner_id, name)
                        );
                        INSERT INTO workflows_new
                            (id, name, owner_id, schedule_seconds, enabled,
                             steps_json, created_at, last_run_at)
                        SELECT
                            id, name, COALESCE(owner_id, 'default'),
                            schedule_seconds, enabled, steps_json, created_at, last_run_at
                        FROM workflows;
                        DROP TABLE workflows;
                        ALTER TABLE workflows_new RENAME TO workflows;
                    """)
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
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_id);
            CREATE INDEX IF NOT EXISTS idx_findings_owner ON findings(owner_id);
            CREATE INDEX IF NOT EXISTS idx_reports_owner ON reports(owner_id);
            CREATE INDEX IF NOT EXISTS idx_credential_vault_owner ON credential_vault(owner_id);
            CREATE INDEX IF NOT EXISTS idx_workflows_owner ON workflows(owner_id);
            CREATE INDEX IF NOT EXISTS idx_notification_rules_owner ON notification_rules(owner_id);
            CREATE INDEX IF NOT EXISTS idx_notification_history_owner ON notification_history(owner_id);
            """
            )


    async def _ensure_schema_migrations_table(self):
        """Create the migration tracking table if it does not already exist."""
        await self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await self.connection.commit()

    async def _applied_migrations(self) -> set[str]:
        """Return the set of migration filenames already applied."""
        rows = await self.fetchall(
            "SELECT version FROM schema_migrations"
        )
        return {row["version"] for row in rows}

    async def _validate_schema_version(self):
        """Ensure the database was not created by a newer application."""

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
        """Record a successfully applied migration."""
        await self.execute(
            """
            INSERT INTO schema_migrations(version)
            VALUES (?)
            """,
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

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncIterator["Database"]:
        """Context manager for atomic transactions.

        Usage::

            async with db.transaction():
                await db.execute("INSERT INTO ...")
                await db.execute("UPDATE ...")

        If any statement raises, the entire transaction is rolled back.
        On success the transaction is committed automatically.

        Nested calls are safe: when a transaction is already active the
        inner context manager becomes a no-op so the outer transaction
        controls the commit/rollback.
        """
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
        """Execute a write query and return the cursor (so callers can inspect rowcount)."""
        cursor = await self.connection.execute(query, params)
        if not self._in_transaction:
            await self.connection.commit()
        return cursor

    async def execute_no_commit(self, query: str, params: tuple = ()):
        """Execute a write query without committing (for use inside transactions)."""
        cursor = await self.connection.execute(query, params)
        return cursor

    async def begin(self):
        """Begin a transaction. No-op if already in a transaction."""
        if self._in_transaction:
            return
        await self.connection.execute("BEGIN")
        self._in_transaction = True

    async def commit(self):
        """Commit the current transaction. No-op if not in a transaction."""
        if not self._in_transaction:
            return
        await self.connection.commit()
        self._in_transaction = False

    async def rollback(self):
        """Roll back the current transaction. No-op if not in a transaction."""
        if not self._in_transaction:
            return
        await self.connection.rollback()
        self._in_transaction = False

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
        """Snapshot the current workflow definition as a new version row.

        Returns the new version record including its auto-assigned version_number.
        The version_number is the next integer in the per-workflow sequence.
        """
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
        """Return all versions for a workflow ordered newest first."""
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
        """Return a specific version record or None if it does not exist."""
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
        """Insert a workflow run record and return the run ID."""
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
        """Mark a workflow run as completed, failed, or cancelled with a timestamp.

        status must be one of: completed | failed | cancelled.
        This is called once all tasks in the run reach a terminal state.
        """
        await self.execute(
            "UPDATE workflow_runs SET status = ?, completed_at = datetime('now'), error_message = ? "
            "WHERE id = ?",
            (status, error_message, run_id),
        )

    async def check_workflow_run_tasks(self, run_id: str) -> Optional[str]:
        """Inspect the task statuses for a run and return the appropriate run status.

        Returns:
          'completed' if all tasks are completed.
          'failed'    if any task failed and none are still running/queued.
          'cancelled' if any task was cancelled and none are still running/queued.
          None        if tasks are still in progress.
        """
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
        """Return paginated run history for a workflow."""
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
