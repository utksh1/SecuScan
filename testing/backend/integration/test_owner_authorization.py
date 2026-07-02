"""
Integration tests for per-user / per-workspace ownership of tasks, findings,
and reports (issue #401 — Broken Object Level Authorization / BOLA).

Two distinct users are simulated by sending different ``X-User-Id`` headers on
top of the shared deployment API key (see auth.resolve_owner_id). The tests
assert that User B can never read, list, delete, or export User A's data, while
User A retains full access to their own.
"""

import sqlite3
import time

import pytest

from backend.secuscan.config import settings


ALICE = {"X-User-Id": "alice"}
BOB = {"X-User-Id": "bob"}

# owner_id values as persisted by auth.resolve_owner_id for the headers above.
ALICE_OWNER = "user:alice"
BOB_OWNER = "user:bob"


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

def test_started_task_records_requesting_user_as_owner(test_client):
    """A task created via the API is owned by the requesting user."""
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
            headers=ALICE,
        )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    assert _task_owner(task_id) == ALICE_OWNER


def test_tasks_created_by_distinct_users_get_distinct_owners(test_client):
    """The default (no header) owner is distinct from an explicit user."""
    _seed_task("default", "legacy-task")
    _seed_task(ALICE_OWNER, "alice-task")

    # The default/no-header client sees only the legacy task.
    resp = test_client.get("/api/v1/tasks")
    assert resp.status_code == 200
    ids = {t["task_id"] for t in resp.json()["tasks"]}
    assert "legacy-task" in ids
    assert "alice-task" not in ids


# ---------------------------------------------------------------------------
# Cross-user GET / report / cancel / delete on a single task
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
def test_user_b_cannot_access_user_a_task(test_client, method, path_tmpl):
    """Every task-scoped endpoint returns 403 for a non-owner."""
    _seed_task(ALICE_OWNER, "alice-task")
    path = path_tmpl.format(tid="alice-task")

    resp = getattr(test_client, method)(path, headers=BOB)
    assert resp.status_code == 403, f"{method.upper()} {path} -> {resp.status_code}: {resp.text}"


def test_user_a_can_access_own_task(test_client):
    """The owner retains full access to their own task."""
    _seed_task(ALICE_OWNER, "alice-task")

    assert test_client.get("/api/v1/task/alice-task/status", headers=ALICE).status_code == 200
    assert test_client.get("/api/v1/task/alice-task/result", headers=ALICE).status_code == 200


def test_unknown_task_returns_404_not_403(test_client):
    """A genuinely missing task is 404; only ownership mismatch is 403."""
    resp = test_client.get("/api/v1/task/does-not-exist/status", headers=BOB)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Vault secrets must stay owner-scoped across CRUD operations
# ---------------------------------------------------------------------------

def test_cross_owner_vault_read_returns_404(test_client):
    """A non-owner should not be able to read another owner's vault secret."""
    secret_name = "cross-owner-read"
    create_resp = test_client.put(
        f"/api/v1/vault/{secret_name}",
        json={"value": "alice-secret"},
        headers=ALICE,
    )
    assert create_resp.status_code == 200

    read_resp = test_client.get(f"/api/v1/vault/{secret_name}", headers=BOB)

    assert read_resp.status_code == 404
    assert read_resp.json()["detail"] == "Secret not found"


def test_cross_owner_vault_update_does_not_overwrite_owner_secret(test_client):
    """A non-owner update should create a separate secret for the caller, not overwrite the owner."""
    secret_name = "cross-owner-update"
    create_resp = test_client.put(
        f"/api/v1/vault/{secret_name}",
        json={"value": "alice-secret"},
        headers=ALICE,
    )
    assert create_resp.status_code == 200

    update_resp = test_client.put(
        f"/api/v1/vault/{secret_name}",
        json={"value": "bob-secret"},
        headers=BOB,
    )
    assert update_resp.status_code == 200

    alice_read = test_client.get(f"/api/v1/vault/{secret_name}", headers=ALICE)
    bob_read = test_client.get(f"/api/v1/vault/{secret_name}", headers=BOB)

    assert alice_read.status_code == 200
    assert alice_read.json()["value"] == "alice-secret"
    assert bob_read.status_code == 200
    assert bob_read.json()["value"] == "bob-secret"


def test_cross_owner_vault_delete_returns_404_and_preserves_owner_secret(test_client):
    """A non-owner delete should not remove the owner's secret and should behave as not found."""
    secret_name = "cross-owner-delete"
    create_resp = test_client.put(
        f"/api/v1/vault/{secret_name}",
        json={"value": "alice-secret"},
        headers=ALICE,
    )
    assert create_resp.status_code == 200

    delete_resp = test_client.delete(f"/api/v1/vault/{secret_name}", headers=BOB)

    assert delete_resp.status_code == 404
    assert delete_resp.json()["detail"] == "Secret not found"

    alice_read = test_client.get(f"/api/v1/vault/{secret_name}", headers=ALICE)
    assert alice_read.status_code == 200
    assert alice_read.json()["value"] == "alice-secret"


# ---------------------------------------------------------------------------
# Listing endpoints must not leak another user's resources
# ---------------------------------------------------------------------------

def test_task_list_is_scoped_to_owner(test_client):
    _seed_task(ALICE_OWNER, "alice-task")
    _seed_task(BOB_OWNER, "bob-task")

    alice_ids = {t["task_id"] for t in test_client.get("/api/v1/tasks", headers=ALICE).json()["tasks"]}
    bob_ids = {t["task_id"] for t in test_client.get("/api/v1/tasks", headers=BOB).json()["tasks"]}

    assert "alice-task" in alice_ids and "bob-task" not in alice_ids
    assert "bob-task" in bob_ids and "alice-task" not in bob_ids


def test_findings_list_is_scoped_to_owner(test_client):
    _seed_task(ALICE_OWNER, "alice-task")
    _seed_task(BOB_OWNER, "bob-task")
    _seed_finding(ALICE_OWNER, "alice-finding", "alice-task")
    _seed_finding(BOB_OWNER, "bob-finding", "bob-task")

    alice_findings = {f["id"] for f in test_client.get("/api/v1/findings", headers=ALICE).json()["findings"]}
    bob_findings = {f["id"] for f in test_client.get("/api/v1/findings", headers=BOB).json()["findings"]}

    assert alice_findings == {"alice-finding"}
    assert bob_findings == {"bob-finding"}


def test_reports_list_is_scoped_to_owner(test_client):
    _seed_task(ALICE_OWNER, "alice-task")
    _seed_task(BOB_OWNER, "bob-task")
    _seed_report(ALICE_OWNER, "report:alice", "alice-task")
    _seed_report(BOB_OWNER, "report:bob", "bob-task")

    alice_reports = {r["id"] for r in test_client.get("/api/v1/reports", headers=ALICE).json()["reports"]}
    bob_reports = {r["id"] for r in test_client.get("/api/v1/reports", headers=BOB).json()["reports"]}

    assert alice_reports == {"report:alice"}
    assert bob_reports == {"report:bob"}


def test_finding_detail_blocks_cross_user_access(test_client):
    _seed_task(ALICE_OWNER, "alice-task")
    _seed_finding(ALICE_OWNER, "alice-finding", "alice-task")

    assert test_client.get("/api/v1/finding/alice-finding", headers=BOB).status_code == 403
    assert test_client.get("/api/v1/finding/alice-finding", headers=ALICE).status_code == 200


# ---------------------------------------------------------------------------
# Bulk delete must only ever touch the caller's own tasks
# ---------------------------------------------------------------------------

def test_bulk_delete_ignores_other_users_tasks(test_client):
    _seed_task(ALICE_OWNER, "alice-task")

    resp = test_client.request("DELETE", "/api/v1/tasks/bulk", json=["alice-task"], headers=BOB)
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 0
    # Alice's task must still exist.
    assert _task_owner("alice-task") == ALICE_OWNER


def test_bulk_delete_removes_only_owned_tasks(test_client):
    _seed_task(ALICE_OWNER, "alice-task")
    _seed_task(BOB_OWNER, "bob-task")

    # Alice attempts to delete both her task and Bob's in one request.
    resp = test_client.request(
        "DELETE", "/api/v1/tasks/bulk", json=["alice-task", "bob-task"], headers=ALICE
    )
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 1
    assert _task_owner("alice-task") is None
    assert _task_owner("bob-task") == BOB_OWNER


def test_clear_only_purges_callers_history(test_client):
    _seed_task(ALICE_OWNER, "alice-task")
    _seed_task(BOB_OWNER, "bob-task")

    resp = test_client.delete("/api/v1/tasks/clear", headers=ALICE)
    assert resp.status_code == 200
    assert _task_owner("alice-task") is None
    assert _task_owner("bob-task") == BOB_OWNER


def test_owner_can_delete_own_task(test_client):
    _seed_task(ALICE_OWNER, "alice-task", status="completed")

    resp = test_client.delete("/api/v1/task/alice-task", headers=ALICE)
    assert resp.status_code == 200
    assert _task_owner("alice-task") is None
