"""
Route-level validation tests for POST /api/v1/task/start.

Run with:
    python -m pytest testing/backend/unit/test_routes_validation.py -v

These tests exercise the validation path in start_task() using the FastAPI
test client with fully mocked dependencies, so no real database, executor,
or plugin infrastructure is required.
"""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin(category: str = "network") -> MagicMock:
    plugin = MagicMock()
    plugin.category = category
    plugin.safety = {}
    plugin.presets = {}
    return plugin


def _make_plugin_manager(plugin: Optional[MagicMock] = None) -> MagicMock:
    pm = MagicMock()
    pm.get_plugin.return_value = plugin
    pm.list_plugins.return_value = []
    pm.get_plugin_schema.return_value = None
    pm.plugins = {}
    return pm


class _FakeSettings:
    require_consent: bool = False
    safe_mode_default: bool = True
    max_tasks_per_hour: int = 100
    debug: bool = False
    plugins_dir: str = "/tmp/plugins"
    data_dir: str = "/tmp/data"
    docker_enabled: bool = False
    sandbox_timeout: int = 300
    sandbox_cpu_quota: int = 50000
    sandbox_memory_mb: int = 512
    bind_address: str = "127.0.0.1"
    bind_port: int = 8080
    allowed_networks: list = []
    resolved_vault_key: str = "test-key"


_SETTINGS = _FakeSettings()


def _build_app(
    *,
    plugin: Optional[MagicMock] = None,
    validate_result: tuple = (True, None, None),
    task_id: str = "task-abc-123",
) -> FastAPI:
    """Build a minimal FastAPI app with the routes module and all deps mocked."""
    app = FastAPI()

    fake_cache = AsyncMock()
    fake_cache.get_json.return_value = None
    fake_cache.set_json.return_value = None
    fake_cache.delete_prefix.return_value = None

    async def _get_cache():
        return fake_cache

    fake_rate_limiter = AsyncMock()
    fake_rate_limiter.can_execute.return_value = (True, None)

    fake_concurrent_limiter = AsyncMock()
    fake_concurrent_limiter.acquire.return_value = (True, None)
    fake_concurrent_limiter.release.return_value = None

    fake_executor = AsyncMock()
    fake_executor.create_task.return_value = task_id
    fake_executor.execute_task = AsyncMock()
    fake_executor.get_task_status.return_value = None
    fake_executor.subscribe.return_value = asyncio.Queue()
    fake_executor.unsubscribe.return_value = None
    fake_executor.cancel_task.return_value = False

    effective_plugin = plugin if plugin is not None else _make_plugin()
    fake_pm = _make_plugin_manager(effective_plugin)

    async def _get_plugin_manager_for_request():
        return fake_pm

    def _sanitize_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return dict(inputs)

    def _extract_target(inputs: Dict[str, Any]) -> Optional[str]:
        return inputs.get("target") or inputs.get("url") or inputs.get("host")

    def _validate_task_inputs(inputs, *, safe_mode=True):
        is_valid, error_msg, updated = validate_result
        return (is_valid, error_msg, updated if updated is not None else inputs)

    patches = [
        patch("backend.secuscan.routes.settings", _SETTINGS),
        patch("backend.secuscan.routes.get_cache", _get_cache),
        patch("backend.secuscan.routes.rate_limiter", fake_rate_limiter),
        patch("backend.secuscan.routes.concurrent_limiter", fake_concurrent_limiter),
        patch("backend.secuscan.routes.executor", fake_executor),
        patch("backend.secuscan.routes.get_plugin_manager_for_request", _get_plugin_manager_for_request),
        patch("backend.secuscan.routes.sanitize_inputs", side_effect=_sanitize_inputs),
        patch("backend.secuscan.routes.extract_target_from_inputs", side_effect=_extract_target),
        patch("backend.secuscan.routes.validate_task_inputs", side_effect=_validate_task_inputs),
        patch("backend.secuscan.routes.get_db", AsyncMock()),
    ]

    for p in patches:
        p.start()
        app.state.patches = getattr(app.state, "patches", []) + [p]

    from backend.secuscan import routes
    app.include_router(routes.router)

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_PAYLOAD: Dict[str, Any] = {
    "plugin_id": "nmap",
    "inputs": {"target": "192.168.1.1"},
    "preset": None,
    "consent_granted": True,
}


@pytest.fixture()
def client_accept():
    """Valid private target — validation passes."""
    app = _build_app(
        plugin=_make_plugin(category="network"),
        validate_result=(True, None, {"target": "192.168.1.1"}),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in getattr(app.state, "patches", []):
        p.stop()


@pytest.fixture()
def client_reject_public():
    """Public IP target — validation fails in safe_mode."""
    app = _build_app(
        plugin=_make_plugin(category="network"),
        validate_result=(False, "Target '8.8.8.8' is not allowed in safe mode", None),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in getattr(app.state, "patches", []):
        p.stop()


@pytest.fixture()
def client_reject_malformed():
    """Malformed hostname — validation fails."""
    app = _build_app(
        plugin=_make_plugin(category="network"),
        validate_result=(False, "Invalid target: hostname could not be resolved", None),
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    for p in getattr(app.state, "patches", []):
        p.stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStartTaskValidation:
    """Route-level tests for POST /api/v1/task/start."""

    def test_private_ip_target_accepted(self, client_accept):
        payload = {**BASE_PAYLOAD, "inputs": {"target": "192.168.1.1"}}
        resp = client_accept.post("/api/v1/task/start", json=payload)

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "queued"

    def test_public_ip_rejected_in_safe_mode(self, client_reject_public):
        payload = {**BASE_PAYLOAD, "inputs": {"target": "8.8.8.8"}}
        resp = client_reject_public.post("/api/v1/task/start", json=payload)

        assert resp.status_code == 400, resp.text

    def test_malformed_hostname_rejected(self, client_reject_malformed):
        payload = {**BASE_PAYLOAD, "inputs": {"target": "not_a_valid_host!!!"}}
        resp = client_reject_malformed.post("/api/v1/task/start", json=payload)

        assert resp.status_code == 400, resp.text

    def test_validation_error_has_detail_key(self, client_reject_public):
        payload = {**BASE_PAYLOAD, "inputs": {"target": "8.8.8.8"}}
        resp = client_reject_public.post("/api/v1/task/start", json=payload)

        assert "detail" in resp.json()