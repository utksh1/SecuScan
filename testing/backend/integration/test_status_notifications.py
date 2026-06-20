"""
Unit tests for finding status updates and notification system.
Tests status workflow (OPEN -> IN_PROGRESS -> RESOLVED) and notification generation.
"""

from backend.secuscan.config import settings
import pytest
import sqlite3
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


ALICE = {"X-User-Id": "alice"}
BOB = {"X-User-Id": "bob"}

ALICE_OWNER = "user:alice"
BOB_OWNER = "user:bob"


def _seed_finding(owner_id: str, finding_id: str, task_id: str = "task-1", status: str = "OPEN") -> None:
    """Insert a finding directly for testing."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category,
                                  severity, target, description, remediation, assigned_to, status, visibility)
            VALUES (?, ?, ?, 'nmap', 'Open port', 'network', 'high', '127.0.0.1', 'desc', 'fix', ?, ?, 'PRIVATE')
            """,
            (finding_id, owner_id, task_id, None, status),
        )
        conn.commit()
    finally:
        conn.close()


def _get_finding_status(finding_id: str) -> str:
    """Get the current status of a finding."""
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT status FROM findings WHERE id = ?",
            (finding_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _get_activities_for_finding(finding_id: str, action: str = None) -> list:
    """Get activities for a finding, optionally filtered by action."""
    conn = sqlite3.connect(settings.database_path)
    try:
        if action:
            cur = conn.execute(
                "SELECT action, user_id FROM activities WHERE finding_id = ? AND action = ?",
                (finding_id, action),
            )
        else:
            cur = conn.execute(
                "SELECT action, user_id FROM activities WHERE finding_id = ?",
                (finding_id,),
            )
        return [{"action": row[0], "user_id": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


def test_status_update_open_to_in_progress(test_client):
    """Test updating a finding status from OPEN to IN_PROGRESS."""
    finding_id = "finding-status-1"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ALICE,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == finding_id
    assert data["old_status"] == "OPEN"
    assert data["new_status"] == "IN_PROGRESS"


def test_status_update_to_resolved(test_client):
    """Test updating a finding status to RESOLVED."""
    finding_id = "finding-status-2"
    _seed_finding(ALICE_OWNER, finding_id, status="IN_PROGRESS")

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "RESOLVED"},
        headers=ALICE,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["new_status"] == "RESOLVED"

    # Verify database update
    status = _get_finding_status(finding_id)
    assert status == "RESOLVED"


def test_status_update_creates_activity(test_client):
    """Test that status updates create activity records."""
    finding_id = "finding-status-3"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ALICE,
    )

    assert resp.status_code == 200

    # Verify activity was created
    activities = _get_activities_for_finding(finding_id, "status_changed")
    assert len(activities) == 1
    assert activities[0]["user_id"] == ALICE_OWNER


def test_status_update_not_allowed_without_ownership(test_client):
    """Test that non-owner cannot change finding status."""
    finding_id = "finding-status-4"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=BOB,
    )

    assert resp.status_code == 403

    # Verify status wasn't changed
    status = _get_finding_status(finding_id)
    assert status == "OPEN"


def test_status_transitions_multiple_times(test_client):
    """Test that a finding can transition through multiple statuses."""
    finding_id = "finding-status-5"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    # OPEN -> IN_PROGRESS
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ALICE,
    )
    assert resp.status_code == 200
    assert _get_finding_status(finding_id) == "IN_PROGRESS"

    # IN_PROGRESS -> RESOLVED
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "RESOLVED"},
        headers=ALICE,
    )
    assert resp.status_code == 200
    assert _get_finding_status(finding_id) == "RESOLVED"

    # RESOLVED -> OPEN (reopening)
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "OPEN"},
        headers=ALICE,
    )
    assert resp.status_code == 200
    assert _get_finding_status(finding_id) == "OPEN"


def test_status_update_notifies_assignee(test_client):
    """Test that status updates notify the assigned team member."""
    finding_id = "finding-status-6"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    # First assign to Bob
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Now update status
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Verify Bob received a notification about status change
    resp = test_client.get(
        "/api/v1/notifications",
        headers=BOB,
    )
    assert resp.status_code == 200
    data = resp.json()

    status_notif = next(
        (n for n in data["notifications"]
         if n["action_type"] == "status_changed"),
        None,
    )
    assert status_notif is not None


def test_multiple_status_changes_create_multiple_activities(test_client):
    """Test that each status change creates a separate activity record."""
    finding_id = "finding-status-7"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    # First change
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Second change
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "RESOLVED"},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Verify two activities exist
    activities = _get_activities_for_finding(finding_id, "status_changed")
    assert len(activities) == 2


def test_notification_mark_read(test_client):
    """Test that notifications can be marked as read."""
    finding_id = "finding-status-8"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    # Assign to Bob to generate notification
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Get unread notifications for Bob
    resp = test_client.get(
        "/api/v1/notifications?is_read=false",
        headers=BOB,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notifications"]) > 0

    notif_id = data["notifications"][0]["id"]
    assert not data["notifications"][0]["is_read"]

    # Mark as read
    resp = test_client.post(
        f"/api/v1/notification/{notif_id}/mark-read",
        headers=BOB,
    )
    assert resp.status_code == 200

    # Verify it's marked as read
    resp = test_client.get(
        f"/api/v1/notifications?is_read=true",
        headers=BOB,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert any(n["id"] == notif_id and n["is_read"]
               for n in data["notifications"])


def test_activity_feed_retrieval(test_client):
    """Test that activity feed can be retrieved in reverse chronological order."""
    finding_id = "finding-status-9"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    # Create several activities
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ALICE,
    )
    assert resp.status_code == 200

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={"content": "Working on fix"},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Retrieve activity feed
    resp = test_client.get(
        f"/api/v1/finding/{finding_id}/activity",
        headers=ALICE,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["finding_id"] == finding_id
    assert len(data["activities"]) >= 2

    # Verify ordering (most recent first)
    actions = [a["action"] for a in data["activities"]]
    assert actions[0] == "comment_added"  # Most recent
    assert actions[1] == "status_changed"  # Earlier


def test_notification_filters_by_read_status(test_client):
    """Test that notifications can be filtered by read status."""
    finding_id = "finding-status-10"
    _seed_finding(ALICE_OWNER, finding_id, status="OPEN")

    # Create multiple notifications
    for i in range(2):
        resp = test_client.post(
            f"/api/v1/finding/{finding_id}/assign",
            json={"assigned_to": BOB_OWNER},
            headers=ALICE,
        )
        assert resp.status_code == 200

    # Get all unread notifications
    resp = test_client.get(
        "/api/v1/notifications?is_read=false",
        headers=BOB,
    )
    assert resp.status_code == 200
    data = resp.json()
    unread_count = len(data["notifications"])
    assert unread_count > 0

    # Mark first as read
    resp = test_client.post(
        f"/api/v1/notification/{data['notifications'][0]['id']}/mark-read",
        headers=BOB,
    )
    assert resp.status_code == 200

    # Get unread again
    resp = test_client.get(
        "/api/v1/notifications?is_read=false",
        headers=BOB,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notifications"]) == unread_count - 1
