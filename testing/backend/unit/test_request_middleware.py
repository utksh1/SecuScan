from fastapi.testclient import TestClient
import concurrent.futures

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

    def test_very_long_request_id_is_rejected(self):
        with TestClient(app) as client:
            long_id = "x" * 512
            response = client.get(
                "/api/v1/health",
                headers={"X-Request-ID": long_id},
            )

        assert response.status_code == 200
        # Oversized ID should be replaced with a generated UUID
        assert response.headers["X-Request-ID"] != long_id
        assert response.headers["X-Request-ID"]


class TestRequestIDMiddlewareEdgeCases:
    """Edge case tests for RequestIDMiddleware covering special characters and concurrency."""

    def test_malicious_request_ids_are_rejected(self):
        """Malformed X-Request-ID values with dangerous chars should be rejected."""
        malicious_ids = [
            "req/with/slashes",
            "req;with;semicolons",
            'req"with"quotes',
            "req with spaces",
        ]
        for malicious_id in malicious_ids:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/health",
                    headers={"X-Request-ID": malicious_id},
                )

            assert response.status_code == 200
            # Malicious ID should be replaced with a safe UUID
            assert response.headers["X-Request-ID"] != malicious_id
            assert response.headers["X-Request-ID"]

    def test_valid_request_ids_are_preserved(self):
        """Valid alphanumeric request IDs with hyphens/underscores should be preserved."""
        valid_ids = [
            "req-with-dash_underscore",
            "abc123",
            "550e8400-e29b-41d4-a716-446655440000",
        ]
        for valid_id in valid_ids:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/health",
                    headers={"X-Request-ID": valid_id},
                )

            assert response.status_code == 200
            assert response.headers["X-Request-ID"] == valid_id

    def test_concurrent_requests_get_isolated_request_ids(self):
        """Two concurrent threads should each get an isolated request ID via ContextVar."""
        import uuid
        from backend.secuscan.request_context import get_request_id, set_request_id
        from concurrent.futures import ThreadPoolExecutor

        def thread_work():
            set_request_id()
            import time
            time.sleep(0.01)  # yield to other thread
            return get_request_id()

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(thread_work)
            future2 = executor.submit(thread_work)
            id1 = future1.result()
            id2 = future2.result()

        assert id1 is not None
        assert id2 is not None
        # Both should be valid UUIDs
        uuid.UUID(id1)
        uuid.UUID(id2)
        # And they should be different (isolated contexts)
        assert id1 != id2
