"""API contract tests for cron-based workflow schedules."""


def _workflow_payload(name: str = "Cron Nightly"):
    return {
        "name": name,
        "cron_expression": "0 2 * * *",
        "timezone": "UTC",
        "blackout_start": "22:00",
        "blackout_end": "06:00",
        "enabled": True,
        "steps": [{"plugin_id": "http_inspector", "inputs": {"url": "http://127.0.0.1:8000"}}],
    }


def test_cron_workflow_create_list_update_contract(test_client):
    create_response = test_client.post("/api/v1/workflows", json=_workflow_payload())
    assert create_response.status_code == 200
    created = create_response.json()

    assert created["cron_expression"] == "0 2 * * *"
    assert created["timezone"] == "UTC"
    assert created["blackout_start"] == "22:00"
    assert created["blackout_end"] == "06:00"
    assert created["schedule_seconds"] is None

    list_response = test_client.get("/api/v1/workflows")
    assert list_response.status_code == 200
    listed = list_response.json()["workflows"][0]
    assert listed["cron_expression"] == "0 2 * * *"

    update_response = test_client.patch(
        f"/api/v1/workflows/{created['id']}",
        json={"cron_expression": "0 3 * * *", "enabled": False},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["cron_expression"] == "0 3 * * *"
    assert updated["enabled"] is False


def test_workflow_rejects_both_interval_and_cron(test_client):
    payload = _workflow_payload("Invalid")
    payload["schedule_seconds"] = 3600
    response = test_client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 400
    assert "not both" in response.json()["detail"].lower()
