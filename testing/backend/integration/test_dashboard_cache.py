import asyncio
import sqlite3
import json

from unittest.mock import AsyncMock, patch
from backend.secuscan.config import settings


def test_dashboard_summary_second_request_hits_cache(test_client):
    """Repeated requests to /dashboard/summary must use cached data.

    The DB builder is invoked once for the first request. The second
    request returns the same payload from the in-memory cache without
    issuing new DB queries.
    """
    with (
        patch(
            "backend.secuscan.database.Database.fetchall",
            new_callable=AsyncMock,
        ) as mock_fetchall,
        patch(
            "backend.secuscan.database.Database.fetchone",
            new_callable=AsyncMock,
        ) as mock_fetchone,
    ):
        mock_fetchall.return_value = []
        mock_fetchone.return_value = {"total": 0, "completed": 0, "running": 0}

        r1 = test_client.get("/api/v1/dashboard/summary")
        assert r1.status_code == 200

        calls_after_first = mock_fetchall.call_count
        assert calls_after_first > 0, "first request must query the database"

        r2 = test_client.get("/api/v1/dashboard/summary")
        assert r2.status_code == 200

        assert mock_fetchall.call_count == calls_after_first, (
            "second request must not issue new DB queries — data should come from cache"
        )

        assert r1.json() == r2.json()


def test_dashboard_summary_cache_invalidated_after_task_start(test_client):
    """Starting a new task invalidates the summary cache.

    After a task is created the cache is cleared, so the next summary
    request rebuilds from the database.
    """
    with (
        patch(
            "backend.secuscan.database.Database.fetchall",
            new_callable=AsyncMock,
        ) as mock_fetchall,
        patch(
            "backend.secuscan.database.Database.fetchone",
            new_callable=AsyncMock,
        ) as mock_fetchone,
    ):
        mock_fetchall.return_value = []
        mock_fetchone.return_value = {"total": 0, "completed": 0, "running": 0}

        # Warm up the cache
        r1 = test_client.get("/api/v1/dashboard/summary")
        assert r1.status_code == 200
        calls_after_warm = mock_fetchall.call_count

        # A successful write (task start) should invalidate the cache.
        # We don't care whether the task actually starts; invalidation
        # happens even on a 400 response for an unknown plugin.
        test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "http_inspector",
                "inputs": {"url": "http://127.0.0.1:8000"},
                "consent_granted": True,
            },
        )

        # Next summary request must go back to the DB because the cache
        # was cleared.
        r2 = test_client.get("/api/v1/dashboard/summary")
        assert r2.status_code == 200
        assert mock_fetchall.call_count > calls_after_warm, (
            "post-invalidation request must rebuild from the database"
        )


def test_dashboard_summary_cache_invalidated_when_task_enters_running(test_client):
    """Transitioning a task to running must invalidate the summary cache.

    The race: /task/start invalidates before returning, but the background
    executor only schedules the scan. A dashboard poll between start and
    the first execute_task tick can cache a snapshot where running_tasks is
    empty. This test verifies that the cache is dropped as soon as the
    executor marks the task running, so the next poll reflects the real state.
    """
    # Seed a queued task directly so we control its state
    task_id = "cache-running-test-001"
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, created_at,
                           preset, inputs_json, command_used, structured_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, "http_inspector", "http_inspector", "https://example.com",
            "queued", "2026-05-19T10:00:00",
            "standard", json.dumps({"target": "https://example.com"}),
            "", json.dumps({"findings": []}),
        ),
    )
    conn.commit()
    conn.close()

    # Warm the cache while the task is still queued
    r1 = test_client.get("/api/v1/dashboard/summary")
    assert r1.status_code == 200
    assert r1.json()["scan_activity"]["running"] == 0

    # Simulate the executor's running transition
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        "UPDATE tasks SET status = 'running', started_at = '2026-05-19T10:00:01' WHERE id = ?",
        (task_id,),
    )
    conn.commit()
    conn.close()

    # Manually trigger the invalidation the executor now calls after updating to running
    from backend.secuscan.executor import executor
    asyncio.run(executor._invalidate_cached_views())

    # Dashboard must reflect the running task, not the stale cached snapshot
    r2 = test_client.get("/api/v1/dashboard/summary")
    assert r2.status_code == 200
    assert r2.json()["scan_activity"]["running"] == 1, (
        "dashboard must show running count after cache invalidation on task start"
    )


def test_dashboard_summary_degrades_cleanly_when_one_query_fails(test_client):
    """A single dashboard subquery failure must not take down the whole response."""
    async def fake_fetchall(_self, query, params=()):
        if "GROUP BY severity" in query:
            raise RuntimeError("severity aggregation failed")
        if "status = 'running'" in query:
            return [{"id": "task-running-1", "status": "running", "plugin_id": "http_inspector"}]
        if "duration_seconds" in query:
            return [{"id": "task-recent-1", "status": "completed", "plugin_id": "http_inspector"}]
        return []

    async def fake_fetchone(_self, query, params=()):
        if "COUNT(*) AS total FROM findings" in query:
            return {"total": 7}
        if "FROM tasks" in query:
            return {"total": 3, "completed": 2, "running": 1}
        return None

    with (
        patch("backend.secuscan.database.Database.fetchall", new=fake_fetchall),
        patch("backend.secuscan.database.Database.fetchone", new=fake_fetchone),
    ):
        response = test_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["total_findings"] == 7
    assert data["critical_findings"] == 0
    assert data["high_findings"] == 0
    assert data["medium_findings"] == 0
    assert data["low_findings"] == 0
    assert data["info_findings"] == 0
    assert data["recent_findings"] == []
    assert data["scan_activity"] == {"total": 3, "completed": 2, "running": 1}
    assert data["running_tasks"] == [{"id": "task-running-1", "status": "running", "plugin_id": "http_inspector"}]
    assert data["recent_tasks"] == [{"id": "task-recent-1", "status": "completed", "plugin_id": "http_inspector"}]
