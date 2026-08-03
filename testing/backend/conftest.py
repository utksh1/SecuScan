import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Add repo root to sys.path so package imports work (backend.*)
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from backend.secuscan.config import settings
from backend.secuscan import database as database_module
from backend.secuscan.database import init_db
from backend.secuscan.main import app
from backend.secuscan.plugins import init_plugins
from backend.secuscan.ratelimit import concurrent_limiter, rate_limiter
from backend.secuscan import auth as auth_module


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Override settings for tests to ensure isolated execution."""
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    temp_path = temp_dir.name

    monkeypatch.setattr(settings, "data_dir", temp_path)
    monkeypatch.setattr(settings, "raw_output_dir", f"{temp_path}/raw")
    monkeypatch.setattr(settings, "reports_dir", f"{temp_path}/reports")
    monkeypatch.setattr(settings, "plugins_dir", str(repo_root / "plugins"))
    monkeypatch.setattr(settings, "database_path", f"{temp_path}/test_secuscan.db")
    monkeypatch.setattr(settings, "vault_key", "test-vault-key-for-unit-tests-only")
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    # Disable network policy enforcement in tests: integration tests mock
    # _execute_command but the policy check runs before that mock fires.
    # Tests that specifically test policy behaviour override this themselves.
    monkeypatch.setattr(settings, "enforce_network_policy", False)
    # Disable scan rate limiter in tests to avoid 429 interference
    monkeypatch.setattr(settings, "scan_rate_limit", 0)

    settings.ensure_directories()

    yield temp_path

    temp_dir.cleanup()

@pytest.fixture
def anyio_backend():
    """Force AnyIO tests to run on asyncio (trio is not a dependency in CI)."""
    return "asyncio"



@pytest.fixture
def test_client(setup_test_environment):
    """Provides a synchronous test client backed by initialized async services."""
    import asyncio

    async def setup():
        await rate_limiter.reset()
        async with concurrent_limiter.lock:
            concurrent_limiter.running_tasks.clear()
        try:
            from backend.secuscan.ratelimit import reset_all_endpoint_limiters
            await reset_all_endpoint_limiters()
        except ImportError:
            pass
        scan_limiter = getattr(app.state, "scan_rate_limiter", None)
        if scan_limiter:
            scan_limiter._rate_limit = 0
            await scan_limiter.reset()
        await init_db(settings.database_path)
        await init_plugins(settings.plugins_dir)

    asyncio.run(setup())

    api_key = auth_module.init_api_key(settings.data_dir)

    with TestClient(app, headers={"X-Api-Key": api_key}) as client:
        yield client

    async def teardown():
        await rate_limiter.reset()
        async with concurrent_limiter.lock:
            concurrent_limiter.running_tasks.clear()
        try:
            from backend.secuscan.ratelimit import reset_all_endpoint_limiters
            await reset_all_endpoint_limiters()
        except ImportError:
            pass
        scan_limiter = getattr(app.state, "scan_rate_limiter", None)
        if scan_limiter:
            scan_limiter._rate_limit = 0
            await scan_limiter.reset()
        if database_module.db:
            await database_module.db.disconnect()

    asyncio.run(teardown())
