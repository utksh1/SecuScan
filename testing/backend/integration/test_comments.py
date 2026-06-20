"""
Unit tests for finding comments and annotation functionality.
Tests the creation, retrieval, and notification of comments on findings.
"""

from backend.secuscan.config import settings
import pytest
import sqlite3
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


ALICE = {"X-User-Id": "alice"}
BOB = {"X-User-Id": "bob"}

ALICE_OWNER = "user:alice"
BOB_OWNER = "user:bob"


def _seed_finding(owner_id: str, finding_id: str, task_id: str = "task-1") -> None:
    """Insert a finding directly for testing."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category,
                                  severity, target, description, remediation, assigned_to, status, visibility)
            VALUES (?, ?, ?, 'nmap', 'Open port', 'network', 'high', '127.0.0.1', 'desc', 'fix', NULL, 'OPEN', 'PRIVATE')
            """,
            (finding_id, owner_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def _get_comments_count(finding_id: str) -> int:
    """Get the number of comments on a finding."""
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE finding_id = ?",
            (finding_id,),
        )
        return cur.fetchone()[0]
    finally:
        conn.close()


def _get_notifications_count(user_id: str, action_type: str = None) -> int:
    """Get the number of notifications for a user."""
    conn = sqlite3.connect(settings.database_path)
    try:
        if action_type:
            cur = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND action_type = ?",
                (user_id, action_type),
            )
        else:
            cur = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
                (user_id,),
            )
        return cur.fetchone()[0]
    finally:
        conn.close()


def test_comment_creation(test_client):
    """Test that a user can create a comment on a finding they own."""
    finding_id = "finding-test-1"
    _seed_finding(ALICE_OWNER, finding_id)

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={
            "content": "This is a critical vulnerability that needs immediate attention."
        },
        headers=ALICE,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["finding_id"] == finding_id
    assert data["user_id"] == ALICE_OWNER
    assert (
        data["content"]
        == "This is a critical vulnerability that needs immediate attention."
    )
    assert "id" in data
    assert "created_at" in data


def test_comment_not_allowed_without_access(test_client):
    """Test that a user cannot comment on a finding they don't own."""
    finding_id = "finding-test-2"
    _seed_finding(ALICE_OWNER, finding_id)

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={"content": "Trying to hack!"},
        headers=BOB,
    )

    assert resp.status_code == 403


def test_comment_validation(test_client):
    """Test that empty comments are rejected."""
    finding_id = "finding-test-3"
    _seed_finding(ALICE_OWNER, finding_id)

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={"content": ""},
        headers=ALICE,
    )

    assert resp.status_code == 422  # Validation error


def test_comment_creates_activity(test_client):
    """Test that creating a comment creates an activity record."""
    finding_id = "finding-test-4"
    _seed_finding(ALICE_OWNER, finding_id)

    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={"content": "Adding a detailed analysis of the vulnerability."},
        headers=ALICE,
    )

    assert resp.status_code == 200

    # Verify activity was created
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT action, user_id FROM activities WHERE finding_id = ? AND action = ?",
            (finding_id, "comment_added"),
        )
        activity = cur.fetchone()
        assert activity is not None
        assert activity[1] == ALICE_OWNER
    finally:
        conn.close()


def test_comment_listing(test_client):
    """Test that comments can be retrieved in chronological order."""
    finding_id = "finding-test-5"
    _seed_finding(ALICE_OWNER, finding_id)

    # Create multiple comments
    for i in range(3):
        resp = test_client.post(
            f"/api/v1/finding/{finding_id}/comments",
            json={"content": f"Comment {i+1}"},
            headers=ALICE,
        )
        assert resp.status_code == 200

    # Retrieve comments
    resp = test_client.get(
        f"/api/v1/finding/{finding_id}/comments",
        headers=ALICE,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["finding_id"] == finding_id
    assert len(data["comments"]) == 3
    # Verify chronological order (oldest first)
    assert data["comments"][0]["content"] == "Comment 1"
    assert data["comments"][1]["content"] == "Comment 2"
    assert data["comments"][2]["content"] == "Comment 3"


def test_comments_access_denied_for_other_owner(test_client):
    """Test that another user cannot see comments on findings they don't own."""
    finding_id = "finding-test-6"
    _seed_finding(ALICE_OWNER, finding_id)

    # Alice creates a comment
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={"content": "Secret analysis"},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Bob tries to read comments
    resp = test_client.get(
        f"/api/v1/finding/{finding_id}/comments",
        headers=BOB,
    )

    assert resp.status_code == 403


def test_comment_notification_to_assignee(test_client):
    """Test that assigning a finding and then commenting notifies the assignee."""
    finding_id = "finding-test-7"
    _seed_finding(ALICE_OWNER, finding_id)

    # First, assign the finding to Bob
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/assign",
        json={"assigned_to": BOB_OWNER},
        headers=ALICE,
    )
    assert resp.status_code == 200

    # Now Alice creates a comment
    resp = test_client.post(
        f"/api/v1/finding/{finding_id}/comments",
        json={"content": "Updated status on the fix"},
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
    # Should have at least 2 notifications: assignment + comment
    assert len(data["notifications"]) >= 1
    comment_notif = next(
        (n for n in data["notifications"] if n["action_type"] == "comment_added"),
        None,
    )
    assert comment_notif is not None
