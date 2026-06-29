from fastapi.testclient import TestClient

from backend.secuscan.main import app


class TestRequestIDMiddleware:
    def test_preserves_existing_request_id(self):
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/health",
                headers={"X-Request-ID": "test-request-123"},
            )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "test-request-123"

    def test_generates_request_id_when_missing(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"]

    def test_response_always_contains_request_id_header(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_empty_request_id_header_is_preserved(self):
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/health",
                headers={"X-Request-ID": ""},
            )

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_generated_request_id_is_uuid_format(self):
        import uuid
        with TestClient(app) as client:
            response = client.get("/api/v1/health")

        rid = response.headers["X-Request-ID"]
        try:
            uuid.UUID(rid)
        except ValueError:
            raise AssertionError(f"Expected UUID format, got: {rid}")

    def test_very_long_request_id_is_preserved(self):
        with TestClient(app) as client:
            long_id = "x" * 512
            response = client.get(
                "/api/v1/health",
                headers={"X-Request-ID": long_id},
            )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == long_id
