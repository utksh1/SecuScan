import time
import sqlite3
from unittest.mock import patch

from backend.secuscan.models import TaskStatus
from backend.secuscan.config import settings

def test_health_check(test_client):
    """Test health check endpoint."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert "plugin_check_latency_ms" in data
    assert isinstance(
        data["plugin_check_latency_ms"],
        (int, float),
    )
    assert data["plugin_check_latency_ms"] >= 0

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
        assert "implementation_status" in first
        assert "supports_authenticated_crawling" in first
        assert "supports_session_reuse" in first

def test_plugin_summary(test_client):
    """Test plugin summary endpoint."""

    response = test_client.get("/api/v1/plugins/summary")

    assert response.status_code == 200

    data = response.json()

    assert "total_plugins" in data
    assert "runnable_count" in data
    assert "unavailable_count" in data
    assert "category_counts" in data

    assert isinstance(data["total_plugins"], int)
    assert isinstance(data["runnable_count"], int)
    assert isinstance(data["unavailable_count"], int)
    assert isinstance(data["category_counts"], dict)
    assert (
    data["runnable_count"] +
    data["unavailable_count"]
    ) == data["total_plugins"]

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
        assert "finding_groups" in result_data
        assert "asset_summary" in result_data
        assert "scan_diff" in result_data

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
    assert "execution_context" in data

def test_start_task_missing_plugin(test_client):
    """Starting a task with a missing plugin should return 404 and helpful detail."""
    missing_id = "plugin_does_not_exist_123"
    payload = {
        "plugin_id": missing_id,
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }

    response = test_client.post("/api/v1/task/start", json=payload)
    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert missing_id in detail or "plugin" in detail.lower()


def test_start_task_rejects_unknown_preset_before_queueing(test_client):
    """Starting a task with an unknown preset should fail before a task row is created."""
    payload = {
        "plugin_id": "http_inspector",
        "preset": "stale-preset-name",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }

    response = test_client.post("/api/v1/task/start", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown preset 'stale-preset-name' for plugin 'http_inspector'"

    with sqlite3.connect(settings.database_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 0

class TestSafeModeCIDRBypass:
    """
    Regression tests for issue #267: is_filesystem_target() was treating
    CIDR notation as a filesystem path, silently bypassing safe-mode enforcement.

    With the fix applied, any CIDR target (public or private) must go through
    validate_target(), which enforces safe-mode restrictions correctly.
    """

    def test_public_cidr_rejected_in_safe_mode(self, test_client, monkeypatch):
        """
        The canonical attack payload from issue #267.
        8.8.8.8/32 must be rejected with 400 when safe_mode=True.
        Before the fix, this returned 200 and queued an nmap scan against Google DNS.
        """
        from backend.secuscan.config import settings
        monkeypatch.setattr(settings, "safe_mode_default", True)

        response = test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "nmap",
                "inputs": {"target": "8.8.8.8/32"},
                "consent_granted": True,
            },
        )
        assert response.status_code == 400
        detail = response.json().get("detail", "")
        assert "Public IPs" in detail or "safe mode" in detail.lower(), (
            f"Expected safe-mode rejection message, got: {detail!r}"
        )

    def test_public_class_b_cidr_rejected_in_safe_mode(self, test_client, monkeypatch):
        """1.1.1.1/16 is another CIDR that must be rejected."""
        from backend.secuscan.config import settings
        monkeypatch.setattr(settings, "safe_mode_default", True)

        response = test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "nmap",
                "inputs": {"target": "1.1.1.1/16"},
                "consent_granted": True,
            },
        )
        assert response.status_code == 400

    def test_private_cidr_accepted_in_safe_mode(self, test_client, monkeypatch):
        """
        192.168.1.0/24 is a private CIDR and should be accepted in safe mode.
        This verifies the fix does not break legitimate private-network scanning.
        """
        from backend.secuscan.config import settings
        monkeypatch.setattr(settings, "safe_mode_default", True)

        # Mock executor to avoid actual network scan
        with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
            mock_exec.return_value = ("Mocked successful output", 0)

            response = test_client.post(
                "/api/v1/task/start",
                json={
                    "plugin_id": "nmap",
                    "inputs": {"target": "192.168.1.0/24"},
                    "consent_granted": True,
                },
            )
            # Should be accepted (200) or at worst a concurrency/rate-limit issue (429/503)
            # — NOT a 400 validation rejection
            assert response.status_code != 400, (
                f"Private CIDR should not be rejected by safe mode. Got: {response.json()}"
            )

    def test_cidr_accepted_when_safe_mode_disabled(self, test_client, monkeypatch):
        """
        With safe mode off, a public CIDR should be accepted.
        This verifies we haven't accidentally hardcoded CIDR rejection.
        """
        from backend.secuscan.config import settings
        monkeypatch.setattr(settings, "safe_mode_default", False)

        with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
            mock_exec.return_value = ("Mocked successful output", 0)

            response = test_client.post(
                "/api/v1/task/start",
                json={
                    "plugin_id": "nmap",
                    "inputs": {"target": "8.8.8.8/32"},
                    "consent_granted": True,
                },
            )
            assert response.status_code != 400, (
                f"Public CIDR should be accepted when safe mode is disabled. Got: {response.json()}"
            )

    def test_filesystem_path_still_accepted_for_code_plugins(self, test_client, monkeypatch):
        """
        Regression: filesystem paths must still bypass network validation for code plugins.
        This verifies the fix does not break the intended filesystem-path behaviour.
        """
        from backend.secuscan.config import settings
        monkeypatch.setattr(settings, "safe_mode_default", True)

        with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
            mock_exec.return_value = ("Mocked successful output", 0)

            response = test_client.post(
                "/api/v1/task/start",
                json={
                    "plugin_id": "code_analyzer",  # code-category plugin
                    "inputs": {"target": "/home/user/repo"},
                    "consent_granted": True,
                },
            )
            # Must NOT be rejected with a network-validation 400
            if response.status_code == 400:
                detail = response.json().get("detail", "")
                assert "safe mode" not in detail.lower() and "Public IP" not in detail, (
                    f"Filesystem path was incorrectly rejected by network validation: {detail!r}"
                )

def test_task_retry_idempotency(test_client):
    """Test the /task/{task_id}/retry endpoint is idempotent and rejects non-failed tasks."""
    # Start a task and wait for it to complete/fail
    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = ("Failed", 1)  # Simulate failure

        payload = {
            "plugin_id": "http_inspector",
            "inputs": {"url": "http://127.0.0.1:8000"},
            "consent_granted": True,
        }
        start_res = test_client.post("/api/v1/task/start", json=payload)
        assert start_res.status_code == 200
        task_id = start_res.json()["task_id"]

        time.sleep(0.5)

        # Verify it is failed
        status_res = test_client.get(f"/api/v1/task/{task_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == TaskStatus.FAILED.value

        # Attempt to retry it multiple times concurrently/rapidly
        mock_exec.return_value = ("Mocked successful output", 0)  # Next run succeeds

        # We must mock execute_task so the TestClient doesn't run it inline
        # before the second retry request can even be fired.
        with patch("backend.secuscan.executor.TaskExecutor.execute_task"):
            retry_res_1 = test_client.post(f"/api/v1/task/{task_id}/retry")
            retry_res_2 = test_client.post(f"/api/v1/task/{task_id}/retry")

            assert retry_res_1.status_code == 200
            assert retry_res_1.json()["status"] == "queued"

            # Second immediate retry should hit idempotency check
            assert retry_res_2.status_code == 409

        # Now let it actually run to completion manually
        import asyncio
        from backend.secuscan.executor import executor
        asyncio.run(executor.execute_task(task_id))

        # Verify it completed successfully this time
        status_res = test_client.get(f"/api/v1/task/{task_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["status"] == TaskStatus.COMPLETED.value

        # Attempting to retry a completed task should fail
        retry_res_3 = test_client.post(f"/api/v1/task/{task_id}/retry")
        assert retry_res_3.status_code == 400

def test_task_retry_authorization(test_client):
    """Test the /task/{task_id}/retry endpoint properly scopes to owner."""
    import sqlite3
    from backend.secuscan.config import settings

    payload = {
        "plugin_id": "http_inspector",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }
    start_res = test_client.post("/api/v1/task/start", json=payload)
    assert start_res.status_code == 200
    task_id = start_res.json()["task_id"]

    # Temporarily change owner in the database to simulate another user's task
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE tasks SET owner_id = 'other_owner', status = 'failed' WHERE id = ?", (task_id,))
        conn.commit()

    # Attempt to retry it with our default test_client (which is not 'other_owner')
    retry_res = test_client.post(f"/api/v1/task/{task_id}/retry")
    assert retry_res.status_code == 403
    assert "access" in retry_res.json()["detail"].lower()

def test_task_retry_terminal_states(test_client):
    """Test retry behavior explicitly on all terminal vs non-terminal statuses."""
    import sqlite3
    from backend.secuscan.config import settings

    payload = {
        "plugin_id": "http_inspector",
        "inputs": {"url": "http://127.0.0.1:8000"},
        "consent_granted": True,
    }
    start_res = test_client.post("/api/v1/task/start", json=payload)
    assert start_res.status_code == 200
    task_id = start_res.json()["task_id"]

    # Test mapping of status to expected HTTP response codes when hitting /retry
    status_expectations = [
        ("completed", 400),
        ("failed", 200),
        ("cancelled", 200),
        ("queued", 409),
        ("running", 409),
    ]

    for status, expected_code in status_expectations:
        with sqlite3.connect(settings.database_path) as conn:
            conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
            conn.commit()

        with patch("backend.secuscan.executor.TaskExecutor.execute_task"):
            res = test_client.post(f"/api/v1/task/{task_id}/retry")
            assert res.status_code == expected_code, f"Expected {expected_code} for status '{status}', got {res.status_code}"
