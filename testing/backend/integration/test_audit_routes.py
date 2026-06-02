"""
Tests for audit log API routes — /api/v1/audit and /api/v1/audit/export,
plus verification that delete_task_records preserves audit_log entries.
"""

import uuid

import aiosqlite
import pytest


@pytest.fixture
def db_path(test_client):
    """Return the DB path used by test_client by reading settings after setup."""
    from backend.secuscan.config import settings
    return settings.database_path


def test_get_audit_logs_empty(test_client):
    response = test_client.get("/api/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["entries"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 50
    assert data["total_pages"] == 1


def test_get_audit_logs_with_data(test_client, db_path):
    import asyncio
    async def seed():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            for i in range(5):
                await conn.execute(
                    "INSERT INTO audit_log (id, event_type, severity, message, timestamp) "
                    "VALUES (?, 'scan_completed', 'info', ?, datetime('now'))",
                    (str(uuid.uuid4()), f"Scan {i} completed"),
                )
            await conn.commit()
    asyncio.run(seed())

    response = test_client.get("/api/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["entries"]) >= 5
    assert data["page"] == 1
    assert data["per_page"] == 50


def test_audit_pagination_bounds(test_client, db_path):
    import asyncio
    async def seed():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            for i in range(10):
                await conn.execute(
                    "INSERT INTO audit_log (id, event_type, severity, message, timestamp) "
                    "VALUES (?, 'scan_completed', 'info', ?, datetime('now'))",
                    (str(uuid.uuid4()), f"Batch {i}"),
                )
            await conn.commit()
    asyncio.run(seed())

    resp_page_1 = test_client.get("/api/v1/audit?page=1&per_page=3")
    assert resp_page_1.status_code == 200
    d1 = resp_page_1.json()
    assert len(d1["entries"]) == 3
    assert d1["total_pages"] == 4

    resp_page_2 = test_client.get("/api/v1/audit?page=2&per_page=3")
    assert resp_page_2.status_code == 200
    d2 = resp_page_2.json()
    assert len(d2["entries"]) == 3

    resp_page_4 = test_client.get("/api/v1/audit?page=4&per_page=3")
    assert resp_page_4.status_code == 200
    d4 = resp_page_4.json()
    assert len(d4["entries"]) == 1

    resp_page_5 = test_client.get("/api/v1/audit?page=5&per_page=3")
    assert resp_page_5.status_code == 200
    d5 = resp_page_5.json()
    assert d5["entries"] == []


def test_audit_filter_by_event_type(test_client, db_path):
    import asyncio
    async def seed():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            for evt in [("scan_start", "started", "info"),
                         ("scan_completed", "done", "info"),
                         ("task_deleted", "removed", "warning")]:
                await conn.execute(
                    "INSERT INTO audit_log (id, event_type, severity, message, timestamp) "
                    "VALUES (?, ?, ?, ?, datetime('now'))",
                    (str(uuid.uuid4()), evt[0], evt[2], evt[1]),
                )
            await conn.commit()
    asyncio.run(seed())

    resp = test_client.get("/api/v1/audit?event_type=scan_completed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for entry in data["entries"]:
        assert entry["event_type"] == "scan_completed"


def test_audit_export_json(test_client, db_path):
    import asyncio
    async def seed():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute(
                "INSERT INTO audit_log (id, event_type, severity, message, timestamp) "
                "VALUES (?, 'scan_start', 'info', ?, datetime('now'))",
                (str(uuid.uuid4()), "export test"),
            )
            await conn.commit()
    asyncio.run(seed())

    response = test_client.get("/api/v1/audit/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "filename=secuscan-audit-log.json" in response.headers["content-disposition"]
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_audit_export_csv(test_client, db_path):
    import asyncio
    async def seed():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute(
                "INSERT INTO audit_log (id, event_type, severity, message, timestamp) "
                "VALUES (?, 'scan_start', 'info', ?, datetime('now'))",
                (str(uuid.uuid4()), "csv export"),
            )
            await conn.commit()
    asyncio.run(seed())

    response = test_client.get("/api/v1/audit/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"
    assert "filename=secuscan-audit-log.csv" in response.headers["content-disposition"]
    body = response.text
    assert body.startswith("id,timestamp,event_type,severity,message,task_id,plugin_id,context")
    assert "csv export" in body


def test_audit_export_default_format_json(test_client):
    response = test_client.get("/api/v1/audit/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_audit_export_invalid_format(test_client):
    response = test_client.get("/api/v1/audit/export?format=xml")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_audit_log_preserved_on_task_deletion(test_client, db_path):
    import asyncio
    from unittest.mock import patch, AsyncMock, MagicMock

    from backend.secuscan.database import get_db

    async def seed():
        db = await get_db()
        task_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO tasks (id, plugin_id, tool_name, target, status, inputs_json, consent_granted) "
            "VALUES (?, 'nmap', 'nmap', '127.0.0.1', 'completed', '{}', 1)",
            (task_id,),
        )
        await db.log_audit(
            event_type="scan_completed",
            message=f"Task {task_id} completed",
            severity="info",
            task_id=task_id,
        )
        return task_id

    task_id = asyncio.run(seed())

    with patch("backend.secuscan.routes.executor") as mock_exec:
        mock_exec.get_task_status = AsyncMock(return_value={"status": "completed"})
        delete_resp = test_client.delete(f"/api/v1/task/{task_id}")
        assert delete_resp.status_code == 200

    async def verify():
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            rows = await conn.execute_fetchall(
                "SELECT id, event_type, message FROM audit_log WHERE task_id = ?",
                (task_id,),
            )
            assert len(rows) == 1
            assert rows[0][1] == "scan_completed"

    asyncio.run(verify())
