import time
from unittest.mock import patch

from backend.secuscan.models import TaskStatus


def _create_target_policy(test_client, **overrides):
    payload = {
        "name": "Authorized External Scope",
        "description": "Allows approved public-target assessment",
        "allow_public_targets": True,
        "allow_exploit_validation": True,
        "allow_authenticated_scan": True,
        "default_validation_mode": "proof",
        "allowed_targets": ["8.8.8.8/32", "https://example.com"],
    }
    payload.update(overrides)
    response = test_client.post("/api/v1/target-policies", json=payload)
    assert response.status_code == 200
    return response.json()


def test_target_policy_and_profile_resources(test_client):
    policy = _create_target_policy(test_client)
    listed_policies = test_client.get("/api/v1/target-policies")
    assert listed_policies.status_code == 200
    assert any(item["id"] == policy["id"] for item in listed_policies.json()["items"])

    credential = test_client.post(
        "/api/v1/credential-profiles",
        json={
            "name": "Basic Auth",
            "username_secret_name": "scanner-user",
            "password_secret_name": "scanner-pass",
            "extra_headers": {"X-Role": "scanner"},
        },
    )
    assert credential.status_code == 200

    session = test_client.post(
        "/api/v1/session-profiles",
        json={
            "name": "Captured Session",
            "cookie_secret_name": "scanner-cookie",
            "extra_headers": {"X-Session-Mode": "replay"},
        },
    )
    assert session.status_code == 200

    assert test_client.get("/api/v1/credential-profiles").json()["total"] == 1
    assert test_client.get("/api/v1/session-profiles").json()["total"] == 1


def test_public_target_allowed_when_target_policy_opted_in(test_client, monkeypatch):
    from backend.secuscan.config import settings

    monkeypatch.setattr(settings, "safe_mode_default", True)
    policy = _create_target_policy(test_client, allow_public_targets=True, allow_exploit_validation=False)

    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = ("Mocked successful output", 0)
        response = test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "nmap",
                "inputs": {"target": "8.8.8.8/32"},
                "consent_granted": True,
                "execution_context": {
                    "target_policy_id": policy["id"],
                    "scan_profile": "standard",
                    "validation_mode": "detect_only",
                    "evidence_level": "standard",
                },
            },
        )
        assert response.status_code == 200, response.text


def test_exploit_plugin_requires_exploit_enabled_target_policy(test_client):
    response = test_client.post(
        "/api/v1/task/start",
        json={
            "plugin_id": "xss_exploiter",
            "inputs": {"target": "https://example.com/search?q=test"},
            "consent_granted": True,
            "execution_context": {
                "scan_profile": "standard",
                "validation_mode": "proof",
                "evidence_level": "standard",
            },
        },
    )
    assert response.status_code == 400
    assert "exploit validation" in response.json()["detail"].lower()


def test_network_scanner_correlates_service_to_cve(test_client, monkeypatch):
    from backend.secuscan.config import settings

    monkeypatch.setattr(settings, "safe_mode_default", False)
    nmap_output = "\n".join(
        [
            "22/tcp open ssh OpenSSH 8.2p1 Ubuntu 4ubuntu0.5",
            "80/tcp open http nginx 1.18.0",
        ]
    )

    with patch("backend.secuscan.scanners.base.BaseScanner._execute_command") as mock_exec:
        mock_exec.return_value = (nmap_output, 0)

        response = test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "network_scanner",
                "inputs": {"target": "192.168.1.10"},
                "consent_granted": True,
                "execution_context": {
                    "scan_profile": "standard",
                    "validation_mode": "detect_only",
                    "evidence_level": "standard",
                },
            },
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]

        for _ in range(10):
            status = test_client.get(f"/api/v1/task/{task_id}/status").json()["status"]
            if status == TaskStatus.COMPLETED.value:
                break
            time.sleep(0.1)

        result = test_client.get(f"/api/v1/task/{task_id}/result")
        assert result.status_code == 200
        findings = result.json()["findings"]
        assert any(f.get("cpe") == "cpe:/a:nginx:nginx:1.18.0" for f in findings)
        assert any(f.get("cve") == "CVE-2021-23017" for f in findings)

        asset_rows = test_client.get("/api/v1/assets/services").json()["items"]
        assert any(item.get("cpe") == "cpe:/a:nginx:nginx:1.18.0" for item in asset_rows)
