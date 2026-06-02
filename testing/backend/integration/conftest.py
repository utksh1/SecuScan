"""
Shared fixtures for integration tests under testing/backend/integration/.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root))

from backend.secuscan.main import app
from backend.secuscan.config import settings
from backend.secuscan import database as db_module
from backend.secuscan import cache as cache_module
from backend.secuscan import auth as auth_module


@pytest_asyncio.fixture
async def async_client():
    """
    Yield an AsyncClient wired to the FastAPI app with:
      - a real isolated temp SQLite DB
      - a real in-memory cache (no Redis needed)
    """
    import tempfile as _tf

    tmp_dir = _tf.TemporaryDirectory()
    tmp_path = tmp_dir.name

    db_path = f"{tmp_path}/test_secuscan.db"
    old_db_path = settings.database_path
    old_data_dir = settings.data_dir
    settings.data_dir = tmp_path
    settings.database_path = db_path

    await cache_module.init_cache()

    test_db = await db_module.init_db(db_path)

    auth_dir = _tf.TemporaryDirectory()
    api_key = auth_module.init_api_key(auth_dir.name)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Api-Key": api_key},
    ) as client:
        client._db = test_db
        client._db_path = db_path
        yield client

    await test_db.disconnect()
    db_module.db = None
    await cache_module.cache.disconnect()
    cache_module.cache = None
    settings.database_path = old_db_path
    settings.data_dir = old_data_dir
    auth_dir.cleanup()
    tmp_dir.cleanup()
