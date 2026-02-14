import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add repo root to sys.path so package imports work (backend.*)
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from backend.secuscan.config import settings
from backend.secuscan import database as database_module
from backend.secuscan.database import init_db
from backend.secuscan.main import app
from backend.secuscan.plugins import init_plugins


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Override settings for tests to ensure isolated execution."""
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = temp_dir.name

    monkeypatch.setattr(settings, "data_dir", temp_path)
    monkeypatch.setattr(settings, "raw_output_dir", f"{temp_path}/raw")
    monkeypatch.setattr(settings, "reports_dir", f"{temp_path}/reports")
    monkeypatch.setattr(settings, "plugins_dir", str(Path(__file__).parent.parent / "plugins"))
    monkeypatch.setattr(settings, "database_path", f"{temp_path}/test_secuscan.db")

    settings.ensure_directories()

    yield temp_path

    temp_dir.cleanup()


@pytest.fixture
def test_client(setup_test_environment):
    """Provides a synchronous test client backed by initialized async services."""
    import asyncio

    async def setup():
        await init_db(settings.database_path)
        await init_plugins(settings.plugins_dir)

    asyncio.run(setup())

    with TestClient(app) as client:
        yield client

    if database_module.db:
        asyncio.run(database_module.db.disconnect())
