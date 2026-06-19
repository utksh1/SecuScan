"""
Unit tests for finding assignment functionality.
Tests the assignment of findings to team members and notification generation.
"""

import sqlite3
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import pytest
from backend.secuscan.config import settings


ALICE = {"X-User-Id": "alice"}
BOB = {"X-User-Id": "bob"}
CHARLIE = {"X-User-Id": "charlie"}

ALICE_OWNER = "user:alice"
BOB_OWNER = "user:bob"
CHARLIE_OWNER = "user:charlie"


def _seed_finding(owner_id: str, finding_id: str, task_id: str = "task-1") -> None:
    """Insert a finding directly for testing."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category,
                                  severity, target, description, remediation, assigned_to, status, visibility)
            VALUES (?, ?, ?, 'nmap', 'Open port', 'network', 'critical', '127.0.0.1', 'desc', 'fix', NULL, 'OPEN', 'PRIVATE')
            """,
            (finding_id, owner_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_finding_assignment(finding_id: str) -> dict:
    """Get the assignment info for a finding."""
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT assigned_to, assigned_by FROM findings WHERE id = ?",
            (finding_id,),
        )
        row = cur.fetchone()
        return {"assigned_to": row[0], "assigned_by": row[1]} if row else None
    finally:
        conn.close()


def _get_notification_by_action(user_id: str, finding_id: str, action_type: str) -> dict:
    """Get a notification for a specific user and finding."""
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT id, message, action_type FROM notifications WHERE user_id = ? AND finding_id = ? AND action_type = ?",
            (user_id, finding_id, action_type),
        )
        row = cur.fetchone()
        return {"id": row[0], "message": row[1], "action_type": row[2]} if row else None
    finally:
        conn.close()


def test_assignment_basic(test_client):
    """Test that a finding can be assigned to a team member."""
    finding_id = "finding-assign-1"
    _seed_finding(ALICE_OWNER, finding_id)
    
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == finding_id
    assert data["assigned_to"] == BOB_OWNER
    assert data["assigned_by"] == ALICE_OWNER


def test_assignment_updates_finding_fields(test_client):
    """Test that assignment updates the finding's assigned_to and assigned_by fields."""
    finding_id = "finding-assign-2"
    _seed_finding(ALICE_OWNER, finding_id)
    
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    
    assert resp.status_code == 200
    
    # Verify database was updated
    assignment = _get_finding_assignment(finding_id)
    assert assignment["assigned_to"] == BOB_OWNER
    assert assignment["assigned_by"] == ALICE_OWNER


def test_assignment_creates_activity(test_client):
    """Test that assignment creates an activity record."""
    finding_id = "finding-assign-3"
    _seed_finding(ALICE_OWNER, finding_id)
    
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    
    assert resp.status_code == 200
    
    # Verify activity was created
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT action, user_id FROM activities WHERE finding_id = ? AND action = ?",
            (finding_id, "finding_assigned"),
        )
        activity = cur.fetchone()
        assert activity is not None
        assert activity[1] == ALICE_OWNER
    finally:
        conn.close()


def test_assignment_notifies_assignee(test_client):
    """Test that the assignee receives a notification."""
    finding_id = "finding-assign-4"
    _seed_finding(ALICE_OWNER, finding_id)
    
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    
    assert resp.status_code == 200
    
    # Verify Bob received a notification
    resp = test_client.get(
        "/api/v1/notifications",
        headers=BOB,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notifications"]) >= 1
    
    assignment_notif = next(
        (n for n in data["notifications"] if n["action_type"] == "finding_assigned"),
        None,
    )
    assert assignment_notif is not None
    assert finding_id in assignment_notif["finding_id"] or finding_id == assignment_notif["finding_id"]


def test_assignment_not_allowed_without_ownership(test_client):
    """Test that non-owner cannot assign a finding."""
    finding_id = "finding-assign-5"
    _seed_finding(ALICE_OWNER, finding_id)
    
    # Bob tries to assign Alice's finding
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": CHARLIE_OWNER},
        headers=BOB,
    )
    
    assert resp.status_code == 403


def test_multiple_reassignments(test_client):
    """Test that a finding can be reassigned multiple times."""
    finding_id = "finding-assign-6"
    _seed_finding(ALICE_OWNER, finding_id)
    
    # First assignment: to Bob
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200
    
    # Second assignment: to Charlie
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": CHARLIE_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200
    
    # Verify final assignment
    assignment = _get_finding_assignment(finding_id)
    assert assignment["assigned_to"] == CHARLIE_OWNER
    assert assignment["assigned_by"] == ALICE_OWNER


def test_assignment_creates_two_activities_for_reassignment(test_client):
    """Test that reassignment creates a second activity record."""
    finding_id = "finding-assign-7"
    _seed_finding(ALICE_OWNER, finding_id)
    
    # First assignment
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200
    
    # Reassign
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": CHARLIE_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200
    
    # Verify two activities exist
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM activities WHERE finding_id = ? AND action = ?",
            (finding_id, "finding_assigned"),
        )
        count = cur.fetchone()[0]
        assert count == 2
    finally:
        conn.close()


def test_assignment_with_invalid_user(test_client):
    """Test that assignment with non-existent user still stores the assignment."""
    finding_id = "finding-assign-8"
    _seed_finding(ALICE_OWNER, finding_id)
    
    # Assign to a non-existent but valid-format user ID
    invalid_user = "user:nonexistent"
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": invalid_user},
        headers=ALICE,
    )
    
    # Should still succeed (we don't validate if user exists)
    assert resp.status_code == 200
    
    assignment = _get_finding_assignment(finding_id)
    assert assignment["assigned_to"] == invalid_user
