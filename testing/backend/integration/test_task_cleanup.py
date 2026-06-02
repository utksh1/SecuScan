"""
Backend integration tests for task cancellation and cleanup endpoints.
Issue #30 - covers: cancel, single delete, bulk delete, clear all, missing ID errors.
"""

<<<<<<< HEAD
import asyncio
import json
=======
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
>>>>>>> upstream/main
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.secuscan.database import Database
from backend.secuscan.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def make_db():
    db = Database(":memory:")
    await db.connect()
    return db


<<<<<<< HEAD
def make_get_db(db):
    async def _get_db():
        return db
    return _get_db
=======
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
        from backend.secuscan import auth as auth_module
        import tempfile

        # Initialise a real in-memory cache (it's just a dict, no external deps)
        await cache_module.init_cache()

        # Initialise a fresh DB pointing at our temp file
        test_db = await db_module.init_db(db_path)

        # Initialise API key in a temporary directory so the dependency resolves
        with tempfile.TemporaryDirectory() as tmp_auth_dir:
            api_key = auth_module.init_api_key(tmp_auth_dir)

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-Api-Key": api_key},
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
>>>>>>> upstream/main


async def insert_task(db, task_id="task-1", status="queued", raw_output_path=None):
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, inputs_json, raw_output_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "http_inspector", "http_inspector", "http://test.local", status, "{}", raw_output_path),
    )


async def insert_finding(db, finding_id="finding-1", task_id="task-1"):
    await db.execute(
        """
        INSERT INTO findings (id, task_id, plugin_id, title, category, severity, target, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (finding_id, task_id, "http_inspector", "Test Finding", "web", "high", "http://test.local", "desc"),
    )


async def insert_report(db, report_id="report-1", task_id="task-1"):
    await db.execute(
        """
        INSERT INTO reports (id, task_id, name, type, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (report_id, task_id, "Test Report", "technical", "ready"),
    )


async def insert_audit_log(db, task_id="task-1"):
    await db.execute(
        """
        INSERT INTO audit_log (event_type, severity, message, task_id)
        VALUES (?, ?, ?, ?)
        """,
        ("task_created", "info", "Task created", task_id),
    )


# ---------------------------------------------------------------------------
# 1. Cancel task
# ---------------------------------------------------------------------------

class TestCancelTask:

    def test_cancel_queued_task_returns_200(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="task-cancel-1", status="queued")

            mock_executor = AsyncMock()
            mock_executor.cancel_task = AsyncMock(return_value=True)

            with patch("backend.secuscan.routes.executor", mock_executor), \
                 patch("backend.secuscan.routes.get_db", make_get_db(db)):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post("/api/v1/task/task-cancel-1/cancel")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "cancelled"
            assert data["task_id"] == "task-cancel-1"

        asyncio.run(run())

    def test_cancel_missing_task_returns_404(self):
        async def run():
            mock_executor = AsyncMock()
            mock_executor.cancel_task = AsyncMock(return_value=False)

            with patch("backend.secuscan.routes.executor", mock_executor):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post("/api/v1/task/nonexistent-id/cancel")

            assert response.status_code == 404

        asyncio.run(run())


# ---------------------------------------------------------------------------
# 2. Delete single task
# ---------------------------------------------------------------------------

class TestDeleteSingleTask:

    def test_delete_task_returns_200(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="task-del-1", status="queued")

            mock_executor = AsyncMock()
            mock_executor.get_task_status = AsyncMock(return_value={"status": "queued"})

            with patch("backend.secuscan.routes.executor", mock_executor), \
                 patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.delete("/api/v1/task/task-del-1")

            assert response.status_code == 200
            assert response.json()["deleted"] is True

        asyncio.run(run())

    def test_delete_task_removes_from_db(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="task-del-2", status="queued")

            mock_executor = AsyncMock()
            mock_executor.get_task_status = AsyncMock(return_value={"status": "queued"})

            with patch("backend.secuscan.routes.executor", mock_executor), \
                 patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    await ac.delete("/api/v1/task/task-del-2")

            row = await db.fetchone("SELECT id FROM tasks WHERE id = ?", ("task-del-2",))
            assert row is None

        asyncio.run(run())

    def test_delete_task_removes_findings_and_reports(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="task-del-3", status="queued")
            await insert_finding(db, finding_id="f-1", task_id="task-del-3")
            await insert_report(db, report_id="r-1", task_id="task-del-3")
            await insert_audit_log(db, task_id="task-del-3")

            mock_executor = AsyncMock()
            mock_executor.get_task_status = AsyncMock(return_value={"status": "queued"})

            with patch("backend.secuscan.routes.executor", mock_executor), \
                 patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    await ac.delete("/api/v1/task/task-del-3")

            findings = await db.fetchall("SELECT id FROM findings WHERE task_id = ?", ("task-del-3",))
            reports = await db.fetchall("SELECT id FROM reports WHERE task_id = ?", ("task-del-3",))
            audit = await db.fetchall("SELECT id FROM audit_log WHERE task_id = ?", ("task-del-3",))

            assert findings == []
            assert reports == []
            assert audit == []

        asyncio.run(run())

    def test_delete_running_task_returns_400(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="task-running-1", status="running")

            mock_executor = AsyncMock()
            mock_executor.get_task_status = AsyncMock(return_value={"status": "running"})

            with patch("backend.secuscan.routes.executor", mock_executor), \
                 patch("backend.secuscan.routes.get_db", make_get_db(db)):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.delete("/api/v1/task/task-running-1")

            assert response.status_code == 400

        asyncio.run(run())

    def test_delete_task_removes_output_file(self):
        async def run():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
                tmp_path = f.name
                f.write(b"scan output")

            assert os.path.exists(tmp_path)

            db = await make_db()
            await insert_task(db, task_id="task-file-1", status="queued", raw_output_path=tmp_path)

            mock_executor = AsyncMock()
            mock_executor.get_task_status = AsyncMock(return_value={"status": "queued"})

            with patch("backend.secuscan.routes.executor", mock_executor), \
                 patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    await ac.delete("/api/v1/task/task-file-1")

            assert not os.path.exists(tmp_path)

        asyncio.run(run())


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
# 3. Bulk delete
# ---------------------------------------------------------------------------

class TestBulkDeleteTasks:

    def test_bulk_delete_removes_only_requested_tasks(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="bulk-1", status="queued")
            await insert_task(db, task_id="bulk-2", status="queued")
            await insert_task(db, task_id="bulk-3", status="queued")

            with patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.request(
                        "DELETE",
                        "/api/v1/tasks/bulk",
                        json=["bulk-1", "bulk-2"],
                    )

            assert response.status_code == 200
            assert response.json()["deleted_count"] == 2

            surviving = await db.fetchone("SELECT id FROM tasks WHERE id = ?", ("bulk-3",))
            assert surviving is not None

            for gone_id in ("bulk-1", "bulk-2"):
                row = await db.fetchone("SELECT id FROM tasks WHERE id = ?", (gone_id,))
                assert row is None

        asyncio.run(run())

    def test_bulk_delete_blocks_running_tasks(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="bulk-run-1", status="running")
            await insert_task(db, task_id="bulk-run-2", status="queued")

            with patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.request(
                        "DELETE",
                        "/api/v1/tasks/bulk",
                        json=["bulk-run-1", "bulk-run-2"],
                    )

            assert response.status_code == 400

        asyncio.run(run())


# ---------------------------------------------------------------------------
# 4. Clear all tasks
# ---------------------------------------------------------------------------

class TestClearAllTasks:

    def test_clear_all_removes_all_tasks(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="clear-1", status="queued")
            await insert_task(db, task_id="clear-2", status="completed")

            mock_settings = MagicMock()
            mock_settings.data_dir = tempfile.mkdtemp()

            with patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()), \
                 patch("backend.secuscan.routes.settings", mock_settings):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.delete("/api/v1/tasks/clear")

            assert response.status_code == 200
            assert response.json()["cleared"] is True

            count = await db.fetchone("SELECT COUNT(*) as total FROM tasks")
            assert count["total"] == 0

        asyncio.run(run())

    def test_clear_all_removes_findings(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="clear-3", status="queued")
            await insert_finding(db, finding_id="f-clear-1", task_id="clear-3")

            mock_settings = MagicMock()
            mock_settings.data_dir = tempfile.mkdtemp()

            with patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()), \
                 patch("backend.secuscan.routes.settings", mock_settings):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    await ac.delete("/api/v1/tasks/clear")

            count = await db.fetchone("SELECT COUNT(*) as total FROM findings")
            assert count["total"] == 0

        asyncio.run(run())

    def test_clear_all_blocks_if_running(self):
        async def run():
            db = await make_db()
            await insert_task(db, task_id="clear-running-1", status="running")

            with patch("backend.secuscan.routes.get_db", make_get_db(db)), \
                 patch("backend.secuscan.routes.invalidate_view_cache", AsyncMock()):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.delete("/api/v1/tasks/clear")

            assert response.status_code == 400

        asyncio.run(run())