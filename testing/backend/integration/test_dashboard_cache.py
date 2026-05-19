from unittest.mock import AsyncMock, patch


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
