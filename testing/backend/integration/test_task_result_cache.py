import sqlite3
import json
import pytest
import asyncio
from backend.secuscan.config import settings

def test_task_result_cache_hit_and_invalidation(test_client):
    """Test that requesting task results caches completed tasks, handles cache hits,
    and invalidates appropriately.
    """
    task_id = "cache-result-test-001"

    # Seed a completed task in the database
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        """
        INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, created_at,
                           preset, inputs_json, command_used, structured_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, "default", "http_inspector", "http_inspector", "https://example.com",
            "completed", "2026-05-19T10:00:00",
            "standard", json.dumps({"target": "https://example.com"}),
            "", json.dumps({
                "findings": [
                    {
                        "title": "Initial Title",
                        "category": "General",
                        "severity": "info",
                        "description": "Dummy finding"
                    }
                ]
            }),
        ),
    )
    conn.commit()
    conn.close()

    # First request: gets data from the DB, should cache it
    r1 = test_client.get(f"/api/v1/task/{task_id}/result")
    assert r1.status_code == 200
    assert r1.json()["findings"][0]["title"] == "Initial Title"

    # Modify the DB finding directly to see if the second request uses cached result
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        "UPDATE tasks SET structured_json = ? WHERE id = ?",
        (json.dumps({
            "findings": [
                {
                    "title": "Modified Title",
                    "category": "General",
                    "severity": "info",
                    "description": "Dummy finding"
                }
            ]
        }), task_id)
    )
    conn.commit()
    conn.close()

    # Second request: should hit the cache and still return "Initial Title"
    r2 = test_client.get(f"/api/v1/task/{task_id}/result")
    assert r2.status_code == 200
    assert r2.json()["findings"][0]["title"] == "Initial Title"

    # Invalidate view cache
    from backend.secuscan.routes import invalidate_view_cache
    asyncio.run(invalidate_view_cache())

    # Third request: should miss cache and fetch updated "Modified Title" from DB
    r3 = test_client.get(f"/api/v1/task/{task_id}/result")
    assert r3.status_code == 200
    assert r3.json()["findings"][0]["title"] == "Modified Title"


def test_task_result_cache_bypassed_for_unfinished_tasks(test_client):
    """Test that requesting task results does NOT cache running/queued tasks."""
    task_id = "cache-result-test-002"

    # Seed a running task in the database
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        """
        INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, created_at,
                           preset, inputs_json, command_used, structured_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, "default", "http_inspector", "http_inspector", "https://example.com",
            "running", "2026-05-19T10:00:00",
            "standard", json.dumps({"target": "https://example.com"}),
            "", json.dumps({
                "findings": [
                    {
                        "title": "Running Title",
                        "category": "General",
                        "severity": "info",
                        "description": "Dummy finding"
                    }
                ]
            }),
        ),
    )
    conn.commit()
    conn.close()

    # First request: gets data from DB
    r1 = test_client.get(f"/api/v1/task/{task_id}/result")
    assert r1.status_code == 200
    assert r1.json()["findings"][0]["title"] == "Running Title"

    # Modify the DB finding directly
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        "UPDATE tasks SET structured_json = ? WHERE id = ?",
        (json.dumps({
            "findings": [
                {
                    "title": "Updated Running Title",
                    "category": "General",
                    "severity": "info",
                    "description": "Dummy finding"
                }
            ]
        }), task_id)
    )
    conn.commit()
    conn.close()

    # Second request: since it was running, it should NOT have been cached, so we get updated data
    r2 = test_client.get(f"/api/v1/task/{task_id}/result")
    assert r2.status_code == 200
    assert r2.json()["findings"][0]["title"] == "Updated Running Title"
