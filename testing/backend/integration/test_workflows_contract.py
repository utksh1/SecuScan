from unittest.mock import AsyncMock, patch


def _workflow_payload(name: str = "Nightly Scan"):
    return {
        "name": name,
        "schedule_seconds": 3600,
        "enabled": True,
        "steps": [{"plugin_id": "http_inspector", "inputs": {"url": "http://127.0.0.1:8000"}}],
    }


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
    assert created.get("schedule_timezone") is None
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
    assert listed["workflows"][0].get("schedule_timezone") is None
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
    assert updated.get("schedule_timezone") is None
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


def test_workflow_timezone_validation_contract(test_client):
    # Invalid timezone on create
    bad_payload = _workflow_payload("Bad Timezone Workflow")
    bad_payload["schedule_timezone"] = "Invalid_Timezone"
    res1 = test_client.post("/api/v1/workflows", json=bad_payload)
    assert res1.status_code == 400
    assert "Invalid timezone" in res1.json()["detail"]

    # Valid timezone on create
    good_payload = _workflow_payload("Good Timezone Workflow")
    good_payload["schedule_timezone"] = "America/New_York"
    res2 = test_client.post("/api/v1/workflows", json=good_payload)
    assert res2.status_code == 200
    created = res2.json()
    assert created["schedule_timezone"] == "America/New_York"

    # Invalid timezone on update
    res3 = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"schedule_timezone": "GMT+5"}
    )
    assert res3.status_code == 400
    assert "Invalid timezone" in res3.json()["detail"]

    # Valid timezone on update
    res4 = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"schedule_timezone": "Europe/London"}
    )
    assert res4.status_code == 200
    updated = res4.json()
    assert updated["schedule_timezone"] == "Europe/London"

    # None is accepted on update
    res5 = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"schedule_timezone": None}
    )
    assert res5.status_code == 200
    assert res5.json().get("schedule_timezone") is None
