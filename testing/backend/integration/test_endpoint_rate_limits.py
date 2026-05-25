import time

from backend.secuscan.config import settings


def test_task_start_bucket_returns_clear_429(test_client, monkeypatch):
    monkeypatch.setattr(settings, "task_start_rate_limit", 1)
    monkeypatch.setattr(settings, "endpoint_rate_limit_window_seconds", 60)

    payload = {
        "plugin_id": "missing_plugin",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }

    first = test_client.post("/api/v1/task/start", json=payload)
    assert first.status_code == 404

    second = test_client.post("/api/v1/task/start", json=payload)
    assert second.status_code == 429
    body = second.json()["detail"]
    assert body["error"] == "rate_limit_exceeded"
    assert body["bucket"] == "task_start"
    assert "Retry-After" in second.headers
    assert second.headers["X-RateLimit-Remaining"] == "0"


def test_endpoint_buckets_are_independent(test_client, monkeypatch):
    monkeypatch.setattr(settings, "task_start_rate_limit", 1)
    monkeypatch.setattr(settings, "vault_rate_limit", 2)
    monkeypatch.setattr(settings, "endpoint_rate_limit_window_seconds", 60)

    payload = {
        "plugin_id": "missing_plugin",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }

    assert test_client.post("/api/v1/task/start", json=payload).status_code == 404
    assert test_client.post("/api/v1/task/start", json=payload).status_code == 429

    vault_response = test_client.get("/api/v1/vault")
    assert vault_response.status_code == 200
    assert vault_response.headers["X-RateLimit-Limit"] == "2"
    assert vault_response.headers["X-RateLimit-Remaining"] == "1"


def test_endpoint_bucket_resets_after_window(test_client, monkeypatch):
    monkeypatch.setattr(settings, "read_heavy_rate_limit", 1)
    monkeypatch.setattr(settings, "endpoint_rate_limit_window_seconds", 1)

    first = test_client.get("/api/v1/tasks")
    assert first.status_code == 200
    assert first.headers["X-RateLimit-Remaining"] == "0"

    limited = test_client.get("/api/v1/tasks")
    assert limited.status_code == 429

    time.sleep(1.1)

    reset = test_client.get("/api/v1/tasks")
    assert reset.status_code == 200
    assert reset.headers["X-RateLimit-Remaining"] == "0"


def test_api_key_identity_has_separate_bucket(test_client, monkeypatch):
    monkeypatch.setattr(settings, "read_heavy_rate_limit", 1)
    monkeypatch.setattr(settings, "endpoint_rate_limit_window_seconds", 60)

    assert test_client.get("/api/v1/tasks").status_code == 200
    assert test_client.get("/api/v1/tasks").status_code == 429

    keyed = test_client.get("/api/v1/tasks", headers={"X-API-Key": "ci-user"})
    assert keyed.status_code == 200
    assert keyed.headers["X-RateLimit-Limit"] == "1"
