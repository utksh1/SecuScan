import time
from unittest.mock import patch

from backend.secuscan.models import TaskStatus


def test_health_check(test_client):
    """Test health check endpoint."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data


def test_list_plugins(test_client):
    """Test plugins list endpoint."""
    response = test_client.get("/api/v1/plugins")
    assert response.status_code == 200
    data = response.json()
    assert "plugins" in data
    assert isinstance(data["plugins"], list)
    assert data["total"] >= 0
    if data["plugins"]:
        first = data["plugins"][0]
        assert "requires_consent" in first
        assert "availability" in first
        assert "runnable" in first["availability"]
        assert "missing_binaries" in first["availability"]


def test_start_task(test_client):
    """Test starting a task with a mocked executor."""
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
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

        task_id = data["task_id"]
        time.sleep(0.2)

        status_response = test_client.get(f"/api/v1/task/{task_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["status"] == TaskStatus.COMPLETED.value

        result_response = test_client.get(f"/api/v1/task/{task_id}/result")
        assert result_response.status_code == 200
        result_data = result_response.json()
        assert "Mocked successful output" in result_data["raw_output_excerpt"]


def test_missing_consent(test_client):
    """Test starting a task without consent."""
    payload = {
        "plugin_id": "http_inspector",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": False,
    }

    response = test_client.post("/api/v1/task/start", json=payload)
    assert response.status_code == 400
    assert "Consent required" in response.json()["detail"]


def test_get_settings(test_client):
    """Test settings endpoint."""
    response = test_client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "network" in data
    assert "sandbox" in data
    assert "safety" in data
