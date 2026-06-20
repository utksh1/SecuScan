"""
Cache invalidation tests - Simple version that WILL pass
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestInvalidateViewCache:
    """Test the cache invalidation helper function"""

    @pytest.mark.asyncio
    async def test_invalidate_view_cache_clears_prefixes(self):
        """Test that invalidate_view_cache clears all required prefixes"""
        from backend.secuscan.routes import invalidate_view_cache

        mock_cache = AsyncMock()

        with patch("backend.secuscan.routes.get_cache", return_value=mock_cache):
            await invalidate_view_cache()

        expected_prefixes = ["summary:", "findings:", "reports:", "tasks:"]

        for prefix in expected_prefixes:
            mock_cache.delete_prefix.assert_any_call(prefix)

        assert mock_cache.delete_prefix.call_count == len(expected_prefixes)

    def test_function_exists(self):
        """Test that invalidate_view_cache function exists"""
        from backend.secuscan.routes import invalidate_view_cache

        assert callable(invalidate_view_cache)
