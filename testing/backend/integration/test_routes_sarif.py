import json
import asyncio
from unittest.mock import patch

import pytest
from backend.secuscan.database import get_db

async def insert_mock_completed_task(task_id: str):
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
            "https://example.com",
            "completed",
            "2026-05-14T10:30:00",
            "standard",
            '{"target": "https://example.com"}',
            "nikto -h https://example.com",
            json.dumps({
                "findings": [
                    {
                        "title": "Exposed admin panel",
                        "category": "Exposure",
                        "severity": "HIGH",
                        "target": "src/admin.py:45",
                        "description": "Admin panel is reachable.",
                        "remediation": "Restrict access.",
                        "cve": "CVE-2026-0001"
                    }
                ]
            })
        )
    )

async def insert_mock_failed_task(task_id: str):
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
            "https://example.com",
            "failed",
            "2026-05-14T10:30:00",
            "standard",
            '{"target": "https://example.com"}',
            "nikto -h https://example.com",
            json.dumps({"findings": []})
        )
    )

def test_download_sarif_report_success(test_client):
    task_id = "test-task-completed-123"

    # Pre-populate database with a completed task
    asyncio.run(insert_mock_completed_task(task_id))

    # Request the SARIF report
    response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sarif+json"

    # Verify Content-Disposition header
    assert "attachment" in response.headers["content-disposition"]
    assert "filename=" in response.headers["content-disposition"]
    assert "secuscan_http-inspector_example-com_" in response.headers["content-disposition"]
    assert ".sarif" in response.headers["content-disposition"]

    # Verify SARIF payload
    sarif = response.json()
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "http_inspector"

    driver = sarif["runs"][0]["tool"]["driver"]
    assert driver["properties"]["generatorVersion"]

    run_properties = sarif["runs"][0]["properties"]
    assert run_properties["pluginId"] == "http_inspector"
    assert run_properties["exportTimestamp"]

    results = sarif["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "cve-2026-0001"
    assert results[0]["level"] == "error"

def test_download_sarif_report_not_found(test_client):
    response = test_client.get("/api/v1/task/non-existent-task-id/report/sarif")
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]

def test_download_sarif_report_not_finished(test_client):
    # If the task is queued/running, we expect 400 Bad Request
    task_id = "test-task-running-123"

    async def insert_running_task():
        db = await get_db()
        await db.execute(
            """
            INSERT INTO tasks (id, plugin_id, tool_name, target, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, "http_inspector", "http_inspector", "https://example.com", "running", "2026-05-14T10:30:00")
        )

    asyncio.run(insert_running_task())

    response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")
    assert response.status_code == 400
    assert "Task is not finished yet" in response.json()["detail"]

def test_download_sarif_report_failed_task(test_client):
    task_id = "test-task-failed-123"

    asyncio.run(insert_mock_failed_task(task_id))

    # Requesting report for failed task is allowed (returns 200 with empty findings or partial data)
    response = test_client.get(f"/api/v1/task/{task_id}/report/sarif")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sarif+json"
    sarif = response.json()
    assert len(sarif["runs"][0]["results"]) == 0


@pytest.mark.parametrize(
    "report_format, patch_target",
    [
        ("csv", "backend.secuscan.routes.reporting.generate_csv_report"),
        ("html", "backend.secuscan.routes.reporting.generate_html_report"),
        ("pdf", "backend.secuscan.routes.reporting.generate_pdf_report"),
        ("sarif", "backend.secuscan.routes.reporting.generate_sarif_report"),
    ],
)
def test_download_report_generation_failure_returns_structured_error(test_client, report_format, patch_target):
    task_id = f"test-task-report-fail-{report_format}"
    asyncio.run(insert_mock_completed_task(task_id))

    with patch(patch_target, side_effect=RuntimeError("boom internal trace")):
        response = test_client.get(f"/api/v1/task/{task_id}/report/{report_format}")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "report_generation_failed"
    assert body["message"] == f"Failed to generate {report_format.upper()} report"
    assert body["details"]["task_id"] == task_id
    assert body["details"]["format"] == report_format
    assert "boom internal trace" not in json.dumps(body)
