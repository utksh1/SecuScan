import pytest
import base64
from datetime import datetime, timezone
from backend.secuscan.database import get_db

pytestmark = pytest.mark.asyncio

async def insert_finding(db, id_str, discovered_at):
    await db.execute(
        "INSERT INTO findings (id, task_id, plugin_id, title, category, severity, target, description, discovered_at, metadata_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (id_str, "t1", "p1", f"Finding {id_str}", "Test", "high", "example.com", "desc", discovered_at, "{}")
    )

async def test_findings_cursor_pagination(test_client):
    db = await get_db()
    
    # Insert some dummy findings
    # Oldest to newest
    await insert_finding(db, "f1", "2026-05-25T10:00:00Z")
    await insert_finding(db, "f2", "2026-05-25T11:00:00Z")
    await insert_finding(db, "f3", "2026-05-25T12:00:00Z")
    await insert_finding(db, "f4", "2026-05-25T12:00:00Z")  # Same timestamp to test tie-breaking
    await insert_finding(db, "f5", "2026-05-25T13:00:00Z")

    # Fetch page 1 (limit 2)
    response = test_client.get("/api/v1/findings?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["findings"]) == 2
    
    # Should be newest first (f5, then f4)
    assert data["findings"][0]["id"] == "f5"
    assert data["findings"][1]["id"] == "f4"
    assert data["pagination"]["has_more"] is True
    assert data["pagination"]["total_count"] >= 5
    
    next_cursor = data["pagination"]["next_cursor"]
    assert next_cursor is not None
    
    # Fetch page 2 (limit 2)
    response = test_client.get(f"/api/v1/findings?limit=2&cursor={next_cursor}")
    assert response.status_code == 200
    data2 = response.json()
    assert len(data2["findings"]) == 2
    
    # Should be f3, then f2
    assert data2["findings"][0]["id"] == "f3"
    assert data2["findings"][1]["id"] == "f2"
    assert data2["pagination"]["has_more"] is True
    
    next_cursor = data2["pagination"]["next_cursor"]
    
    # Fetch page 3
    response = test_client.get(f"/api/v1/findings?limit=2&cursor={next_cursor}")
    assert response.status_code == 200
    data3 = response.json()
    # At least f1
    assert data3["findings"][0]["id"] == "f1"
    
    # Test invalid cursor
    response = test_client.get("/api/v1/findings?cursor=invalid_base64_!")
    assert response.status_code == 400
