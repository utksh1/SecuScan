"""Test CORS configuration in Docker Compose setup.

Validates that the backend correctly configures CORS allowed origins
from environment variables when running in Docker Compose.
"""

import os
import pytest


def test_cors_origins_from_env():
    """Verify CORS origins are correctly configured from env var."""
    # This simulates the Docker Compose environment
    os.environ["SECUSCAN_CORS_ALLOWED_ORIGINS"] = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:8080,"
        "http://127.0.0.1:8080"
    )

    # Import after env var is set
    from secuscan.config import Settings

    settings = Settings()
    cors_origins = settings.cors_allowed_origins

    expected = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    assert cors_origins == expected


def test_no_docker_service_names_in_cors():
    """Ensure Docker service names (http://frontend:5173) are not in CORS origins.

    Docker service names are internal to the container network and cannot be
    used by browsers. Only browser-accessible origins should be allowed.
    """
    os.environ["SECUSCAN_CORS_ALLOWED_ORIGINS"] = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:8080,"
        "http://127.0.0.1:8080"
    )

    from secuscan.config import Settings

    settings = Settings()
    cors_origins = settings.cors_allowed_origins

    # Verify no Docker service names are in the list
    assert "http://frontend:5173" not in cors_origins
    assert "http://api:8081" not in cors_origins
    assert "http://postgres:5432" not in cors_origins
    assert "http://redis:6379" not in cors_origins
