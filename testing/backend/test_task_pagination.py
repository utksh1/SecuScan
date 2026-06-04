"""
Tests for pagination metadata in tasks list endpoint.
"""

import asyncio

import pytest
from backend.secuscan.database import get_db


async def _insert_task(task_id, plugin_id, status, created_at):
    db = await get_db()
    await db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, status, created_at, inputs_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            plugin_id,
            "Test Scanner",
            "example.com",
            status,
            created_at,
            "{}",
        ),
    )


class TestTasksPagination:
    """Test pagination metadata for /api/v1/tasks endpoint"""

    def test_pagination_has_next_previous_fields(self, test_client):
        """Test that next and previous fields exist in response"""
        response = test_client.get("/api/v1/tasks")

        if response.status_code == 200:
            data = response.json()
            assert "pagination" in data
            pagination = data["pagination"]

            assert "next" in pagination
            assert "previous" in pagination
            assert "page" in pagination
            assert "per_page" in pagination
            assert "total_items" in pagination
            assert "total_pages" in pagination
        else:
            pytest.fail(f"API returned {response.status_code}")

    def test_default_pagination_values(self, test_client):
        """Test default page=1, per_page=25"""
        response = test_client.get("/api/v1/tasks")
        assert response.status_code == 200

        pagination = response.json()["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 25

    def test_custom_per_page(self, test_client):
        """Test that per_page parameter is respected"""
        response = test_client.get("/api/v1/tasks?page=1&per_page=10")
        assert response.status_code == 200

        pagination = response.json()["pagination"]
        assert pagination["per_page"] == 10

    @pytest.mark.parametrize(
        "qs",
        [
            "page=0",
            "page=-1",
            "per_page=0",
            "per_page=-5",
            "per_page=101",
        ],
    )
    def test_invalid_pagination_is_rejected(self, test_client, qs):
        response = test_client.get(f"/api/v1/tasks?{qs}")
        assert response.status_code == 422

    def test_status_filter_valid(self, test_client):
        response = test_client.get("/api/v1/tasks?status=completed")
        assert response.status_code == 200

        data = response.json()
        assert "tasks" in data
        assert all(task["status"] == "completed" for task in data["tasks"])

    def test_status_filter_invalid(self, test_client):
        response = test_client.get("/api/v1/tasks?status=invalid-status")
        assert response.status_code == 400

        data = response.json()
        assert data["detail"] == (
            "Invalid task status 'invalid-status'. Allowed values: queued, running, completed, failed, cancelled"
        )

    def test_first_page_previous_is_null(self, test_client):
        """Test that previous is None on first page"""
        response = test_client.get("/api/v1/tasks?page=1&per_page=10")
        assert response.status_code == 200

        pagination = response.json()["pagination"]
        assert pagination["previous"] is None

    def test_next_url_preserves_filters(self, test_client):
        """Test that next URL keeps filter parameters"""
        response = test_client.get(
            "/api/v1/tasks?page=1&per_page=5&status=completed&plugin_id=nmap"
        )
        assert response.status_code == 200

        data = response.json()
        next_url = data["pagination"]["next"]

        if next_url:
            assert "per_page=5" in next_url
            assert "status=completed" in next_url
            assert "plugin_id=nmap" in next_url

    def test_next_url_encodes_filtered_pagination_params(self, test_client):
        """Test that filtered pagination links URL-encode query values."""
        plugin_id = "web scanner/alpha"
        status = "queued & reviewed"
        asyncio.run(
            _insert_task("encoded-filter-1", plugin_id, status, "2026-06-02T10:00:00")
        )
        asyncio.run(
            _insert_task("encoded-filter-2", plugin_id, status, "2026-06-02T09:00:00")
        )

        response = test_client.get(
            "/api/v1/tasks",
            params={
                "page": 1,
                "per_page": 1,
                "plugin_id": plugin_id,
                "status": status,
            },
        )
        assert response.status_code == 200

        next_url = response.json()["pagination"]["next"]
        assert next_url == (
            "/api/v1/tasks?page=2&per_page=1&"
            "plugin_id=web+scanner%2Falpha&status=queued+%26+reviewed"
        )
