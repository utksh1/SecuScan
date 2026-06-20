import pytest
from unittest.mock import patch


def test_request_id_present_on_success(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != ""


def test_request_id_echoed_when_provided(test_client):
    response = test_client.get(
        "/api/v1/health", headers={"X-Request-ID": "my-trace-id"}
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "my-trace-id"


def test_request_id_present_on_404(test_client):
    response = test_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != ""
    # Verify JSON shape
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Not Found"


def test_request_id_present_on_422(test_client):
    # POST with missing required fields triggers 422 validation error
    response = test_client.post("/api/v1/task/start", json={})
    assert response.status_code == 422
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != ""
    # Verify JSON shape
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json()["detail"], list)


def test_request_id_present_on_unhandled_exception(test_client):
    # Force an unhandled exception in a route handler by mocking platform.system.
    # We create a local TestClient with raise_exceptions=False to ensure our
    # global exception handler is exercised instead of Starlette re-raising.
    from fastapi.testclient import TestClient
    from backend.secuscan.main import app
    from backend.secuscan import auth as auth_module
    from backend.secuscan.config import settings

    api_key = auth_module.init_api_key(settings.data_dir)
    client = TestClient(
        app, headers={"X-Api-Key": api_key}, raise_server_exceptions=False
    )

    with patch("platform.system", side_effect=RuntimeError("boom")):
        response = client.get("/api/v1/health")
        assert response.status_code == 500
        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] != ""

        # Verify shape and header matches standard Starlette ServerErrorMiddleware
        if settings.debug:
            assert "text/html" in response.headers["content-type"]
            assert "500 Internal Server Error" in response.text
        else:
            assert "text/plain" in response.headers["content-type"]
            assert response.text == "Internal Server Error"


def test_request_id_is_consistent_across_same_request(test_client):
    # The ID in the response header should match what was set on the request state.
    custom_id = "consistency-check-id"
    response = test_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id
