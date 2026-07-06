"""
Integration tests for #1623: scan attempts blocked before execution (missing
consent, unknown plugin, invalid preset, unauthorised policy configuration,
invalid input, safe-mode target rejection, rate limiting) must leave an
audit log entry, not silently disappear.
"""

import asyncio

from backend.secuscan.database import get_db


async def get_audit_entries(event_type: str):
    db = await get_db()
    return await db.fetchall(
        "SELECT event_type, message, severity, context_json, plugin_id FROM audit_log WHERE event_type = ?",
        (event_type,),
    )


def test_missing_consent_is_logged(test_client):
    payload = {
        "plugin_id": "http_inspector",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": False,
    }

    response = test_client.post("/api/v1/task/start", json=payload)
    assert response.status_code == 400

    entries = asyncio.run(get_audit_entries("task_blocked_consent"))
    assert len(entries) >= 1
    latest = entries[-1]
    assert latest["severity"] == "warning"
    assert latest["plugin_id"] == "http_inspector"


def test_unknown_plugin_is_logged(test_client):
    payload = {
        "plugin_id": "this-plugin-does-not-exist",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }

    response = test_client.post("/api/v1/task/start", json=payload)
    assert response.status_code == 404

    entries = asyncio.run(get_audit_entries("task_blocked_plugin_not_found"))
    assert len(entries) >= 1
    assert entries[-1]["plugin_id"] == "this-plugin-does-not-exist"


def test_invalid_preset_is_logged(test_client):
    payload = {
        "plugin_id": "http_inspector",
        "preset": "definitely-not-a-real-preset",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }

    response = test_client.post("/api/v1/task/start", json=payload)
    assert response.status_code == 400

    entries = asyncio.run(get_audit_entries("task_blocked_invalid_preset"))
    assert len(entries) >= 1


def test_safe_mode_target_rejection_is_logged(test_client):
    # A public, non-loopback target is rejected in safe mode (the default),
    # since no target policy grants allow_public_targets. start_task's
    # safe-mode check currently keys specifically on the "target" input
    # field (see the separately-flagged follow-up about plugins whose field
    # is named "url"/"host"/"domain" instead), so it's included alongside
    # the plugin's own declared "url" field to exercise that path here.
    payload = {
        "plugin_id": "http_inspector",
        "preset": "quick",
        "inputs": {"url": "http://8.8.8.8", "target": "8.8.8.8"},
        "consent_granted": True,
    }

    response = test_client.post("/api/v1/task/start", json=payload)
    assert response.status_code == 400

    entries = asyncio.run(get_audit_entries("task_blocked_safe_mode"))
    assert len(entries) >= 1
    context = entries[-1]["context_json"]
    assert "8.8.8.8" in context


def test_successful_task_creation_is_still_logged_as_before(test_client):
    # Guards against a regression where instrumenting the rejection paths
    # accidentally breaks (or duplicates) the existing "task_created" audit
    # entry for the success path.
    from unittest.mock import patch

    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = ("Mocked successful output", 0)

        payload = {
            "plugin_id": "http_inspector",
            "preset": "quick",
            "inputs": {"url": "http://127.0.0.1:8000"},
            "consent_granted": True,
        }

        response = test_client.post("/api/v1/task/start", json=payload)
        assert response.status_code == 200
        task_id = response.json()["task_id"]

    db = asyncio.run(get_db())
    entries = asyncio.run(
        db.fetchall(
            "SELECT event_type FROM audit_log WHERE task_id = ? AND event_type = 'task_created'",
            (task_id,),
        )
    )
    assert len(entries) == 1
