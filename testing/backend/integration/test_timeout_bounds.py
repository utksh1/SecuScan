import pytest
from backend.secuscan.config import settings


def test_task_start_rejects_unsafe_max_scan_time(test_client):
    # Try to start nikto with a value larger than server sandbox_timeout
    payload = {
        "plugin_id": "nikto",
        "inputs": {
            "target": "127.0.0.1",
            "max_scan_time": settings.sandbox_timeout + 999,
        },
        "consent_granted": True,
    }

    r = test_client.post("/api/v1/task/start", json=payload)
    assert r.status_code == 400
    assert "max_scan_time" in r.json().get("detail", "")


def test_task_start_accepts_safe_max_scan_time(test_client):
    # Start nikto with a safe value within server sandbox_timeout
    safe_value = min(300, settings.sandbox_timeout)
    payload = {
        "plugin_id": "nikto",
        "inputs": {"target": "127.0.0.1", "max_scan_time": safe_value},
        "consent_granted": True,
    }

    r = test_client.post("/api/v1/task/start", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "queued"
    assert "task_id" in data
