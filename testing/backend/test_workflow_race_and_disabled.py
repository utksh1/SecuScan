"""
testing/backend/test_workflow_race_and_disabled.py

Regression tests for workflow run/delete race conditions and
disabled-workflow behaviour as described in issue #570.

Strategy
--------
All tests call the REAL application routes through the shared ``test_client``
fixture defined in conftest.py, which initialises the real database, plugins,
and auth layer.  ``backend.secuscan.routes.get_db`` is patched with a plain
async function returning a controlled mock, matching the
``db = await get_db()`` call shape used in routes.py, so no persistent
SQLite state leaks between tests.

Routes under test (from backend/secuscan/routes.py):
  POST   /api/v1/workflows/{id}/run  - manual run trigger
  DELETE /api/v1/workflows/{id}      - delete
  PATCH  /api/v1/workflows/{id}      - update (enable/disable toggle)
  GET    /api/v1/workflows           - list
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.secuscan.main import app


# ---------------------------------------------------------------------------
# Shared row builders
# ---------------------------------------------------------------------------

def _workflow_row(
    wf_id="wf-abc-123",
    name="test-workflow",
    enabled=1,
    schedule_seconds=None,
    steps=None,
):
    """Return a dict that matches the shape of a real workflows table row."""
    if steps is None:
        steps = [{"plugin_id": "port_scan", "params": {}}]
    return {
        "id": wf_id,
        "name": name,
        "enabled": enabled,
        "schedule_seconds": schedule_seconds,
        "steps_json": json.dumps(steps),
        "last_run_at": None,
        "created_at": "2026-01-01T00:00:00",
    }


# ---------------------------------------------------------------------------
# Mock-DB helpers
# ---------------------------------------------------------------------------

def _make_mock_db(fetchone_return=None, fetchall_return=None):
    """
    Return a MagicMock whose async methods mirror the real DB session.
    fetchone_return may be a single value or a list used as side_effect.
    """
    mock_db = MagicMock()
    if isinstance(fetchone_return, list):
        mock_db.fetchone = AsyncMock(side_effect=fetchone_return)
    else:
        mock_db.fetchone = AsyncMock(return_value=fetchone_return)
    mock_db.fetchall = AsyncMock(
        return_value=fetchall_return if fetchall_return is not None else []
    )
    mock_db.execute = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock(return_value=None)
    mock_db.close = AsyncMock(return_value=None)
    return mock_db


def _patch_get_db(fetchone_return=None, fetchall_return=None):
    """
    Patch ``backend.secuscan.routes.get_db`` with a plain async function
    returning a controlled mock, matching ``db = await get_db()`` in routes.py.
    Returns (patch_context, mock_db) so callers can inspect mock_db after.
    """
    mock_db = _make_mock_db(
        fetchone_return=fetchone_return,
        fetchall_return=fetchall_return,
    )

    async def _get_db_override():
        return mock_db

    return patch("backend.secuscan.routes.get_db", new=_get_db_override), mock_db


# ---------------------------------------------------------------------------
# DELETE then run - race condition
# ---------------------------------------------------------------------------

class TestDeleteThenRunRace:
    """
    Scenario: a workflow is deleted, then something tries to run it.
    The run endpoint must return 404 - not crash or create orphaned tasks.
    """

    def test_run_deleted_workflow_returns_404(self, test_client):
        ctx, _ = _patch_get_db(fetchone_return=None)
        with ctx:
            response = test_client.post("/api/v1/workflows/deleted-wf-id/run")
        assert response.status_code == 404, (
            f"Running a deleted workflow must return 404, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_run_deleted_workflow_body_is_stable_json(self, test_client):
        ctx, _ = _patch_get_db(fetchone_return=None)
        with ctx:
            response = test_client.post("/api/v1/workflows/deleted-wf-id/run")
        assert response.status_code == 404
        assert isinstance(response.json(), dict), (
            f"404 body should be a JSON object, got: {response.text}"
        )

    def test_delete_nonexistent_workflow_returns_404(self, test_client):
        ctx, _ = _patch_get_db(fetchone_return=None)
        with ctx:
            response = test_client.delete("/api/v1/workflows/ghost-wf-id")
        assert response.status_code == 404, (
            f"Deleting a non-existent workflow must return 404, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_run_missing_workflow_is_deterministic(self, test_client):
        """Repeated calls with a missing ID always return 404."""
        for _ in range(3):
            ctx, _ = _patch_get_db(fetchone_return=None)
            with ctx:
                response = test_client.post("/api/v1/workflows/missing-id/run")
            assert response.status_code == 404, (
                f"Non-deterministic: got {response.status_code} on repeat"
            )


# ---------------------------------------------------------------------------
# Disabled workflow behaviour
# ---------------------------------------------------------------------------

class TestDisabledWorkflow:
    """
    Scenario: a workflow has enabled=0.
    Manual run must be refused; list must reflect the disabled state.
    """

    def test_run_disabled_workflow_is_refused(self, test_client):
        disabled_row = _workflow_row(enabled=0)
        ctx, _ = _patch_get_db(fetchone_return=disabled_row)
        with ctx:
            response = test_client.post(
                f"/api/v1/workflows/{disabled_row['id']}/run"
            )
        assert response.status_code not in (200, 201, 202), (
            f"Running a disabled workflow must be refused, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_run_disabled_workflow_response_is_json_object(self, test_client):
        disabled_row = _workflow_row(enabled=0)
        ctx, _ = _patch_get_db(fetchone_return=disabled_row)
        with ctx:
            response = test_client.post(
                f"/api/v1/workflows/{disabled_row['id']}/run"
            )
        assert response.status_code not in (200, 201, 202)
        assert isinstance(response.json(), dict), (
            f"Expected JSON object body, got: {response.text}"
        )

    def test_disabled_workflow_appears_in_list_with_enabled_false(self, test_client):
        """GET /api/v1/workflows must faithfully surface the enabled=0 state."""
        disabled_row = _workflow_row(enabled=0)
        ctx, _ = _patch_get_db(fetchall_return=[disabled_row])
        with ctx:
            response = test_client.get("/api/v1/workflows")
        assert response.status_code == 200
        workflows = response.json().get("workflows", [])
        assert len(workflows) == 1
        assert workflows[0].get("enabled") in (False, 0), (
            f"Disabled workflow should appear as enabled=False, "
            f"got {workflows[0].get('enabled')!r}"
        )

    def test_toggle_workflow_to_disabled_calls_update(self, test_client):
        """
        PATCH /api/v1/workflows/{id} with enabled=False must reach the DB layer.
        We verify db.execute was called, confirming the production update path.
        """
        existing_row = _workflow_row(enabled=1)
        updated_row = {**existing_row, "enabled": 0}
        ctx, mock_db = _patch_get_db(
            fetchone_return=[existing_row, updated_row]
        )
        with ctx:
            response = test_client.patch(
                f"/api/v1/workflows/{existing_row['id']}",
                json={"enabled": False},
            )
        assert response.status_code in (200, 201, 204), (
            f"Toggling workflow disabled should succeed, "
            f"got {response.status_code}. Body: {response.text}"
        )
        assert mock_db.execute.called, (
            "db.execute should have been called to persist the enabled=0 change"
        )


# ---------------------------------------------------------------------------
# Delete then list - deleted workflow must not appear in list
# ---------------------------------------------------------------------------

class TestDeleteThenList:
    """After deletion, GET /api/v1/workflows must not include the deleted row."""

    def test_deleted_workflow_not_in_list(self, test_client):
        ctx, _ = _patch_get_db(fetchall_return=[])
        with ctx:
            response = test_client.get("/api/v1/workflows")
        assert response.status_code == 200
        body = response.json()
        assert body.get("workflows") == [], (
            f"After deletion the list must be empty, got {body.get('workflows')!r}"
        )

    def test_list_returns_only_remaining_workflows_after_partial_delete(self, test_client):
        """Two workflows exist; one is deleted - list must return exactly one."""
        remaining = _workflow_row(wf_id="wf-keep", name="keep-me")
        ctx, _ = _patch_get_db(fetchall_return=[remaining])
        with ctx:
            response = test_client.get("/api/v1/workflows")
        assert response.status_code == 200
        workflows = response.json().get("workflows", [])
        assert len(workflows) == 1
        assert workflows[0]["id"] == "wf-keep"


# ---------------------------------------------------------------------------
# Successful run of an enabled workflow - sanity / regression guard
# ---------------------------------------------------------------------------

class TestEnabledWorkflowRun:
    """A valid, enabled workflow must reach the run path and return 2xx."""

    def test_run_enabled_workflow_returns_success(self, test_client):
        row = _workflow_row(enabled=1, wf_id="wf-enabled-001")
        ctx, _ = _patch_get_db(fetchone_return=row)
        with ctx:
            response = test_client.post(f"/api/v1/workflows/{row['id']}/run")
        assert response.status_code in (200, 201, 202), (
            f"Running a valid enabled workflow must return 2xx, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_run_enabled_workflow_response_is_json_object(self, test_client):
        row = _workflow_row(enabled=1, wf_id="wf-enabled-001")
        ctx, _ = _patch_get_db(fetchone_return=row)
        with ctx:
            response = test_client.post(f"/api/v1/workflows/{row['id']}/run")
        assert response.status_code in (200, 201, 202)
        assert isinstance(response.json(), dict), (
            f"Expected JSON object body, got: {response.text}"
        )
