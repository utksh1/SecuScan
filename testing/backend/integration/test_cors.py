def test_cors_preflight_allows_local_frontend_origin(test_client):
    origin = "http://localhost:5173"
    response = test_client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_allows_preview_origin(test_client):
    origin = "http://localhost:8080"
    response = test_client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

def test_cors_rejects_missing_origin(test_client):
    response = test_client.get("/api/v1/health")

    assert response.status_code == 403
    assert response.json()["success"] is False
    assert "Missing Origin header" in response.json()["message"]


def test_cors_allows_docs_without_origin(test_client):
    # Documentation endpoints should still be accessible without Origin header
    # (e.g. by directly opening in browser)
    for path in ["/docs", "/redoc", "/openapi.json"]:
        response = test_client.get(path)
        assert response.status_code == 200
