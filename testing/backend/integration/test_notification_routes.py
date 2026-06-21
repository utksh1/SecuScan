import uuid

from backend.secuscan.models import NotificationDeliveryStatus


def _rule_payload(
    name: str = "Critical alerts",
    severity_threshold: str = "critical",
    channel_type: str = "webhook",
    target_url_or_email: str = "https://example.com/hook",
    is_active: bool = True,
):
    return {
        "name": name,
        "severity_threshold": severity_threshold,
        "channel_type": channel_type,
        "target_url_or_email": target_url_or_email,
        "is_active": is_active,
    }


def test_notification_rule_crud_contract(test_client):
    create_response = test_client.post(
        "/api/v1/notifications/rules",
        json=_rule_payload(),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["id"]
    assert created["name"] == "Critical alerts"
    assert created["severity_threshold"] == "critical"
    assert created["channel_type"] == "webhook"
    assert created["target_url_or_email"] == "https://example.com/hook"
    assert created["is_active"] is True
    assert created["created_at"]
    assert created["updated_at"]

    list_response = test_client.get("/api/v1/notifications/rules")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["rules"][0]["id"] == created["id"]

    get_response = test_client.get(f"/api/v1/notifications/rules/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]

    update_response = test_client.patch(
        f"/api/v1/notifications/rules/{created['id']}",
        json={"severity_threshold": "high", "is_active": False},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["severity_threshold"] == "high"
    assert updated["is_active"] is False

    delete_response = test_client.delete(
        f"/api/v1/notifications/rules/{created['id']}"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    missing_response = test_client.get(f"/api/v1/notifications/rules/{created['id']}")
    assert missing_response.status_code == 404


def test_notification_rule_rejects_invalid_webhook(test_client):
    response = test_client.post(
        "/api/v1/notifications/rules",
        json=_rule_payload(target_url_or_email="not-a-url"),
    )
    assert response.status_code == 400


def test_notification_rule_accepts_email_target(test_client):
    response = test_client.post(
        "/api/v1/notifications/rules",
        json=_rule_payload(
            channel_type="email",
            target_url_or_email="alerts@example.com",
        ),
    )
    assert response.status_code == 200
    assert response.json()["channel_type"] == "email"
    assert response.json()["target_url_or_email"] == "alerts@example.com"


def test_notification_history_list_contract(test_client):
    import asyncio

    from backend.secuscan.database import get_db

    create_response = test_client.post(
        "/api/v1/notifications/rules",
        json=_rule_payload(name="History rule"),
    )
    assert create_response.status_code == 200
    rule_id = create_response.json()["id"]

    async def seed_history():
        db = await get_db()
        task_id = str(uuid.uuid4())
        finding_id = str(uuid.uuid4())
        history_id = str(uuid.uuid4())

        await db.execute(
            """
            INSERT INTO tasks (
                id, plugin_id, tool_name, target, status, inputs_json, consent_granted
            ) VALUES (?, 'nmap', 'nmap', '127.0.0.1', 'completed', '{}', 1)
            """,
            (task_id,),
        )
        await db.execute(
            """
            INSERT INTO findings (
                id, task_id, plugin_id, title, category, severity, target, description, remediation
            ) VALUES (?, ?, 'nmap', 'Open port', 'network', 'critical', '127.0.0.1', 'desc', 'fix')
            """,
            (finding_id, task_id),
        )
        await db.execute(
            """
            INSERT INTO notification_history (id, rule_id, finding_id, status, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                history_id,
                rule_id,
                finding_id,
                NotificationDeliveryStatus.SUCCESS.value,
                None,
            ),
        )
        return history_id

    history_id = asyncio.run(seed_history())

    response = test_client.get("/api/v1/notifications/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert any(item["id"] == history_id for item in data["history"])

    filtered = test_client.get(
        f"/api/v1/notifications/history?rule_id={rule_id}&limit=10"
    )
    assert filtered.status_code == 200
    filtered_data = filtered.json()
    assert filtered_data["total"] == 1
    assert filtered_data["history"][0]["rule_id"] == rule_id
    assert filtered_data["history"][0]["finding_id"]
    assert filtered_data["history"][0]["status"] == "success"


def test_admin_diagnostics_notifications(test_client, monkeypatch):
    from backend.secuscan.config import settings

    monkeypatch.setattr(settings, "admin_api_key", "secret-test-key-long")

    # Unauthorized without key
    unauth_resp = test_client.get("/api/v1/admin/diagnostics/notifications")
    assert unauth_resp.status_code == 401

    # Success with key
    auth_resp = test_client.get(
        "/api/v1/admin/diagnostics/notifications",
        headers={"X-API-Key": "secret-test-key-long"},
    )
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert "webhook_timeout_seconds" in data
    assert "webhook_connect_timeout_seconds" in data
    assert "max_retries" in data
    assert "backoff_factor_seconds" in data
    assert type(data["max_retries"]) is int
    assert type(data["webhook_timeout_seconds"]) is float
