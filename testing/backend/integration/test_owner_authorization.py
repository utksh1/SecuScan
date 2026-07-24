"""
Integration tests for per-user / per-workspace ownership of tasks, findings,
and reports (issue #401 — Broken Object Level Authorization / BOLA).

Security model: X-User-Id is NOT trusted for ownership (to prevent header
spoofing BOLA). The authenticated principal resolves to DEFAULT_OWNER_ID.
Cross-owner isolation is verified by seeding data directly with different
owner_ids and confirming the API only exposes the caller's data.
"""

import sqlite3
import time

import pytest

from backend.secuscan.config import settings
from backend.secuscan.auth import DEFAULT_OWNER_ID


OWNER_DEFAULT = DEFAULT_OWNER_ID
OWNER_OTHER = "user:other-tenant"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_task(owner_id: str, task_id: str, *, status: str = "completed") -> None:
    """Insert a task row directly with an explicit owner_id."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target,
                               status, inputs_json, structured_json, consent_granted)
            VALUES (?, ?, 'nmap', 'nmap', '127.0.0.1', ?, '{}', '{"findings": []}', 1)
            """,
            (task_id, owner_id, status),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_finding(owner_id: str, finding_id: str, task_id: str) -> None:
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category,
                                  severity, target, description, remediation)
            VALUES (?, ?, ?, 'nmap', 'Open port', 'network', 'low', '127.0.0.1', 'desc', 'fix')
            """,
            (finding_id, owner_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_report(owner_id: str, report_id: str, task_id: str) -> None:
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO reports (id, owner_id, task_id, name, type, status)
            VALUES (?, ?, ?, 'report', 'technical', 'ready')
            """,
            (report_id, owner_id, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def _task_owner(task_id: str):
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute("SELECT owner_id FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Creation wiring
# ---------------------------------------------------------------------------

def test_started_task_records_default_owner(test_client):
    """A task created via the API is owned by DEFAULT_OWNER_ID."""
    from unittest.mock import patch

    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = ("Mocked output", 0)
        resp = test_client.post(
            "/api/v1/task/start",
            json={
                "plugin_id": "http_inspector",
                "preset": "quick",
                "inputs": {"url": "http://127.0.0.1:8000"},
                "consent_granted": True,
            },
        )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    assert _task_owner(task_id) == OWNER_DEFAULT


def test_tasks_created_by_default_owner_are_visible(test_client):
    """Tasks owned by DEFAULT_OWNER_ID are visible to the API client."""
    _seed_task(OWNER_DEFAULT, "default-task")
    resp = test_client.get("/api/v1/tasks")
    assert resp.status_code == 200
    ids = {t["task_id"] for t in resp.json()["tasks"]}
    assert "default-task" in ids


# ---------------------------------------------------------------------------
# Cross-owner isolation — other owner's data is invisible
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "method,path_tmpl",
    [
        ("get", "/api/v1/task/{tid}/status"),
        ("get", "/api/v1/task/{tid}/result"),
        ("get", "/api/v1/task/{tid}/stream"),
        ("get", "/api/v1/task/{tid}/report/csv"),
        ("get", "/api/v1/task/{tid}/report/html"),
        ("get", "/api/v1/task/{tid}/report/pdf"),
        ("get", "/api/v1/task/{tid}/report/sarif"),
        ("post", "/api/v1/task/{tid}/cancel"),
        ("delete", "/api/v1/task/{tid}"),
    ],
)
def test_other_owner_task_returns_403(test_client, method, path_tmpl):
    """Every task-scoped endpoint returns 403 for another owner's task."""
    _seed_task(OWNER_OTHER, "other-task")
    path = path_tmpl.format(tid="other-task")

    resp = getattr(test_client, method)(path)
    assert resp.status_code == 403, f"{method.upper()} {path} -> {resp.status_code}: {resp.text}"


def test_default_owner_can_access_own_task(test_client):
    """The owner retains full access to their own task."""
    _seed_task(OWNER_DEFAULT, "default-task")

    assert test_client.get("/api/v1/task/default-task/status").status_code == 200
    assert test_client.get("/api/v1/task/default-task/result").status_code == 200


def test_unknown_task_returns_404_not_403(test_client):
    """A genuinely missing task is 404; only ownership mismatch is 403."""
    resp = test_client.get("/api/v1/task/does-not-exist/status")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Vault secrets must stay owner-scoped across CRUD operations
# ---------------------------------------------------------------------------

def test_other_owner_vault_read_returns_404(test_client):
    """Another owner's vault secret is not accessible."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT INTO credential_vault (name, owner_id, encrypted_value) VALUES (?, ?, ?)",
            ("cross-owner-read", OWNER_OTHER, "encrypted-blob"),
        )
        conn.commit()
    finally:
        conn.close()

    read_resp = test_client.get("/api/v1/vault/cross-owner-read")
    assert read_resp.status_code == 404
    assert read_resp.json()["detail"] == "Secret not found"


def test_other_owner_vault_delete_returns_404(test_client):
    """Another owner's vault secret cannot be deleted."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT INTO credential_vault (name, owner_id, encrypted_value) VALUES (?, ?, ?)",
            ("cross-owner-delete", OWNER_OTHER, "encrypted-blob"),
        )
        conn.commit()
    finally:
        conn.close()

    delete_resp = test_client.delete("/api/v1/vault/cross-owner-delete")
    assert delete_resp.status_code == 404

    # Verify the secret still exists in DB
    conn = sqlite3.connect(settings.database_path)
    try:
        cur = conn.execute(
            "SELECT 1 FROM credential_vault WHERE name = ? AND owner_id = ?",
            ("cross-owner-delete", OWNER_OTHER),
        )
        assert cur.fetchone() is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Listing endpoints must not leak another user's resources
# ---------------------------------------------------------------------------

def test_task_list_is_scoped_to_owner(test_client):
    _seed_task(OWNER_DEFAULT, "default-task")
    _seed_task(OWNER_OTHER, "other-task")

    resp = test_client.get("/api/v1/tasks")
    assert resp.status_code == 200
    ids = {t["task_id"] for t in resp.json()["tasks"]}
    assert "default-task" in ids
    assert "other-task" not in ids


def test_findings_list_is_scoped_to_owner(test_client):
    _seed_task(OWNER_DEFAULT, "default-task")
    _seed_task(OWNER_OTHER, "other-task")
    _seed_finding(OWNER_DEFAULT, "default-finding", "default-task")
    _seed_finding(OWNER_OTHER, "other-finding", "other-task")

    resp = test_client.get("/api/v1/findings")
    assert resp.status_code == 200
    finding_ids = {f["id"] for f in resp.json()["findings"]}
    assert "default-finding" in finding_ids
    assert "other-finding" not in finding_ids


def test_reports_list_is_scoped_to_owner(test_client):
    _seed_task(OWNER_DEFAULT, "default-task")
    _seed_task(OWNER_OTHER, "other-task")
    _seed_report(OWNER_DEFAULT, "report:default", "default-task")
    _seed_report(OWNER_OTHER, "report:other", "other-task")

    resp = test_client.get("/api/v1/reports")
    assert resp.status_code == 200
    report_ids = {r["id"] for r in resp.json()["reports"]}
    assert "report:default" in report_ids
    assert "report:other" not in report_ids


def test_finding_detail_blocks_cross_user_access(test_client):
    _seed_task(OWNER_DEFAULT, "default-task")
    _seed_finding(OWNER_DEFAULT, "default-finding", "default-task")

    _seed_task(OWNER_OTHER, "other-task")
    _seed_finding(OWNER_OTHER, "other-finding", "other-task")

    assert test_client.get("/api/v1/finding/other-finding").status_code == 403
    assert test_client.get("/api/v1/finding/default-finding").status_code == 200


# ---------------------------------------------------------------------------
# Bulk delete must only ever touch the caller's own tasks
# ---------------------------------------------------------------------------

def test_bulk_delete_ignores_other_owner_tasks(test_client):
    _seed_task(OWNER_DEFAULT, "default-task")

    resp = test_client.request("DELETE", "/api/v1/tasks/bulk", json=["default-task", "other-task"])
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 1
    assert _task_owner("default-task") is None


def test_bulk_delete_does_not_remove_other_owner_tasks(test_client):
    _seed_task(OWNER_OTHER, "other-task")

    resp = test_client.request("DELETE", "/api/v1/tasks/bulk", json=["other-task"])
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 0
    assert _task_owner("other-task") == OWNER_OTHER


def test_clear_only_purges_callers_history(test_client):
    _seed_task(OWNER_DEFAULT, "default-task")
    _seed_task(OWNER_OTHER, "other-task")

    resp = test_client.delete("/api/v1/tasks/clear")
    assert resp.status_code == 200
    assert _task_owner("default-task") is None
    assert _task_owner("other-task") == OWNER_OTHER


def test_owner_can_delete_own_task(test_client):
    _seed_task(OWNER_DEFAULT, "default-task", status="completed")

    resp = test_client.delete("/api/v1/task/default-task")
    assert resp.status_code == 200
    assert _task_owner("default-task") is None


# ---------------------------------------------------------------------------
# Header spoofing regression
# ---------------------------------------------------------------------------

def test_x_user_id_header_cannot_select_other_owner(test_client):
    """Spoofing X-User-Id header cannot access another owner's resources."""
    _seed_task(OWNER_OTHER, "spoof-target")

    resp = test_client.get(
        "/api/v1/task/spoof-target/status",
        headers={"X-User-Id": "other-tenant"},
    )
    assert resp.status_code == 403, (
        "Spoofed X-User-Id header allowed access to another owner's task"
    )
