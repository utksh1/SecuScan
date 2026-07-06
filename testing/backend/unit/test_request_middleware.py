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

    def test_very_long_request_id_is_preserved(self):
        with TestClient(app) as client:
            long_id = "x" * 512
            response = client.get(
                "/api/v1/health",
                headers={"X-Request-ID": long_id},
            )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == long_id


class TestRequestIDMiddlewareEdgeCases:
    """Edge case tests for RequestIDMiddleware covering special characters and concurrency."""

    def test_special_characters_in_request_id_are_preserved(self):
        """Special characters in X-Request-ID header should be preserved in response."""
        special_ids = [
            "req-with-dash_underscore.dot",
            "req/with/slashes",
            "req;with;semicolons",
            'req"with"quotes',
            "req with spaces",
        ]
        for special_id in special_ids:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/health",
                    headers={"X-Request-ID": special_id},
                )

            assert response.status_code == 200
            assert response.headers["X-Request-ID"] == special_id

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
