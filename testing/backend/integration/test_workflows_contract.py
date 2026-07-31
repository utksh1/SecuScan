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
    payload = _workflow_payload()
    payload["schedule_timezone"] = "America/New_York"
    create_response = test_client.post("/api/v1/workflows", json=payload)
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
    assert created["schedule_timezone"] == "America/New_York"
    assert created["enabled"] is True
    assert created["steps"] == [expected_step]
    assert created["queued_task_ids"] == []
    assert "steps_json" not in created

    list_response = test_client.get("/api/v1/workflows")
    assert list_response.status_code == 200
    listed = list_response.json()
    # Find our created workflow in case multiple tests ran
    wf_item = next((w for w in listed["workflows"] if w["id"] == created["id"]), None)
    assert wf_item is not None
    assert wf_item["schedule_seconds"] == 3600
    assert wf_item["schedule_timezone"] == "America/New_York"
    assert wf_item["steps"] == created["steps"]
    assert "steps_json" not in wf_item

    update_response = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"schedule_seconds": 7200, "enabled": False, "schedule_timezone": "UTC"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == created["id"]
    assert updated["schedule_seconds"] == 7200
    assert updated["schedule_timezone"] == "UTC"
    assert updated["enabled"] is False
    assert updated["steps"] == created["steps"]

    update_response2 = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"schedule_timezone": None},
    )
    assert update_response2.status_code == 200
    updated2 = update_response2.json()
    assert updated2["schedule_timezone"] is None


def test_workflow_create_invalid_timezone(test_client):
    payload = _workflow_payload("Bad TZ Create")
    payload["schedule_timezone"] = "America/Invalid_Timezone"
    response = test_client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 400
    assert "Invalid timezone" in response.json()["detail"]

    # Test with abbreviation
    payload["schedule_timezone"] = "EST"
    response = test_client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 400
    assert "Invalid timezone" in response.json()["detail"]

    # Test with empty string
    payload["schedule_timezone"] = ""
    response = test_client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 400
    assert "must be a non-empty string" in response.json()["detail"]


def test_workflow_update_invalid_timezone(test_client):
    create_response = test_client.post("/api/v1/workflows", json=_workflow_payload("Bad TZ Update"))
    assert create_response.status_code == 200
    workflow_id = create_response.json()["id"]

    # Patch with bad IANA zone
    response = test_client.patch(f"/api/v1/workflows/{workflow_id}", json={"schedule_timezone": "Europe/Invalid"})
    assert response.status_code == 400
    assert "Invalid timezone" in response.json()["detail"]

    # Patch with offset
    response = test_client.patch(f"/api/v1/workflows/{workflow_id}", json={"schedule_timezone": "GMT+5"})
    assert response.status_code == 400
    assert "Invalid timezone" in response.json()["detail"]


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
