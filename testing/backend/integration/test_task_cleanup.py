"""
Integration tests for SecuScan task cancellation and cleanup endpoints.
Issue #30 — Add backend tests for task cancellation and cleanup endpoints.

Test file location: testing/backend/integration/test_task_cleanup.py
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_path(tmp_path):
    """Return a path to a fresh temp SQLite file (schema created by init_db)."""
    return str(tmp_path / "test_secuscan.db")


@pytest_asyncio.fixture
async def app_client(db_path):
    """
    Yield an AsyncClient wired to the FastAPI app with:
      - a real isolated temp SQLite DB (schema auto-created by init_db)
      - a real in-memory cache (init_cache — no Redis needed)
      - executor fully mocked (no real scans)
    """
    mock_executor = MagicMock()
    mock_executor.cancel_task = AsyncMock(return_value=True)
    mock_executor.get_task_status = AsyncMock(return_value={"status": "queued"})

    with patch("backend.secuscan.routes.executor", mock_executor):

        from backend.secuscan.main import app
        from backend.secuscan import database as db_module
        from backend.secuscan import cache as cache_module

        # Initialise a real in-memory cache (it's just a dict, no external deps)
        await cache_module.init_cache()

        # Initialise a fresh DB pointing at our temp file
        test_db = await db_module.init_db(db_path)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            client._mock_executor = mock_executor
            client._db = test_db
            client._db_path = db_path
            yield client

        # Teardown
        await test_db.disconnect()
        db_module.db = None
        await cache_module.cache.disconnect()
        cache_module.cache = None


# ---------------------------------------------------------------------------
# DB helpers — read directly from the temp DB to verify side effects
# ---------------------------------------------------------------------------

async def db_fetchall(db_path: str, sql: str, params=()):
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Seed helpers — insert test data directly into the temp DB
# ---------------------------------------------------------------------------

async def insert_task(db, status: str = "completed",
                      raw_output_path: str = None) -> str:
    task_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO tasks "
        "(id, plugin_id, tool_name, target, status, inputs_json, raw_output_path, consent_granted) "
        "VALUES (?, 'nmap', 'nmap', '127.0.0.1', ?, '{}', ?, 1)",
        (task_id, status, raw_output_path),
    )
    return task_id


async def insert_finding(db, task_id: str) -> str:
    finding_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO findings "
        "(id, task_id, plugin_id, title, category, severity, target, description, remediation) "
        "VALUES (?, ?, 'nmap', 'Open port', 'network', 'low', '127.0.0.1', 'desc', 'fix')",
        (finding_id, task_id),
    )
    return finding_id


async def insert_report(db, task_id: str) -> str:
    report_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO reports (id, task_id, name, type, status) "
        "VALUES (?, ?, 'report', 'pdf', 'ready')",
        (report_id, task_id),
    )
    return report_id


async def insert_audit_log(db, task_id: str):
    await db.execute(
        "INSERT INTO audit_log (event_type, severity, message, task_id) "
        "VALUES ('scan_start', 'info', 'started', ?)",
        (task_id,),
    )


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/task/{task_id}/cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_queued_task_returns_200(app_client):
    """Cancelling a queued task returns 200 with status='cancelled'."""
    db = app_client._db
    task_id = await insert_task(db, status="queued")
    app_client._mock_executor.cancel_task = AsyncMock(return_value=True)

    resp = await app_client.post(f"/api/v1/task/{task_id}/cancel")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task_id"] == task_id
    assert body["status"] == "cancelled"
    assert "cancelled_at" in body


@pytest.mark.asyncio
async def test_cancel_missing_task_returns_404(app_client):
    """Cancelling a non-existent task returns 404."""
    app_client._mock_executor.cancel_task = AsyncMock(return_value=None)

    resp = await app_client.post(f"/api/v1/task/{uuid.uuid4()}/cancel")

    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Tests: DELETE /api/v1/task/{task_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_task_returns_200_and_removes_row(app_client):
    """Deleting a completed task removes it from the DB and returns 200."""
    db = app_client._db
    db_path = app_client._db_path
    task_id = await insert_task(db, status="completed")

    resp = await app_client.delete(f"/api/v1/task/{task_id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task_id"] == task_id
    assert body["deleted"] is True

    rows = await db_fetchall(db_path, "SELECT id FROM tasks WHERE id = ?", (task_id,))
    assert len(rows) == 0, "Task row should have been deleted from the DB"


@pytest.mark.asyncio
async def test_delete_task_also_removes_associated_records(app_client):
    """Deleting a task cascades to findings, reports, and audit_log."""
    db = app_client._db
    db_path = app_client._db_path
    task_id = await insert_task(db, status="completed")
    finding_id = await insert_finding(db, task_id)
    report_id = await insert_report(db, task_id)
    await insert_audit_log(db, task_id)

    resp = await app_client.delete(f"/api/v1/task/{task_id}")
    assert resp.status_code == 200, resp.text

    rows = await db_fetchall(db_path, "SELECT id FROM findings WHERE id = ?", (finding_id,))
    assert len(rows) == 0, "Finding should have been deleted"

    rows = await db_fetchall(db_path, "SELECT id FROM reports WHERE id = ?", (report_id,))
    assert len(rows) == 0, "Report should have been deleted"

    rows = await db_fetchall(db_path, "SELECT id FROM audit_log WHERE task_id = ?", (task_id,))
    assert len(rows) == 0, "Audit log rows should have been deleted"


@pytest.mark.asyncio
async def test_delete_running_task_returns_400(app_client):
    """Attempting to delete a running task must return 400.

    The route checks executor.get_task_status(), not the DB status field,
    so we make the mock report the task as running.
    """
    db = app_client._db
    task_id = await insert_task(db, status="running")

    # Make executor report this task as actively running
    app_client._mock_executor.get_task_status = AsyncMock(
        return_value={"status": "running"}
    )

    resp = await app_client.delete(f"/api/v1/task/{task_id}")

    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_delete_missing_task_returns_200(app_client):
    """Deleting a task that doesn't exist returns 200 (route is idempotent).

    The delete endpoint calls delete_task_records() which issues DELETE SQL —
    deleting zero rows is not treated as an error by this implementation.
    """
    resp = await app_client.delete(f"/api/v1/task/{uuid.uuid4()}")

    # The route succeeds silently when the task doesn't exist
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deleted"] is True


@pytest.mark.asyncio
async def test_delete_task_removes_raw_output_file(app_client, tmp_path):
    """If the task has a raw_output_path, that file is deleted from disk."""
    db = app_client._db

    raw_file = tmp_path / "scan_output.txt"
    raw_file.write_text("nmap output data")
    assert raw_file.exists()

    task_id = await insert_task(db, status="completed",
                                raw_output_path=str(raw_file))

    resp = await app_client.delete(f"/api/v1/task/{task_id}")
    assert resp.status_code == 200, resp.text

    assert not raw_file.exists(), "raw_output_path file should have been deleted from disk"


@pytest.mark.asyncio
async def test_completed_task_stream_replays_raw_output_in_chunks(app_client, tmp_path):
    """Completed-task SSE must not read and send the full raw output in one event."""
    from backend.secuscan.routes import SSE_RAW_OUTPUT_CHUNK_SIZE

    raw_output = "a" * SSE_RAW_OUTPUT_CHUNK_SIZE + "tail"
    raw_file = tmp_path / "large_scan_output.txt"
    raw_file.write_text(raw_output)

    task_id = await insert_task(
        app_client._db,
        status="completed",
        raw_output_path=str(raw_file),
    )
    app_client._mock_executor.get_task_status = AsyncMock(
        return_value={"status": "completed"}
    )

    resp = await app_client.get(f"/api/v1/task/{task_id}/stream")

    assert resp.status_code == 200, resp.text
    event_name = None
    output_chunks = []
    for line in resp.text.splitlines():
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ")
        elif line.startswith("data: ") and event_name == "output":
            output_chunks.append(json.loads(line.removeprefix("data: "))["chunk"])

    assert len(output_chunks) == 2
    assert all(len(chunk) <= SSE_RAW_OUTPUT_CHUNK_SIZE for chunk in output_chunks)
    assert "".join(output_chunks) == raw_output


# ---------------------------------------------------------------------------
# Tests: DELETE /api/v1/tasks/bulk
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bulk_delete_removes_only_requested_tasks(app_client):
    """Bulk delete removes listed tasks but leaves others untouched."""
    db = app_client._db
    db_path = app_client._db_path

    task_a = await insert_task(db, status="completed")
    task_b = await insert_task(db, status="completed")
    task_c = await insert_task(db, status="completed")  # must survive

    resp = await app_client.request(
        "DELETE", "/api/v1/tasks/bulk", json=[task_a, task_b],
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["deleted_count"] == 2

    for tid in (task_a, task_b):
        rows = await db_fetchall(db_path, "SELECT id FROM tasks WHERE id = ?", (tid,))
        assert len(rows) == 0, f"Task {tid} should have been deleted"

    rows = await db_fetchall(db_path, "SELECT id FROM tasks WHERE id = ?", (task_c,))
    assert len(rows) == 1, "task_c should NOT have been deleted"


@pytest.mark.asyncio
async def test_bulk_delete_with_running_task_returns_400(app_client):
    """Bulk delete containing a running task returns 400; nothing is deleted."""
    db = app_client._db
    db_path = app_client._db_path

    task_ok = await insert_task(db, status="completed")
    task_running = await insert_task(db, status="running")

    resp = await app_client.request(
        "DELETE", "/api/v1/tasks/bulk", json=[task_ok, task_running],
    )

    assert resp.status_code == 400, resp.text

    for tid in (task_ok, task_running):
        rows = await db_fetchall(db_path, "SELECT id FROM tasks WHERE id = ?", (tid,))
        assert len(rows) == 1, f"Task {tid} should NOT have been deleted after 400"


# ---------------------------------------------------------------------------
# Tests: DELETE /api/v1/tasks/clear
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clear_all_tasks_removes_everything(app_client):
    """Clear endpoint deletes all tasks, findings, reports, and audit_log rows."""
    db = app_client._db
    db_path = app_client._db_path

    for _ in range(3):
        tid = await insert_task(db, status="completed")
        await insert_finding(db, tid)
        await insert_report(db, tid)
        await insert_audit_log(db, tid)

    resp = await app_client.delete("/api/v1/tasks/clear")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cleared"] is True
    assert "message" in body

    for table in ("tasks", "findings", "reports", "audit_log"):
        rows = await db_fetchall(db_path, f"SELECT 1 FROM {table}")
        assert len(rows) == 0, f"Table '{table}' should be empty after /clear"


@pytest.mark.asyncio
async def test_clear_while_task_running_returns_400(app_client):
    """Clear returns 400 when any task is still running; nothing is deleted."""
    db = app_client._db
    db_path = app_client._db_path

    await insert_task(db, status="completed")
    await insert_task(db, status="running")

    resp = await app_client.delete("/api/v1/tasks/clear")

    assert resp.status_code == 400, resp.text

    rows = await db_fetchall(db_path, "SELECT id FROM tasks")
    assert len(rows) == 2, "No tasks should have been deleted after a 400 clear"
