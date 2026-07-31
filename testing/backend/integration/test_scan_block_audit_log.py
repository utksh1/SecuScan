"""
Integration tests: blocked/failed scan attempts create an audit trail.

Covers the fix for the bug where scans rejected by the consent gate or
blocked by safe-mode target validation left no entry in the audit log,
making it impossible for an administrator to reconstruct misuse attempts
after the fact.
"""

import json
import asyncio

from backend.secuscan.database import get_db


async def get_audit_entries(event_type: str, plugin_id: str):
    db = await get_db()
    return await db.fetchall(
        "SELECT event_type, message, severity, context_json, plugin_id "
        "FROM audit_log WHERE event_type = ? AND plugin_id = ?",
        (event_type, plugin_id),
    )


def test_consent_rejection_creates_audit_entry(test_client):
    """A scan blocked by the consent gate must leave an audit trail."""
    response = test_client.post(
        "/api/v1/task/start",
        json={
            "plugin_id": "amass",
            "inputs": {"target": "192.168.1.1"},
            "consent_granted": False,
        },
    )
    assert response.status_code == 400

    entries = asyncio.run(get_audit_entries("scan_blocked_consent", "amass"))
    assert len(entries) == 1
    entry = entries[0]
    assert entry["severity"] == "warning"
    assert entry["plugin_id"] == "amass"

    ctx = json.loads(entry["context_json"])
    assert ctx["plugin_id"] == "amass"


def test_safe_mode_target_validation_creates_audit_entry(test_client):
    """A scan blocked by safe-mode target validation must leave an audit trail."""
    response = test_client.post(
        "/api/v1/task/start",
        json={
            "plugin_id": "amass",
            "inputs": {"target": "8.8.8.8"},
            "consent_granted": True,
        },
    )
    assert response.status_code == 400

    entries = asyncio.run(get_audit_entries("scan_blocked_target_validation", "amass"))
    assert len(entries) == 1
    entry = entries[0]
    assert entry["severity"] == "warning"
    assert entry["plugin_id"] == "amass"

    ctx = json.loads(entry["context_json"])
    assert ctx["plugin_id"] == "amass"
    assert ctx["target"] == "8.8.8.8"
    assert ctx["safe_mode"] is True
    assert "reason" in ctx


def test_successful_task_start_does_not_create_blocked_audit_entries(test_client):
    """A scan that starts successfully must not create either blocked-attempt entry."""
    response = test_client.post(
        "/api/v1/task/start",
        json={
            "plugin_id": "amass",
            "inputs": {"target": "192.168.1.1"},
            "consent_granted": True,
        },
    )
    assert response.status_code == 200

    consent_entries = asyncio.run(get_audit_entries("scan_blocked_consent", "amass"))
    target_entries = asyncio.run(get_audit_entries("scan_blocked_target_validation", "amass"))
    assert len(consent_entries) == 0
    assert len(target_entries) == 0
