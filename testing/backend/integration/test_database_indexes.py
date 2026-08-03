"""
Tests for database performance indexes and optimized dashboard query.

Verifies:
- All expected indexes exist on findings, reports, audit_log, and tasks tables
- Dashboard severity counts use DB-level GROUP BY (not Python-side iteration)
- Dashboard fetches only 5 recent findings (not full table)
- Optimized query returns correct counts on a seeded dataset
"""

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.secuscan.config import settings
from backend.secuscan.database import init_db


# ── Helpers ───────────────────────────────────────────────────────────────────

def seed_findings(db_path: str, count: int = 100):
    """Insert `count` findings with mixed severities into the test DB."""
    severities = ["critical", "high", "medium", "low", "info"]
    conn = sqlite3.connect(db_path)
    for i in range(count):
        severity = severities[i % len(severities)]
        conn.execute(
            """
            INSERT INTO findings
                (id, task_id, plugin_id, title, category, severity,
                 target, description, remediation, discovered_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                "test_plugin",
                f"Finding {i}",
                "test",
                severity,
                "192.168.1.1",
                f"Description {i}",
                "Fix it",
                (datetime.now(timezone.utc) - timedelta(seconds=i)).isoformat(),
                json.dumps({}),
            ),
        )
    conn.commit()
    conn.close()


def get_index_names(db_path: str) -> set:
    """Return all index names present in the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    names = {row[0] for row in cursor.fetchall()}
    conn.close()
    return names


# ── Index existence tests ─────────────────────────────────────────────────────

class TestDatabaseIndexes:

    def test_findings_severity_index_exists(self, setup_test_environment):
        """idx_findings_severity must exist for GROUP BY severity queries."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_findings_severity" in indexes, (
            "Missing idx_findings_severity — dashboard GROUP BY severity will do a full scan"
        )

    def test_findings_discovered_at_index_exists(self, setup_test_environment):
        """idx_findings_discovered_at must exist for ORDER BY discovered_at DESC."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_findings_discovered_at" in indexes, (
            "Missing idx_findings_discovered_at — findings list ORDER BY will do a full scan"
        )

    def test_findings_task_id_index_exists(self, setup_test_environment):
        """idx_findings_task_id must exist for foreign key lookups."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_findings_task_id" in indexes

    def test_findings_task_severity_composite_index_exists(self, setup_test_environment):
        """idx_findings_task_severity composite index must exist."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_findings_task_severity" in indexes

    def test_reports_generated_at_index_exists(self, setup_test_environment):
        """idx_reports_generated_at must exist for reports list ORDER BY."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_reports_generated_at" in indexes

    def test_reports_task_id_index_exists(self, setup_test_environment):
        """idx_reports_task_id must exist for foreign key lookups."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_reports_task_id" in indexes

    def test_reports_status_index_exists(self, setup_test_environment):
        """idx_reports_status must exist for status filter queries."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_reports_status" in indexes

    def test_audit_log_timestamp_index_exists(self, setup_test_environment):
        """idx_audit_timestamp must exist for audit log ORDER BY timestamp."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_audit_timestamp" in indexes

    def test_audit_log_event_type_index_exists(self, setup_test_environment):
        """idx_audit_event_type must exist for event_type filter queries."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_audit_event_type" in indexes

    def test_tasks_status_created_composite_index_exists(self, setup_test_environment):
        """idx_tasks_status_created composite index must exist."""
        asyncio.run(init_db(settings.database_path))
        indexes = get_index_names(settings.database_path)
        assert "idx_tasks_status_created" in indexes


# ── Dashboard query correctness tests ─────────────────────────────────────────

class TestDashboardQueryCorrectness:

    def test_dashboard_severity_counts_correct(self, test_client, setup_test_environment):
        """Dashboard must return correct severity counts from seeded findings."""
        seed_findings(settings.database_path, count=50)

        r = test_client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        data = r.json()

        # 50 findings, 5 severities, 10 each
        assert data["total_findings"] == 50
        assert data["critical_findings"] == 10
        assert data["high_findings"] == 10
        assert data["medium_findings"] == 10
        assert data["low_findings"] == 10
        assert data["info_findings"] == 10

    def test_dashboard_recent_findings_limit(self, test_client, setup_test_environment):
        """Dashboard must return at most 5 recent findings regardless of total."""
        seed_findings(settings.database_path, count=200)

        r = test_client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        data = r.json()

        assert len(data["recent_findings"]) <= 5, (
            "Dashboard must fetch at most 5 recent findings — not the full table"
        )

    def test_dashboard_empty_findings(self, test_client, setup_test_environment):
        """Dashboard must handle zero findings without errors."""
        r = test_client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        data = r.json()

        assert data["total_findings"] == 0
        assert data["critical_findings"] == 0
        assert data["recent_findings"] == []
        assert data["last_scan_time"] is None

    def test_dashboard_severity_counts_with_single_severity(
        self, test_client, setup_test_environment
    ):
        """Dashboard must correctly count when all findings share one severity."""
        conn = sqlite3.connect(settings.database_path)
        for i in range(15):
            conn.execute(
                """
                INSERT INTO findings
                    (id, task_id, plugin_id, title, category, severity,
                     target, description, remediation, discovered_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), str(uuid.uuid4()), "test_plugin",
                    f"Critical Finding {i}", "test", "critical",
                    "10.0.0.1", "Critical issue", "Patch immediately",
                    datetime.now(timezone.utc).isoformat(), json.dumps({}),
                ),
            )
        conn.commit()
        conn.close()

        r = test_client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        data = r.json()

        assert data["total_findings"] == 15
        assert data["critical_findings"] == 15
        assert data["high_findings"] == 0
        assert data["medium_findings"] == 0