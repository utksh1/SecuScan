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


def test_cors_security_no_wildcard_with_credentials(test_client):
    """Access-Control-Allow-Origin must never be * when credentials are enabled."""
    routes = ["/api/v1/health", "/api/v1/tasks", "/api/v1/findings"]
    for route in routes:
        response = test_client.options(
            route,
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        origin_header = response.headers.get("access-control-allow-origin", "")
        assert origin_header != "*", f"Route {route} returned wildcard with credentials enabled"


def test_cors_rejects_non_whitelisted_origin(test_client):
    """Non-whitelisted origins must not have their origin echoed as CORS header."""
    origin = "https://untrusted-origin.com"
    response = test_client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    cors_origin = response.headers.get("access-control-allow-origin")
    assert cors_origin != origin


def test_cors_actual_request_has_credentials(test_client):
    """Actual (non-preflight) requests should also carry CORS headers."""
    origin = "http://localhost:5173"
    response = test_client.get(
        "/api/v1/health",
        headers={"Origin": origin},
    )
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
