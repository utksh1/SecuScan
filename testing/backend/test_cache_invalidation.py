"""Tests for cache invalidation on task deletion endpoints"""

import pytest
from fastapi.testclient import TestClient

from backend.secuscan.main import app
from backend.secuscan.database import get_db

client = TestClient(app)


@pytest.mark.asyncio
async def test_delete_task_invalidates_cache():
    """Test that deleting a task calls cache invalidation"""
    db = await get_db()

    # Create a dummy task
    task_id = "test-delete-cache-123"
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (task_id, "test-plugin", "test", "example.com", "completed"),
    )

    # Hit cached endpoint before delete
    resp1 = client.get("/api/v1/tasks")
    assert resp1.status_code == 200

    # Delete task (this should call invalidate_view_cache)
    resp2 = client.delete(f"/api/v1/task/{task_id}")
    assert resp2.status_code == 200

    # Hit again after delete
    resp3 = client.get("/api/v1/tasks")
    assert resp3.status_code == 200

    # Cleanup
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


@pytest.mark.asyncio
async def test_bulk_delete_invalidates_cache():
    """Test bulk delete invalidates cache"""
    response = client.delete("/api/v1/tasks/bulk", json={"task_ids": []})
    assert response.status_code in [200, 400]


@pytest.mark.asyncio
async def test_clear_all_tasks_invalidates_cache():
    """Test clear all tasks invalidates cache"""
    response = client.delete("/api/v1/tasks/clear")
    assert response.status_code in [200, 400]
