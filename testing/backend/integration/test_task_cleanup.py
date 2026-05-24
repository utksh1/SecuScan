"""
Backend integration tests for task cancellation and cleanup endpoints.
Issue #30 - covers: cancel, single delete, bulk delete, clear all, missing ID errors.
"""

import asyncio
import json
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


def make_get_db(db):
    async def _get_db():
        return db
    return _get_db


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