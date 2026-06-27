"""
Unit tests for cache module-level functions in backend/secuscan/cache.py.

Covers:
- init_cache: initialises the global cache instance
- get_cache: returns the global cache instance
- invalidate_view_cache: clears caches with view-related prefixes
- invalidate_plugin_caches: clears caches with plugin-related prefixes

CacheClient itself is already tested in test_cache_helpers.py.
This file tests ONLY the module-level functions.
"""

import asyncio
import pytest

from backend.secuscan.cache import (
    get_cache,
    init_cache,
    invalidate_plugin_caches,
    invalidate_view_cache,
)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# init_cache
# ---------------------------------------------------------------------------


class TestInitCache:
    def test_returns_cache_client(self):
        cache = _run(init_cache())
        from backend.secuscan.cache import CacheClient
        assert isinstance(cache, CacheClient)

    def test_sets_global_cache(self):
        _run(init_cache())
        cache = _run(get_cache())
        assert cache is not None

    def test_replaces_existing_global_instance(self):
        first = _run(init_cache())
        second = _run(init_cache())
        from backend.secuscan.cache import CacheClient
        assert isinstance(first, CacheClient)
        assert isinstance(second, CacheClient)
        # init_cache replaces the global each time
        assert first is not second


# ---------------------------------------------------------------------------
# get_cache
# ---------------------------------------------------------------------------


class TestGetCache:
    def test_returns_initialised_cache(self):
        _run(init_cache())
        cache = _run(get_cache())
        from backend.secuscan.cache import CacheClient
        assert isinstance(cache, CacheClient)

    def test_raises_when_not_initialised(self):
        import backend.secuscan.cache as cache_module
        cache_module.cache = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                _run(get_cache())
        finally:
            cache_module.cache = None


# ---------------------------------------------------------------------------
# invalidate_view_cache
# ---------------------------------------------------------------------------


class TestInvalidateViewCache:
    def test_noop_when_cache_not_initialised(self):
        import backend.secuscan.cache as cache_module
        cache_module.cache = None
        # Should not raise
        _run(invalidate_view_cache())

    def test_deletes_view_prefixes(self):
        import backend.secuscan.cache as cache_module
        cache = _run(init_cache())
        deleted_prefixes = []
        original_delete_prefix = cache.delete_prefix

        async def tracking_delete_prefix(prefix: str):
            deleted_prefixes.append(prefix)
            return await original_delete_prefix(prefix)

        cache.delete_prefix = tracking_delete_prefix
        cache_module.cache = cache

        _run(invalidate_view_cache())

        expected = ["summary:", "findings:", "reports:", "tasks:"]
        assert sorted(deleted_prefixes) == sorted(expected)


# ---------------------------------------------------------------------------
# invalidate_plugin_caches
# ---------------------------------------------------------------------------


class TestInvalidatePluginCaches:
    def test_noop_when_cache_not_initialised(self):
        import backend.secuscan.cache as cache_module
        cache_module.cache = None
        # Should not raise
        _run(invalidate_plugin_caches())

    def test_deletes_plugin_prefixes(self):
        import backend.secuscan.cache as cache_module
        cache = _run(init_cache())
        deleted_prefixes = []
        original_delete_prefix = cache.delete_prefix

        async def tracking_delete_prefix(prefix: str):
            deleted_prefixes.append(prefix)
            return await original_delete_prefix(prefix)

        cache.delete_prefix = tracking_delete_prefix
        cache_module.cache = cache

        _run(invalidate_plugin_caches())

        expected = ["summary:", "plugins:"]
        assert sorted(deleted_prefixes) == sorted(expected)
