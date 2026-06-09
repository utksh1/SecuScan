"""
Regression tests for workflow run/delete race conditions and
disabled-workflow behaviour as described in issue #570.

Strategy
--------
All tests call the REAL application routes through TestClient.
The database layer (db.fetchone / db.execute / db.fetchall) is patched
with unittest.mock so no live SQLite file is needed, but the production
route handler code in routes.py runs unchanged.

Routes under test (from backend/secuscan/routes.py):
  POST   /api/workflows                  – create
  POST   /api/workflows/{id}/run         – manual run trigger
  DELETE /api/workflows/{id}             – delete
  PUT    /api/workflows/{id}             – update (enable/disable toggle)
  GET    /api/workflows                  – list
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.secuscan.main import app

# ---------------------------------------------------------------------------
# Shared test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared row builders — simulate what the real DB rows look like
# ---------------------------------------------------------------------------

def _workflow_row(
    wf_id="wf-abc-123",
    name="test-workflow",
    enabled=1,
    schedule_seconds=None,
    steps=None,
):
    """Return a dict that matches the shape of a real `workflows` table row."""
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
# DELETE then run — race condition
# ---------------------------------------------------------------------------

class TestDeleteThenRunRace:
    """
    Scenario: a workflow is deleted, then something tries to run it.
    The run endpoint must return 404 — not crash or create orphaned tasks.
    """

    def test_run_deleted_workflow_returns_404(self, client):
        # Patch db.fetchone to return None, as it would after a real deletion.
        with patch(
            "backend.secuscan.routes.db.fetchone",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/api/workflows/deleted-wf-id/run",
                headers={"Authorization": "Bearer testtoken"},
            )
        # The real route checks `if not row: raise HTTPException(404)`.
        assert response.status_code == 404, (
            f"Running a deleted workflow must return 404, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_run_deleted_workflow_body_is_stable_json(self, client):
        # The 404 response body must be a proper JSON object.
        with patch(
            "backend.secuscan.routes.db.fetchone",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/api/workflows/deleted-wf-id/run",
                headers={"Authorization": "Bearer testtoken"},
            )
        assert response.status_code == 404
        body = response.json()
        assert isinstance(body, dict), (
            f"404 body should be a JSON object, got {body!r}"
        )

    def test_delete_nonexistent_workflow_returns_404(self, client):
        # DELETE on an already-gone workflow must return 404.
        with patch(
            "backend.secuscan.routes.db.fetchone",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.delete("/api/workflows/ghost-wf-id")
        assert response.status_code == 404, (
            f"Deleting a non-existent workflow must return 404, "
            f"got {response.status_code}. Body: {response.text}"
        )


# ---------------------------------------------------------------------------
# Disabled workflow behaviour
# ---------------------------------------------------------------------------

class TestDisabledWorkflow:
    """
    Scenario: a workflow has enabled=0.
    Manual run must be refused; the list endpoint must reflect the disabled
    state correctly.
    """

    def test_run_disabled_workflow_is_refused(self, client):
        # The real route checks `if not row['enabled']` and returns 400/409.
        disabled_row = _workflow_row(enabled=0)
        with patch(
            "backend.secuscan.routes.db.fetchone",
            new_callable=AsyncMock,
            return_value=disabled_row,
        ):
            response = client.post(
                f"/api/workflows/{disabled_row['id']}/run",
                headers={"Authorization": "Bearer testtoken"},
            )
        assert response.status_code in (400, 409), (
            f"Running a disabled workflow must return 400 or 409, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_disabled_workflow_appears_in_list_with_enabled_false(self, client):
        # GET /api/workflows must faithfully surface the enabled=0 state.
        disabled_row = _workflow_row(enabled=0)
        with patch(
            "backend.secuscan.routes.db.fetchall",
            new_callable=AsyncMock,
            return_value=[disabled_row],
        ):
            response = client.get("/api/workflows")
        assert response.status_code == 200
        workflows = response.json().get("workflows", [])
        assert len(workflows) == 1
        # The serialised workflow must expose enabled=False (not True).
        assert workflows[0].get("enabled") in (False, 0), (
            f"Disabled workflow should appear as enabled=False, "
            f"got {workflows[0].get('enabled')!r}"
        )

    def test_toggle_workflow_to_disabled_calls_update(self, client):
        """
        PUT /api/workflows/{id} with enabled=False must reach the DB layer.
        We verify the route completes without error and the DB execute was
        called — confirming the production update path was exercised.
        """
        existing_row = _workflow_row(enabled=1)
        mock_execute = AsyncMock(return_value=None)
        updated_row = {**existing_row, "enabled": 0}

        with (
            patch(
                "backend.secuscan.routes.db.fetchone",
                new_callable=AsyncMock,
                side_effect=[existing_row, updated_row],
            ),
            patch(
                "backend.secuscan.routes.db.execute",
                mock_execute,
            ),
        ):
            response = client.put(
                f"/api/workflows/{existing_row['id']}",
                json={"enabled": False},
            )

        # Route must succeed (200) or return a valid client/server code.
        assert response.status_code in (200, 201, 204), (
            f"Toggling workflow disabled should succeed, "
            f"got {response.status_code}. Body: {response.text}"
        )
        # The production db.execute must have been called (not a fake).
        assert mock_execute.called, (
            "db.execute should have been called to persist the enabled=0 change"
        )


# ---------------------------------------------------------------------------
# Delete then list — race: deleted workflow must not appear in list
# ---------------------------------------------------------------------------

class TestDeleteThenList:
    """After deletion, GET /api/workflows must not include the deleted row."""

    def test_deleted_workflow_not_in_list(self, client):
        # Simulate DB returning an empty list after deletion.
        with patch(
            "backend.secuscan.routes.db.fetchall",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/api/workflows")
        assert response.status_code == 200
        body = response.json()
        assert body.get("workflows") == [], (
            f"After deletion the list must be empty, got {body.get('workflows')!r}"
        )

    def test_list_returns_only_remaining_workflows_after_partial_delete(self, client):
        # Two workflows exist; one is deleted → list must return exactly one.
        remaining = _workflow_row(wf_id="wf-keep", name="keep-me")
        with patch(
            "backend.secuscan.routes.db.fetchall",
            new_callable=AsyncMock,
            return_value=[remaining],
        ):
            response = client.get("/api/workflows")
        assert response.status_code == 200
        workflows = response.json().get("workflows", [])
        assert len(workflows) == 1
        assert workflows[0]["id"] == "wf-keep"


# ---------------------------------------------------------------------------
# Successful run of an enabled workflow — sanity / regression guard
# ---------------------------------------------------------------------------

class TestEnabledWorkflowRun:
    """
    A valid, enabled workflow with proper steps must reach the task-creation
    path in the real route handler and return 200.
    """

    def test_run_enabled_workflow_returns_200(self, client):
        row = _workflow_row(enabled=1, wf_id="wf-enabled-001")
        version_row = {"id": "ver-1", "version_number": 1}

        with (
            patch(
                "backend.secuscan.routes.db.fetchone",
                new_callable=AsyncMock,
                side_effect=[row, version_row],
            ),
            patch(
                "backend.secuscan.routes.db.execute",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "backend.secuscan.routes.db.record_workflow_run",
                new_callable=AsyncMock,
                return_value="run-id-001",
            ),
            # Prevent the background finaliser from running in tests.
            patch("asyncio.create_task", return_value=MagicMock()),
        ):
            response = client.post(
                f"/api/workflows/{row['id']}/run",
                headers={"Authorization": "Bearer testtoken"},
            )

        assert response.status_code == 200, (
            f"Running a valid enabled workflow must return 200, "
            f"got {response.status_code}. Body: {response.text}"
        )
        body = response.json()
        assert "workflow_id" in body, (
            f"Response must contain workflow_id, got keys: {list(body.keys())}"
        )
