import pytest
from unittest.mock import patch
from backend.secuscan.database import get_db

@pytest.mark.asyncio
async def test_validation_error_request_id_contract(test_client):
    # Case 1: 422 from validation error (missing required field 'plugin_id')
    response = test_client.post("/api/v1/task/start", json={"inputs": {"target": "127.0.0.1"}})
    assert response.status_code == 422

    body = response.json()
    assert "detail" in body
    assert "request_id" in body
    assert isinstance(body["request_id"], str)
    assert len(body["request_id"]) > 0

    # Check headers
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == body["request_id"]

@pytest.mark.asyncio
async def test_http_exception_request_id_contract(test_client):
    # Case 2: 404 from HTTPException (e.g. non-existent task status endpoint)
    response = test_client.get("/api/v1/task/non-existent-task-id-abc/status")
    assert response.status_code == 404

    body = response.json()
    assert "detail" in body
    assert "request_id" in body
    assert isinstance(body["request_id"], str)
    assert len(body["request_id"]) > 0

    # Check headers
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] == body["request_id"]

@pytest.mark.asyncio
async def test_report_generation_error_request_id_contract(test_client):
    # Case 3: 500 report generation error helper payload
    db = await get_db()
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, status, consent_granted, safe_mode, owner_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("test-task-999", "nmap", "nmap", "127.0.0.1", '{"target":"127.0.0.1"}', "completed", 1, 1, "default")
    )

    with patch("backend.secuscan.reporting.reporting.generate_csv_report", side_effect=Exception("Simulated report failure")):
        response = test_client.get("/api/v1/task/test-task-999/report/csv")
        assert response.status_code == 500

        body = response.json()
        assert body["error"] == "report_generation_failed"
        assert "request_id" in body
        assert isinstance(body["request_id"], str)
        assert len(body["request_id"]) > 0

        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == body["request_id"]

@pytest.mark.asyncio
async def test_client_supplied_request_id_contract(test_client):
    # Case 4: Round-tripping a client-supplied X-Request-ID
    client_request_id = "test-client-req-id-12345"
    response = test_client.get(
        "/api/v1/task/non-existent-task-id-xyz/status",
        headers={"X-Request-ID": client_request_id}
    )
    assert response.status_code == 404

    body = response.json()
    assert "detail" in body
    assert body["request_id"] == client_request_id

    assert response.headers["X-Request-ID"] == client_request_id
