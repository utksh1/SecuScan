"""
Integration tests: audit log entries are created on successful report downloads
and are NOT created on 404 or 400 error responses.
"""

import json
import asyncio

import pytest
from backend.secuscan.database import get_db


async def insert_completed_task(task_id: str):
    db = await get_db()
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            "http_inspector",
            "http_inspector",
            "https://audit-test.example.com",
            "completed",
            "2026-05-14T10:30:00",
            "standard",
            '{"target": "https://audit-test.example.com"}',
            "nikto -h https://audit-test.example.com",
            json.dumps({"findings": [{"title": "Finding", "severity": "HIGH", "description": "Test"}]}),
        ),
    )


async def insert_running_task(task_id: str):
    db = await get_db()
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task_id, "http_inspector", "http_inspector", "https://audit-test.example.com", "running", "2026-05-14T10:30:00"),
    )


async def get_audit_entries(task_id: str):
    db = await get_db()
    return await db.fetchall(
        "SELECT event_type, message, severity, context_json, task_id, plugin_id FROM audit_log WHERE task_id = ? AND event_type = 'report_downloaded'",
        (task_id,),
    )


@pytest.mark.parametrize("report_format", ["csv", "html", "sarif"])
def test_successful_download_creates_audit_entry(test_client, report_format):
    task_id = f"audit-ok-{report_format}"
    asyncio.run(insert_completed_task(task_id))

    response = test_client.get(f"/api/v1/task/{task_id}/report/{report_format}")
    assert response.status_code == 200

    entries = asyncio.run(get_audit_entries(task_id))
    assert len(entries) == 1
    entry = entries[0]
    assert entry["event_type"] == "report_downloaded"
    assert entry["task_id"] == task_id
    assert entry["plugin_id"] == "http_inspector"
    assert entry["severity"] == "info"

    ctx = json.loads(entry["context_json"])
    assert ctx["format"] == report_format
    assert ctx["task_id"] == task_id
    assert ctx["plugin_id"] == "http_inspector"


def test_pdf_successful_download_creates_audit_entry(test_client):
    task_id = "audit-ok-pdf"
    asyncio.run(insert_completed_task(task_id))

    response = test_client.get(f"/api/v1/task/{task_id}/report/pdf")
    assert response.status_code == 200

    entries = asyncio.run(get_audit_entries(task_id))
    assert len(entries) == 1
    ctx = json.loads(entries[0]["context_json"])
    assert ctx["format"] == "pdf"


def test_404_does_not_create_audit_entry(test_client):
    task_id = "audit-nonexistent-task"

    response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")
    assert response.status_code == 404

    entries = asyncio.run(get_audit_entries(task_id))
    assert len(entries) == 0


def test_unfinished_task_does_not_create_audit_entry(test_client):
    task_id = "audit-running-task"
    asyncio.run(insert_running_task(task_id))

    response = test_client.get(f"/api/v1/task/{task_id}/report/csv")
    assert response.status_code == 400

    entries = asyncio.run(get_audit_entries(task_id))
    assert len(entries) == 0


def test_generation_failure_does_not_create_audit_entry(test_client):
    from unittest.mock import patch

    task_id = "audit-gen-fail"
    asyncio.run(insert_completed_task(task_id))

    with patch("backend.secuscan.routes.reporting.generate_sarif_report", side_effect=RuntimeError("boom")):
        response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")

    assert response.status_code == 500
    entries = asyncio.run(get_audit_entries(task_id))
    assert len(entries) == 0

def test_request_id_is_saved_in_audit_context(test_client):
    task_id = "audit-request-id"
    asyncio.run(insert_completed_task(task_id))

    request_id = "test-request-123"

    response = test_client.get(
        f"/api/v1/task/{task_id}/report/csv",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200

    entries = asyncio.run(get_audit_entries(task_id))
    assert len(entries) == 1

    ctx = json.loads(entries[0]["context_json"])

    assert ctx["request_id"] == request_id
