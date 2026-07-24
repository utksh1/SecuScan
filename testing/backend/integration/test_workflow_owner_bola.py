"""
Integration tests for per-user ownership of workflows and notification rules
(issue #961 — BOLA in workflow and notification rule CRUD).

Security model: X-User-Id is NOT trusted for ownership (to prevent header
spoofing BOLA). The authenticated principal resolves to DEFAULT_OWNER_ID.
Cross-owner isolation is verified by seeding data directly with different
owner_ids and confirming the API only exposes the caller's data.
"""

import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from backend.secuscan.config import settings
from backend.secuscan.auth import DEFAULT_OWNER_ID


OWNER_DEFAULT = DEFAULT_OWNER_ID
OWNER_OTHER = "user:other-tenant"


# ---------------------------------------------------------------------------
# DB helpers (direct SQL, bypasses the API for fixture setup)
# ---------------------------------------------------------------------------

def _conn():
    return sqlite3.connect(settings.database_path)


def _seed_workflow(owner_id: str, workflow_id: str, name: str,
                   *, schedule_seconds=3600, enabled=1):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO workflows (id, name, owner_id, schedule_seconds, enabled, steps_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (workflow_id, name, owner_id, schedule_seconds, enabled,
             json.dumps([{"plugin_id": "http_inspector", "inputs": {"url": "http://example.com"}}])),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_workflow_version(workflow_id: str, version_number: int):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO workflow_versions "
            "(id, workflow_id, version_number, definition_json, created_by) "
            "VALUES (?, ?, ?, ?, 'test')",
            (f"v-{workflow_id}-{version_number}", workflow_id, version_number,
             json.dumps({"name": "test", "enabled": True, "steps": []})),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_notification_rule(owner_id: str, rule_id: str, name: str):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO notification_rules "
            "(id, name, owner_id, severity_threshold, channel_type, target_url_or_email) "
            "VALUES (?, ?, ?, 'medium', 'email', 'a@b.com')",
            (rule_id, name, owner_id),
        )
        conn.commit()
    finally:
        conn.close()


def _workflow_owner(workflow_id: str):
    conn = _conn()
    try:
        cur = conn.execute("SELECT owner_id FROM workflows WHERE id = ?", (workflow_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _workflow_exists(workflow_id: str) -> bool:
    conn = _conn()
    try:
        cur = conn.execute("SELECT 1 FROM workflows WHERE id = ?", (workflow_id,))
        return cur.fetchone() is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Workflow fixtures — payload helper
# ---------------------------------------------------------------------------

def _wf_payload(name: str = "Nightly Scan"):
    return {
        "name": name,
        "schedule_seconds": 3600,
        "enabled": True,
        "steps": [{"plugin_id": "http_inspector", "inputs": {"url": "http://127.0.0.1:8000"}}],
    }


# ---------------------------------------------------------------------------
# Workflow creation and ownership
# ---------------------------------------------------------------------------

def test_created_workflow_has_default_owner(test_client):
    """A workflow created via the API is owned by DEFAULT_OWNER_ID."""
    resp = test_client.post("/api/v1/workflows", json=_wf_payload("MyScan"))
    assert resp.status_code == 200, resp.text
    wf = resp.json()
    assert _workflow_owner(wf["id"]) == OWNER_DEFAULT


# ---------------------------------------------------------------------------
# Cross-owner isolation — other owner's workflows are invisible
# ---------------------------------------------------------------------------

def test_workflow_list_is_scoped_to_owner(test_client):
    _seed_workflow(OWNER_DEFAULT, "wf-default-1", "DefaultWF")
    _seed_workflow(OWNER_OTHER, "wf-other-1", "OtherWF")

    resp = test_client.get("/api/v1/workflows")
    assert resp.status_code == 200
    wf_ids = {w["id"] for w in resp.json()["workflows"]}
    assert "wf-default-1" in wf_ids
    assert "wf-other-1" not in wf_ids


def test_workflow_update_blocks_other_owner(test_client):
    _seed_workflow(OWNER_OTHER, "wf-other-upd", "OtherWF")

    resp = test_client.patch("/api/v1/workflows/wf-other-upd", json={"enabled": False})
    assert resp.status_code in (403, 404), resp.text


def test_workflow_delete_blocks_other_owner(test_client):
    _seed_workflow(OWNER_OTHER, "wf-other-del", "OtherWF")

    resp = test_client.delete("/api/v1/workflows/wf-other-del")
    assert resp.status_code in (403, 404), resp.text
    assert _workflow_exists("wf-other-del")


def test_workflow_run_blocks_other_owner(test_client):
    _seed_workflow(OWNER_OTHER, "wf-other-run", "OtherWF", enabled=0)

    with patch("backend.secuscan.routes.executor.create_task", new=AsyncMock(return_value="t-1")), \
         patch("backend.secuscan.routes.executor.execute_task", new=AsyncMock()):
        resp = test_client.post("/api/v1/workflows/wf-other-run/run")
    assert resp.status_code in (403, 404), resp.text


def test_workflow_runs_blocks_other_owner(test_client):
    _seed_workflow(OWNER_OTHER, "wf-other-runs", "OtherWF")

    resp = test_client.get("/api/v1/workflows/wf-other-runs/runs")
    assert resp.status_code in (403, 404), resp.text


def test_workflow_versions_blocks_other_owner(test_client):
    _seed_workflow(OWNER_OTHER, "wf-other-vers", "OtherWF")
    _seed_workflow_version("wf-other-vers", 1)

    resp = test_client.get("/api/v1/workflows/wf-other-vers/versions")
    assert resp.status_code in (403, 404), resp.text


def test_workflow_rollback_blocks_other_owner(test_client):
    _seed_workflow(OWNER_OTHER, "wf-other-rb", "OtherWF")
    _seed_workflow_version("wf-other-rb", 1)

    resp = test_client.post("/api/v1/workflows/wf-other-rb/rollback/1")
    assert resp.status_code in (403, 404), resp.text


# ---------------------------------------------------------------------------
# Owners can access their own workflows
# ---------------------------------------------------------------------------

def test_workflow_owner_can_update(test_client):
    _seed_workflow(OWNER_DEFAULT, "wf-own-upd", "OwnWF")

    resp = test_client.patch("/api/v1/workflows/wf-own-upd", json={"enabled": False})
    assert resp.status_code == 200, resp.text


def test_workflow_owner_can_delete(test_client):
    _seed_workflow(OWNER_DEFAULT, "wf-own-del", "OwnWF")

    resp = test_client.delete("/api/v1/workflows/wf-own-del")
    assert resp.status_code == 200, resp.text
    assert not _workflow_exists("wf-own-del")


# ---------------------------------------------------------------------------
# Cross-owner isolation — notification rules
# ---------------------------------------------------------------------------

def test_notification_rule_list_is_scoped_to_owner(test_client):
    _seed_notification_rule(OWNER_DEFAULT, "nr-default", "DefaultRule")
    _seed_notification_rule(OWNER_OTHER, "nr-other", "OtherRule")

    resp = test_client.get("/api/v1/notifications/rules")
    assert resp.status_code == 200
    rule_ids = {r["id"] for r in resp.json()["rules"]}
    assert "nr-default" in rule_ids
    assert "nr-other" not in rule_ids


def test_notification_rule_get_blocks_other_owner(test_client):
    _seed_notification_rule(OWNER_OTHER, "nr-other-get", "RuleGet")

    resp = test_client.get("/api/v1/notifications/rules/nr-other-get")
    assert resp.status_code in (403, 404), resp.text


def test_notification_rule_update_blocks_other_owner(test_client):
    _seed_notification_rule(OWNER_OTHER, "nr-other-upd", "RuleUpd")

    resp = test_client.patch(
        "/api/v1/notifications/rules/nr-other-upd",
        json={"severity_threshold": "high"},
    )
    assert resp.status_code in (403, 404), resp.text


def test_notification_rule_delete_blocks_other_owner(test_client):
    _seed_notification_rule(OWNER_OTHER, "nr-other-del", "RuleDel")

    resp = test_client.delete("/api/v1/notifications/rules/nr-other-del")
    assert resp.status_code in (403, 404), resp.text

    # Must still exist
    conn = _conn()
    try:
        cur = conn.execute("SELECT 1 FROM notification_rules WHERE id = 'nr-other-del'")
        assert cur.fetchone() is not None
    finally:
        conn.close()


def test_notification_rule_owner_can_update(test_client):
    _seed_notification_rule(OWNER_DEFAULT, "nr-own-upd", "OwnRule")

    resp = test_client.patch(
        "/api/v1/notifications/rules/nr-own-upd",
        json={"severity_threshold": "high"},
    )
    assert resp.status_code == 200, resp.text


def test_notification_rule_owner_can_delete(test_client):
    _seed_notification_rule(OWNER_DEFAULT, "nr-own-del", "OwnRule")

    resp = test_client.delete("/api/v1/notifications/rules/nr-own-del")
    assert resp.status_code == 200, resp.text

    conn = _conn()
    try:
        cur = conn.execute("SELECT 1 FROM notification_rules WHERE id = 'nr-own-del'")
        assert cur.fetchone() is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Unknown / missing resources return 404, not 403
# ---------------------------------------------------------------------------

def test_unknown_workflow_returns_404_not_403(test_client):
    resp = test_client.get("/api/v1/workflows/does-not-exist/runs")
    assert resp.status_code == 404, resp.text


def test_unknown_notification_rule_returns_404_not_403(test_client):
    resp = test_client.get("/api/v1/notifications/rules/does-not-exist")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Header spoofing regression
# ---------------------------------------------------------------------------

def test_x_user_id_header_cannot_select_other_owner_workflow(test_client):
    """Spoofed X-User-Id cannot access another owner's workflow."""
    _seed_workflow(OWNER_OTHER, "wf-spoof-target", "SpoofTarget")

    resp = test_client.get(
        "/api/v1/workflows/wf-spoof-target/runs",
        headers={"X-User-Id": "other-tenant"},
    )
    assert resp.status_code in (403, 404), (
        "Spoofed X-User-Id header allowed access to another owner's workflow"
    )
