import json
import sqlite3
import time
import uuid
from unittest.mock import patch

from backend.secuscan.config import settings
from backend.secuscan.models import TaskStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_task(task_id: str, target: str, structured_json: dict | None = None) -> None:
    """Insert a minimal completed task row directly into the test DB via sqlite3."""
    with sqlite3.connect(settings.database_path, timeout=10) as conn:
        conn.execute(
            """
            INSERT INTO tasks (
                id, plugin_id, tool_name, target, inputs_json,
                status, consent_granted, safe_mode, structured_json
            ) VALUES (?, ?, ?, ?, '{}', ?, 1, 1, ?)
            """,
            (
                task_id,
                "test_plugin",
                "test_tool",
                target,
                TaskStatus.COMPLETED.value,
                json.dumps(structured_json) if structured_json is not None else None,
            ),
        )


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


# ---------------------------------------------------------------------------
# GET /api/v1/scans/diff — route-level integration tests
# ---------------------------------------------------------------------------

def test_diff_same_scan_returns_400(test_client):
    """Passing the same scan ID for both scan_a and scan_b must return 400."""
    task_id = str(uuid.uuid4())
    _insert_task(task_id, "example.com")

    response = test_client.get(f"/api/v1/scans/diff?scan_a={task_id}&scan_b={task_id}")

    assert response.status_code == 400


def test_diff_different_targets_returns_400(test_client):
    """Two completed scans against different targets must return 400."""
    id_a = str(uuid.uuid4())
    id_b = str(uuid.uuid4())
    _insert_task(id_a, "host-a.example.com")
    _insert_task(id_b, "host-b.example.com")

    response = test_client.get(f"/api/v1/scans/diff?scan_a={id_a}&scan_b={id_b}")

    assert response.status_code == 400


def test_diff_missing_scan_returns_404(test_client):
    """Non-existent scan IDs must return 404."""
    response = test_client.get("/api/v1/scans/diff?scan_a=doesnotexist&scan_b=alsofake")

    assert response.status_code == 404


def test_diff_valid_scans_returns_200(test_client):
    """Two completed scans on the same target must return 200 with the expected shape."""
    id_a = str(uuid.uuid4())
    id_b = str(uuid.uuid4())

    finding_base = {
        "title": "XSS Vulnerability",
        "category": "web",
        "target": "app.example.com",
        "description": "Reflected cross-site scripting",
        "metadata": {},
    }
    _insert_task(id_a, "app.example.com", {"findings": [{**finding_base, "severity": "high"}]})
    _insert_task(id_b, "app.example.com", {"findings": [{**finding_base, "severity": "critical"}]})

    response = test_client.get(f"/api/v1/scans/diff?scan_a={id_a}&scan_b={id_b}")

    assert response.status_code == 200
    data = response.json()
    assert "scan_a" in data
    assert "scan_b" in data
    assert "diff" in data
    assert "summary" in data
