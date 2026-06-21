"""
conftest.py - Unit test configuration for backend/secuscan.

Uses --noconftest when running locally (see cron prompt).
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def isolated_cache_settings():
    """
    Replace backend.secuscan.cache.settings with a fresh mock so tests that call
    set_json(..., ttl=None) get a deterministic TTL without touching the global
    settings singleton at all.
    """
    from backend.secuscan import cache as cache_module

    original = cache_module.settings
    mock_settings = MagicMock()
    mock_settings.cache_ttl_seconds = 60
    cache_module.settings = mock_settings
    yield
    cache_module.settings = original
