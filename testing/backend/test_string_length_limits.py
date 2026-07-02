import pytest

def test_target_policy_length_constraints(test_client):
    # Name > 255 characters
    long_name = "a" * 256
    response = test_client.post("/api/v1/target-policies", json={"name": long_name})
    assert response.status_code == 400
    assert "name exceeds maximum length of 255 characters" in response.json()["detail"]

    # Description > 2000 characters
    long_desc = "a" * 2001
    response = test_client.post("/api/v1/target-policies", json={"name": "Valid Name", "description": long_desc})
    assert response.status_code == 400
    assert "description exceeds maximum length of 2000 characters" in response.json()["detail"]


def test_credential_profile_length_constraints(test_client):
    # Name > 255 characters
    long_name = "a" * 256
    response = test_client.post("/api/v1/credential-profiles", json={"name": long_name})
    assert response.status_code == 400
    assert "name exceeds maximum length of 255 characters" in response.json()["detail"]


def test_session_profile_length_constraints(test_client):
    # Name > 255 characters
    long_name = "a" * 256
    response = test_client.post("/api/v1/session-profiles", json={"name": long_name})
    assert response.status_code == 400
    assert "name exceeds maximum length of 255 characters" in response.json()["detail"]

    # Notes > 2000 characters
    long_notes = "a" * 2001
    response = test_client.post("/api/v1/session-profiles", json={"name": "Valid Name", "notes": long_notes})
    assert response.status_code == 400
    assert "notes exceeds maximum length of 2000 characters" in response.json()["detail"]


def test_workflow_length_constraints(test_client):
    # Name > 255 characters
    long_name = "a" * 256
    response = test_client.post(
        "/api/v1/workflows",
        json={"name": long_name, "steps": [{"plugin_id": "port_scan", "inputs": {}}]}
    )
    assert response.status_code == 400
    assert "name exceeds maximum length of 255 characters" in response.json()["detail"]


def test_notification_rule_length_constraints(test_client):
    # Pydantic validation: Name > 255 characters
    long_name = "a" * 256
    response = test_client.post(
        "/api/v1/notifications/rules",
        json={
            "name": long_name,
            "severity_threshold": "high",
            "channel_type": "email",
            "target_url_or_email": "test@example.com"
        }
    )
    assert response.status_code == 422

    # Pydantic validation: Target > 2000 characters
    long_target = "a" * 2001 + "@example.com"
    response = test_client.post(
        "/api/v1/notifications/rules",
        json={
            "name": "Valid Rule",
            "severity_threshold": "high",
            "channel_type": "email",
            "target_url_or_email": long_target
        }
    )
    assert response.status_code == 422
