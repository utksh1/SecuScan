from unittest.mock import AsyncMock, patch
from backend.secuscan.database import get_db
import asyncio
import json

def _workflow_payload(name: str = "Nightly Scan"):
    return {
        "name": name,
        "schedule_seconds": 3600,
        "enabled": True,
        "steps": [{"plugin_id": "http_inspector", "inputs": {"url": "http://127.0.0.1:8000"}}],
    }

def test_workflow_disable_creates_audit_log(test_client):
    create_response = test_client.post(
        "/api/v1/workflows",
        json=_workflow_payload(),
    )

    workflow_id = create_response.json()["id"]

    update_response = test_client.patch(
        f"/api/v1/workflows/{workflow_id}",
        json={"enabled": False},
    )

    assert update_response.status_code == 200

    async def get_audit():
        db = await get_db()
        return await db.fetchone(
            """
            SELECT *
            FROM audit_log
            WHERE event_type = 'workflow_disabled'
            ORDER BY id DESC
            LIMIT 1
            """
        )

    audit = asyncio.run(get_audit())

    assert audit is not None

    context = json.loads(audit["context_json"])

    assert context["workflow_id"] == workflow_id
    assert context["previous_state"] is True
    assert context["new_state"] is False
    assert context["actor"] is not None
    assert audit["timestamp"] is not None

def test_workflow_enable_creates_audit_log(test_client):
    payload = _workflow_payload()
    payload["enabled"] = False

    create_response = test_client.post(
        "/api/v1/workflows",
        json=payload,
    )

    workflow_id = create_response.json()["id"]

    update_response = test_client.patch(
        f"/api/v1/workflows/{workflow_id}",
        json={"enabled": True},
    )

    assert update_response.status_code == 200

    async def get_audit():
        db = await get_db()
        return await db.fetchone(
            """
            SELECT *
            FROM audit_log
            WHERE event_type = 'workflow_enabled'
            ORDER BY id DESC
            LIMIT 1
            """
        )

    audit = asyncio.run(get_audit())

    assert audit is not None

    context = json.loads(audit["context_json"])

    assert context["workflow_id"] == workflow_id
    assert context["previous_state"] is False
    assert context["new_state"] is True
    assert context["actor"] is not None
    assert audit["timestamp"] is not None

def test_workflow_create_list_update_contract(test_client):
    create_response = test_client.post("/api/v1/workflows", json=_workflow_payload())
    assert create_response.status_code == 200
    created = create_response.json()
    expected_step = {
        "plugin_id": "http_inspector",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "preset": None,
        "execution_context": {
            "target_policy_id": None,
            "scan_profile": "standard",
            "credential_profile_id": None,
            "session_profile_id": None,
            "validation_mode": "proof",
            "evidence_level": "standard",
        },
    }

    assert created["id"]
    assert created["name"] == "Nightly Scan"
    assert created["schedule_seconds"] == 3600
    assert created["enabled"] is True
    assert created["steps"] == [expected_step]
    assert created["queued_task_ids"] == []
    assert "steps_json" not in created

    list_response = test_client.get("/api/v1/workflows")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["workflows"][0]["id"] == created["id"]
    assert listed["workflows"][0]["schedule_seconds"] == 3600
    assert listed["workflows"][0]["steps"] == created["steps"]
    assert "steps_json" not in listed["workflows"][0]

    update_response = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"schedule_seconds": 7200, "enabled": False},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["schedule_seconds"] == 7200
    assert updated["enabled"] is False
    assert updated["steps"] == created["steps"]


def test_workflow_run_uses_queued_task_ids_contract(test_client):
    create_response = test_client.post("/api/v1/workflows", json=_workflow_payload("Run Contract"))
    workflow_id = create_response.json()["id"]

    with (
        patch("backend.secuscan.routes.executor.create_task", new=AsyncMock(return_value="task-001")),
        patch("backend.secuscan.routes.executor.execute_task", new=AsyncMock()),
    ):
        run_response = test_client.post(f"/api/v1/workflows/{workflow_id}/run")

    assert run_response.status_code == 200
    data = run_response.json()
    assert data["workflow_id"] == workflow_id
    assert data["queued_task_ids"] == ["task-001"]
