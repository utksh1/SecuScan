"""
Tests for audit log API routes — /api/v1/audit and /api/v1/audit/export,
plus verification that delete_task_records preserves audit_log entries.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def db_path(tmp_path):
    return str(tmp_path / "test_secuscan.db")


@pytest_asyncio.fixture
async def async_client(db_path):
    from backend.secuscan.main import app
    from backend.secuscan import database as db_module
    from backend.secuscan import cache as cache_module
    from backend.secuscan import auth as auth_module
    import tempfile

    await cache_module.init_cache()

    test_db = await db_module.init_db(db_path)

    with tempfile.TemporaryDirectory() as tmp_auth_dir:
        api_key = auth_module.init_api_key(tmp_auth_dir)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Api-Key": api_key},
        ) as client:
            client._db = test_db
            client._db_path = db_path
            yield client

    await test_db.disconnect()
    db_module.db = None
    await cache_module.cache.disconnect()
    cache_module.cache = None


@pytest.mark.asyncio
async def test_get_audit_logs_empty(async_client):
    response = await async_client.get("/api/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["entries"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 50
    assert data["total_pages"] == 1


@pytest.mark.asyncio
async def test_get_audit_logs_with_data(async_client):
    db = async_client._db
    for i in range(5):
        await db.log_audit(
            event_type="scan_completed",
            message=f"Scan {i} completed",
            severity="info",
            task_id=str(uuid.uuid4()),
        )

    response = await async_client.get("/api/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 5
    assert len(data["entries"]) >= 5
    assert data["page"] == 1
    assert data["per_page"] == 50


@pytest.mark.asyncio
async def test_audit_pagination_bounds(async_client):
    db = async_client._db
    for i in range(10):
        await db.log_audit(
            event_type="scan_completed",
            message=f"Batch {i}",
            severity="info",
        )

    resp_page_1 = await async_client.get("/api/v1/audit?page=1&per_page=3")
    assert resp_page_1.status_code == 200
    d1 = resp_page_1.json()
    assert len(d1["entries"]) == 3
    assert d1["total_pages"] == 4

    resp_page_2 = await async_client.get("/api/v1/audit?page=2&per_page=3")
    assert resp_page_2.status_code == 200
    d2 = resp_page_2.json()
    assert len(d2["entries"]) == 3

    resp_page_4 = await async_client.get("/api/v1/audit?page=4&per_page=3")
    assert resp_page_4.status_code == 200
    d4 = resp_page_4.json()
    assert len(d4["entries"]) == 1

    resp_page_5 = await async_client.get("/api/v1/audit?page=5&per_page=3")
    assert resp_page_5.status_code == 200
    d5 = resp_page_5.json()
    assert d5["entries"] == []


@pytest.mark.asyncio
async def test_audit_filter_by_event_type(async_client):
    db = async_client._db
    await db.log_audit(event_type="scan_start", message="started", severity="info")
    await db.log_audit(event_type="scan_completed", message="done", severity="info")
    await db.log_audit(event_type="task_deleted", message="removed", severity="warning")

    resp = await async_client.get("/api/v1/audit?event_type=scan_completed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for entry in data["entries"]:
        assert entry["event_type"] == "scan_completed"


@pytest.mark.asyncio
async def test_audit_export_json(async_client):
    db = async_client._db
    await db.log_audit(event_type="scan_start", message="export test", severity="info")

    response = await async_client.get("/api/v1/audit/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "filename=secuscan-audit-log.json" in response.headers["content-disposition"]
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_audit_export_csv(async_client):
    db = async_client._db
    await db.log_audit(event_type="scan_start", message="csv export", severity="info")

    response = await async_client.get("/api/v1/audit/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"
    assert "filename=secuscan-audit-log.csv" in response.headers["content-disposition"]
    body = response.text
    assert body.startswith("id,timestamp,event_type,severity,message,task_id,plugin_id,context")
    assert "csv export" in body


@pytest.mark.asyncio
async def test_audit_export_default_format_json(async_client):
    response = await async_client.get("/api/v1/audit/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_audit_export_invalid_format(async_client):
    response = await async_client.get("/api/v1/audit/export?format=xml")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_audit_log_preserved_on_task_deletion(async_client):
    db = async_client._db
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

    from unittest.mock import patch, AsyncMock, MagicMock
    with patch("backend.secuscan.routes.executor") as mock_exec:
        mock_exec.get_task_status = AsyncMock(return_value={"status": "completed"})
        delete_resp = await async_client.delete(f"/api/v1/task/{task_id}")
        assert delete_resp.status_code == 200

    tasks = await db.fetchall("SELECT id FROM tasks WHERE id = ?", (task_id,))
    assert len(tasks) == 0

    audit_rows = await db.fetchall(
        "SELECT id, event_type, message FROM audit_log WHERE task_id = ?",
        (task_id,),
    )
    assert len(audit_rows) == 1
    assert audit_rows[0]["event_type"] == "scan_completed"
