"""
Static validation for the docker-compose CORS configuration (issue #1622).

The frontend service (port 5173) and API service (port 8081) can each be
reached through several origins depending on how the stack is accessed --
localhost, 127.0.0.1, or the Docker-internal service DNS name. Without an
explicit SECUSCAN_CORS_ALLOWED_ORIGINS entry on the `api` service, the
backend's CORS middleware rejects requests from the frontend container.
These tests parse docker-compose.yml directly, so they run without Docker.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"

REQUIRED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://frontend:5173",
}


def _load_compose() -> dict:
    assert COMPOSE_PATH.exists(), f"docker-compose.yml not found at {COMPOSE_PATH}"
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)


def _service_env_as_dict(service: dict) -> dict:
    """Normalize a compose service's `environment` key to a dict.

    docker-compose supports both list form (`KEY=VALUE` strings) and
    mapping form (`KEY: VALUE`) -- normalize to a dict either way.
    """
    env = service.get("environment") or []
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items()}
    result = {}
    for entry in env:
        if "=" not in entry:
            continue
        key, _, value = entry.partition("=")
        result[key] = value
    return result


def test_api_service_defines_cors_allowed_origins():
    compose = _load_compose()
    api_service = compose.get("services", {}).get("api")
    assert api_service is not None, "docker-compose.yml has no 'api' service"

    env = _service_env_as_dict(api_service)
    assert "SECUSCAN_CORS_ALLOWED_ORIGINS" in env, (
        "api service must set SECUSCAN_CORS_ALLOWED_ORIGINS so the frontend "
        "container can call the API -- without it, the backend's CORS "
        "middleware rejects every frontend request."
    )


def test_cors_allowed_origins_cover_all_frontend_access_paths():
    compose = _load_compose()
    api_service = compose["services"]["api"]
    env = _service_env_as_dict(api_service)

    configured = {
        origin.strip()
        for origin in env["SECUSCAN_CORS_ALLOWED_ORIGINS"].split(",")
        if origin.strip()
    }

    missing = REQUIRED_ORIGINS - configured
    assert not missing, (
        f"SECUSCAN_CORS_ALLOWED_ORIGINS is missing required origin(s): {sorted(missing)}. "
        "The frontend must be reachable via localhost, 127.0.0.1, and the "
        "Docker-internal 'frontend' service DNS name."
    )
