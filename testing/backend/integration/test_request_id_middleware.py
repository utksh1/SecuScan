import pytest
from unittest.mock import patch

def test_request_id_present_on_success(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != ""

def test_request_id_echoed_when_provided(test_client):
    response = test_client.get("/api/v1/health", headers={"X-Request-ID": "my-trace-id"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "my-trace-id"

def test_request_id_present_on_404(test_client):
    response = test_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != ""

def test_request_id_present_on_422(test_client):
    # POST with missing required fields triggers 422 validation error
    response = test_client.post("/api/v1/task/start", json={})
    assert response.status_code == 422
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"] != ""

def test_request_id_present_on_unhandled_exception(test_client):
    # Force an unhandled exception in a route handler by mocking platform.system
    with patch("platform.system", side_effect=RuntimeError("boom")):
        response = test_client.get("/api/v1/health")
        assert response.status_code == 500
        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] != ""

def test_request_id_is_consistent_across_same_request(test_client):
    # The ID in the response header should match what was set on the request state.
    custom_id = "consistency-check-id"
    response = test_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id
