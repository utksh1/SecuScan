"""
Unit tests for cache module-level helper functions in backend.secuscan.cache.

Covers:
- init_cache: initialises the global cache instance
- get_cache: returns the global cache instance
- invalidate_view_cache: clears caches with view-related prefixes
- invalidate_plugin_caches: clears caches with plugin-related prefixes

The CacheClient itself is tested in test_cache_helpers.py.
This file tests ONLY the module-level functions.
"""

from __future__ import annotations

import pytest

from backend.secuscan.cache import init_cache, get_cache


class TestInitCache:
    def test_init_cache_returns_cache_client(self):
        """init_cache returns a CacheClient instance."""
        import backend.secuscan.cache as cache_module
        original = getattr(cache_module, "cache", None)
        try:
            result = init_cache(":memory:")
            from backend.secuscan.cache import CacheClient
            assert isinstance(result, CacheClient)
        finally:
            if original is not None:
                cache_module.cache = original

    def test_sets_global_cache_instance(self):
        """init_cache sets the module-level cache global."""
        import backend.secuscan.cache as cache_module
        original = getattr(cache_module, "cache", None)
        try:
            client = init_cache(":memory:")
            assert cache_module.cache is client
        finally:
            if original is not None:
                cache_module.cache = original


class TestGetCache:
    def test_returns_global_cache_instance(self):
        """get_cache returns the module-level cache."""
        import backend.secuscan.cache as cache_module
        original = getattr(cache_module, "cache", None)
        try:
            client = init_cache(":memory:")
            cache_module.cache = client
            result = get_cache()
            assert result is client
        finally:
            if original is not None:
                cache_module.cache = original


class TestInvalidateViewCache:
    async def _make_view_cache(self):
        """Create a cache with view-related keys."""
        import backend.secuscan.cache as cache_module
        original = getattr(cache_module, "cache", None)
        client = init_cache(":memory:")
        cache_module.cache = client
        # Add view-related cache entries
        await client.set_json("view:dashboard", {"data": "dash"}, ttl=3600)
        await client.set_json("view:findings", {"data": "findings"}, ttl=3600)
        await client.set_json("plugin:nmap", {"data": "nmap"}, ttl=3600)
        try:
            yield client
        finally:
            if original is not None:
                cache_module.cache = original

    @pytest.mark.asyncio
    async def test_invalidate_view_cache_removes_view_keys(self):
        """invalidate_view_cache removes keys with view: prefix."""
        import backend.secuscan.cache as cache_module
        from backend.secuscan.cache import invalidate_view_cache

        original = getattr(cache_module, "cache", None)
        client = init_cache(":memory:")
        cache_module.cache = client
        await client.set_json("view:dashboard", {"data": "dash"}, ttl=3600)
        await client.set_json("view:findings", {"data": "findings"}, ttl=3600)
        await client.set_json("plugin:nmap", {"data": "nmap"}, ttl=3600)
        try:
            await invalidate_view_cache()
            r1 = await client.get_json("view:dashboard")
            r2 = await client.get_json("view:findings")
            r3 = await client.get_json("plugin:nmap")
            assert r1 is None, "view:dashboard should be cleared"
            assert r2 is None, "view:findings should be cleared"
            assert r3 is not None, "plugin:nmap should NOT be cleared"
        finally:
            if original is not None:
                cache_module.cache = original


class TestInvalidatePluginCaches:
    @pytest.mark.asyncio
    async def test_invalidate_plugin_caches_removes_plugin_keys(self):
        """invalidate_plugin_caches removes keys with plugin: prefix."""
        import backend.secuscan.cache as cache_module
        from backend.secuscan.cache import invalidate_plugin_caches

        original = getattr(cache_module, "cache", None)
        client = init_cache(":memory:")
        cache_module.cache = client
        await client.set_json("plugin:nmap", {"data": "nmap"}, ttl=3600)
        await client.set_json("plugin:sqlmap", {"data": "sqlmap"}, ttl=3600)
        await client.set_json("view:dashboard", {"data": "dash"}, ttl=3600)
        try:
            await invalidate_plugin_caches()
            r1 = await client.get_json("plugin:nmap")
            r2 = await client.get_json("plugin:sqlmap")
            r3 = await client.get_json("view:dashboard")
            assert r1 is None, "plugin:nmap should be cleared"
            assert r2 is None, "plugin:sqlmap should be cleared"
            assert r3 is not None, "view:dashboard should NOT be cleared"
        finally:
            if original is not None:
                cache_module.cache = original

    @pytest.mark.asyncio
    async def test_invalidate_plugin_caches_no_plugin_keys_no_effect(self):
        """When no plugin keys exist, the function is a no-op."""
        import backend.secuscan.cache as cache_module
        from backend.secuscan.cache import invalidate_plugin_caches

        original = getattr(cache_module, "cache", None)
        client = init_cache(":memory:")
        cache_module.cache = client
        await client.set_json("view:dashboard", {"data": "dash"}, ttl=3600)
        try:
            # Should not raise
            await invalidate_plugin_caches()
            r = await client.get_json("view:dashboard")
            assert r is not None, "view:dashboard should remain"
        finally:
            if original is not None:
                cache_module.cache = original
