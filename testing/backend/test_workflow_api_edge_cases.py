import json
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from backend.secuscan.main import app


# ---------------------------------------------------------------------------
# Shared test client
# ---------------------------------------------------------------------------

@pytest.fixture
def client(test_client):
    return test_client


# ---------------------------------------------------------------------------
# Helpers — payload / step builders
# ---------------------------------------------------------------------------

def _step(plugin_id="port_scan", **extra):
    """Return a minimal valid step dict, with optional field overrides."""
    s = {"plugin_id": plugin_id, "params": {}}
    s.update(extra)
    return s


def _payload(steps=None, **extra):
    """Return a minimal valid workflow payload."""
    base = {
        "name": "edge-case-workflow",
        "steps": [_step()] if steps is None else steps,
    }
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# Helper — assert the response is a well-formed JSON error
# ---------------------------------------------------------------------------

def _assert_error_response(response, *, expected_statuses=(400, 422)):
    """Assert status is one of expected_statuses and body is a JSON object."""
    assert response.status_code in expected_statuses, (
        f"Expected one of {expected_statuses}, got {response.status_code}. "
        f"Body: {response.text}"
    )
    assert isinstance(response.json(), dict), (
        f"Expected JSON object body, got: {response.text}"
    )


# ---------------------------------------------------------------------------
# Mock-DB factory for valid-creation tests
# ---------------------------------------------------------------------------

def _make_fake_row(name="edge-case-workflow", schedule_seconds=None, schedule_timezone=None):
    """Return a dict that mimics the DB row the route would insert/fetch."""
    return {
        "id": "test-wf-id-001",
        "name": name,
        "enabled": 1,
        "schedule_seconds": schedule_seconds,
        "schedule_timezone": schedule_timezone,
        "steps_json": json.dumps([_step()]),
        "last_run_at": None,
        "created_at": "2026-01-01T00:00:00",
    }

def _make_mock_db(fake_row):
    """
    Return a mock that behaves as both an awaitable and an async context
    manager, so it works regardless of how get_db is consumed in routes.py.
    """
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=None)
    mock_db.fetchone = AsyncMock(return_value=fake_row)
    mock_db.commit = AsyncMock(return_value=None)
    mock_db.close = AsyncMock(return_value=None)

    # Support ``async with get_db() as db``
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    return mock_db

def _patch_get_db(fake_row):
    """
    Return a patch context manager that makes get_db yield/return mock_db.
    Works for both ``Depends(get_db)`` with an async-generator and a plain
    async function.
    """
    mock_db = _make_mock_db(fake_row)

    @asynccontextmanager
    async def _fake_get_db():
        yield mock_db

    # FastAPI resolves Depends by calling the function.  We replace get_db
    # with an async generator factory so both generator and non-generator
    # call-sites receive the same mock_db object.
    async def _get_db_override():
        return mock_db

    return patch(
        "backend.secuscan.routes.get_db",
        new=_get_db_override,
    )


# ---------------------------------------------------------------------------
# Empty steps — rejected before DB is touched
# ---------------------------------------------------------------------------

class TestEmptySteps:
    """POST /api/v1/workflows with an empty or missing steps field is rejected."""

    def test_empty_steps_list_is_rejected(self, client):
        response = client.post("/api/v1/workflows", json=_payload(steps=[]))
        _assert_error_response(response)

    def test_empty_steps_error_body_is_json_object(self, client):
        response = client.post("/api/v1/workflows", json=_payload(steps=[]))
        assert response.status_code in (400, 422)
        assert isinstance(response.json(), dict)

    def test_missing_steps_field_is_rejected(self, client):
        """Omitting steps entirely is equivalent to an empty list."""
        response = client.post(
            "/api/v1/workflows", json={"name": "no-steps-workflow"}
        )
        _assert_error_response(response)


# ---------------------------------------------------------------------------
# Malformed step payloads — rejected before DB is touched
# ---------------------------------------------------------------------------

class TestMalformedSteps:
    """Steps that are structurally invalid must cause the request to fail."""

    def test_step_missing_plugin_id_is_rejected(self, client):
        bad_step = {"params": {"target": "127.0.0.1"}}
        response = client.post(
            "/api/v1/workflows", json=_payload(steps=[bad_step])
        )
        _assert_error_response(response)

    def test_step_plugin_id_wrong_type_integer_is_rejected(self, client):
        bad_step = {"plugin_id": 42, "params": {}}
        response = client.post(
            "/api/v1/workflows", json=_payload(steps=[bad_step])
        )
        _assert_error_response(response)

    def test_step_is_null_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(steps=[None])
        )
        _assert_error_response(response)

    def test_step_is_bare_string_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(steps=["run_port_scan"])
        )
        _assert_error_response(response)

    def test_steps_value_is_dict_not_list_is_rejected(self, client):
        """The steps field must be a list, not a dict."""
        response = client.post(
            "/api/v1/workflows",
            json=_payload(steps={"plugin_id": "port_scan"}),
        )
        _assert_error_response(response)

    def test_one_malformed_step_among_valid_steps_is_rejected(self, client):
        """A single bad step in an otherwise valid list must still fail."""
        mixed = [
            _step("port_scan"),           # valid
            {"params": {"target": "x"}},  # missing plugin_id
        ]
        response = client.post(
            "/api/v1/workflows", json=_payload(steps=mixed)
        )
        _assert_error_response(response)


# ---------------------------------------------------------------------------
# Invalid schedule_seconds — rejected before DB is touched
# ---------------------------------------------------------------------------

class TestInvalidScheduleSeconds:
    """schedule_seconds must be a positive integer ≥ 1 when supplied."""

    def test_schedule_seconds_zero_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(schedule_seconds=0)
        )
        _assert_error_response(response)

    def test_schedule_seconds_negative_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(schedule_seconds=-60)
        )
        _assert_error_response(response)

    def test_schedule_seconds_string_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(schedule_seconds="daily")
        )
        _assert_error_response(response)

    def test_schedule_seconds_float_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(schedule_seconds=3.14)
        )
        _assert_error_response(response)

    def test_schedule_seconds_list_is_rejected(self, client):
        response = client.post(
            "/api/v1/workflows", json=_payload(schedule_seconds=[60, 120])
        )
        _assert_error_response(response)


# ---------------------------------------------------------------------------
# Valid / boundary schedule_seconds — patch get_db for determinism
# ---------------------------------------------------------------------------

class TestValidScheduleSeconds:
    """Boundary-valid schedule_seconds values (and absence thereof) are accepted."""

    def test_schedule_seconds_omitted_is_accepted(self, client):
        fake_row = _make_fake_row()
        with _patch_get_db(fake_row):
            response = client.post("/api/v1/workflows", json=_payload())
        assert response.status_code in (200, 201), (
            f"Workflow without schedule should be accepted, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_schedule_seconds_null_is_accepted(self, client):
        """Explicitly passing null must be treated the same as omitting it."""
        fake_row = _make_fake_row()
        with _patch_get_db(fake_row):
            response = client.post(
                "/api/v1/workflows", json=_payload(schedule_seconds=None)
            )
        assert response.status_code in (200, 201), (
            f"schedule_seconds=null should be accepted, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_schedule_seconds_minimum_boundary_60_is_accepted(self, client):
        """60 seconds is the minimum meaningful schedule interval."""
        fake_row = _make_fake_row(schedule_seconds=60)
        with _patch_get_db(fake_row):
            response = client.post(
                "/api/v1/workflows", json=_payload(schedule_seconds=60)
            )
        assert response.status_code in (200, 201), (
            f"schedule_seconds=60 should be accepted, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_schedule_seconds_maximum_boundary_86400_is_accepted(self, client):
        """86 400 seconds (24 h) is the maximum allowed schedule interval."""
        fake_row = _make_fake_row(schedule_seconds=86400)
        with _patch_get_db(fake_row):
            response = client.post(
                "/api/v1/workflows", json=_payload(schedule_seconds=86400)
            )
        assert response.status_code in (200, 201), (
            f"schedule_seconds=86400 should be accepted, "
            f"got {response.status_code}. Body: {response.text}"
        )

    def test_valid_creation_response_body_is_json_object(self, client):
        """A successful creation response body must be a JSON object."""
        fake_row = _make_fake_row()
        with _patch_get_db(fake_row):
            response = client.post("/api/v1/workflows", json=_payload())
        assert response.status_code in (200, 201)
        assert isinstance(response.json(), dict), (
            f"Expected JSON object, got: {response.text}"
        )
