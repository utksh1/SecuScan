"""
Tests for standardized API error responses.
Ensures all core endpoints return machine-readable problem details.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from secuscan.errors import (
    http_exception_handler,
    validation_exception_handler,
    problem,
)


# ── Unit tests for problem() helper ──────────────────────────────────────────

def test_problem_required_fields():
    p = problem(status=404, code="NOT_FOUND", message="Resource missing")
    assert p["code"] == "NOT_FOUND"
    assert p["message"] == "Resource missing"
    assert p["status"] == 404
    assert "request_id" in p


def test_problem_optional_fields():
    p = problem(
        status=400,
        code="BAD_REQUEST",
        message="Bad input",
        field="target",
        hint="Check the value",
        details={"extra": "info"},
        request_id="test-id-123",
    )
    assert p["field"] == "target"
    assert p["hint"] == "Check the value"
    assert p["details"] == {"extra": "info"}
    assert p["request_id"] == "test-id-123"


def test_problem_no_field_when_none():
    p = problem(status=500, code="INTERNAL_ERROR", message="Oops")
    assert "field" not in p


# ── Integration tests using TestClient ───────────────────────────────────────

@pytest.fixture
def test_app():
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)

    @app.get("/not-found")
    async def not_found():
        raise HTTPException(status_code=404, detail="Task not found")

    @app.get("/unauthorized")
    async def unauthorized():
        raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/conflict")
    async def conflict():
        raise HTTPException(status_code=409, detail="Already exists")

    @app.get("/rate-limited")
    async def rate_limited():
        raise HTTPException(status_code=429, detail="Too many requests")

    @app.get("/server-error")
    async def server_error():
        raise HTTPException(status_code=500, detail="Something broke")

    return TestClient(app)


def test_404_returns_problem_details(test_app):
    res = test_app.get("/not-found")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert body["status"] == 404
    assert "request_id" in body
    assert "hint" in body


def test_401_returns_problem_details(test_app):
    res = test_app.get("/unauthorized")
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == "UNAUTHORIZED"
    assert "hint" in body


def test_409_returns_problem_details(test_app):
    res = test_app.get("/conflict")
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "CONFLICT"


def test_429_returns_problem_details(test_app):
    res = test_app.get("/rate-limited")
    assert res.status_code == 429
    body = res.json()
    assert body["code"] == "RATE_LIMITED"


def test_500_returns_problem_details(test_app):
    res = test_app.get("/server-error")
    assert res.status_code == 500
    body = res.json()
    assert body["code"] == "INTERNAL_ERROR"


def test_no_legacy_string_only_error(test_app):
    """Ensure responses never return plain string 'detail' field."""
    res = test_app.get("/not-found")
    body = res.json()
    assert "detail" not in body
    assert "code" in body
    assert "message" in body