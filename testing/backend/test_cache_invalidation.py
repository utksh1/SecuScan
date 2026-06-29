"""
Cache invalidation tests
"""

import pytest
from unittest.mock import AsyncMock, patch

class TestInvalidateViewCache:
    """Test the cache invalidation helper functions"""

    @pytest.mark.asyncio
    async def test_invalidate_view_cache_clears_prefixes(self):
        """Test that invalidate_view_cache clears all required prefixes"""
        from backend.secuscan.cache import invalidate_view_cache

        mock_cache = AsyncMock()
        with patch("backend.secuscan.cache.get_cache", return_value=mock_cache):
            await invalidate_view_cache()

        expected_prefixes = ["summary:", "findings:", "reports:", "tasks:"]
        for prefix in expected_prefixes:
            mock_cache.delete_prefix.assert_any_call(prefix)
        assert mock_cache.delete_prefix.call_count == len(expected_prefixes)

    @pytest.mark.asyncio
    async def test_invalidate_plugin_caches_clears_prefixes(self):
        """Test that invalidate_plugin_caches clears plugin and dashboard prefixes"""
        from backend.secuscan.cache import invalidate_plugin_caches

        mock_cache = AsyncMock()
        with patch("backend.secuscan.cache.get_cache", return_value=mock_cache):
            await invalidate_plugin_caches()

        expected_prefixes = ["summary:", "plugins:"]
        for prefix in expected_prefixes:
            mock_cache.delete_prefix.assert_any_call(prefix)
        assert mock_cache.delete_prefix.call_count == len(expected_prefixes)

    def test_function_exists(self):
        """Test that invalidate_view_cache function exists in routes (backwards compatibility)"""
        from backend.secuscan.routes import invalidate_view_cache
        assert callable(invalidate_view_cache)

    @pytest.mark.asyncio
    async def test_load_plugins_invalidates_cache(self, tmp_path):
        """Test that loading plugins automatically invalidates the plugin cache."""
        from backend.secuscan.plugins import PluginManager

        manager = PluginManager(str(tmp_path))
        with patch("backend.secuscan.cache.invalidate_plugin_caches") as mock_invalidate:
            await manager.load_plugins()
            mock_invalidate.assert_awaited_once()
