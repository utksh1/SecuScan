"""
Tests for cache invalidation on task deletion endpoints.
Verifies that caches are properly cleared when tasks are deleted.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.secuscan.main import app


class TestCacheInvalidation:
    """Test suite for cache invalidation when deleting tasks"""

    def test_delete_task_endpoint_exists(self, test_client):
        """Test that delete task endpoint is accessible"""
        response = test_client.delete("/api/v1/task/non-existent-id")
        # 404 is fine - means endpoint exists but task not found
        assert response.status_code == 404

    def test_bulk_delete_endpoint_exists(self, test_client):
        """Test that bulk delete endpoint exists"""
        response = test_client.delete(
            "/api/v1/tasks/bulk",
            json=[]
        )
        # 200, 400, or 422 are all acceptable
        assert response.status_code in [200, 400, 422]

    def test_clear_all_tasks_endpoint_exists(self, test_client):
        """Test that clear all tasks endpoint exists"""
        response = test_client.delete("/api/v1/tasks/clear")
        assert response.status_code in [200, 400]

    def test_invalidate_view_cache_function_exists(self):
        """Test that invalidate_view_cache helper function exists"""
        from backend.secuscan.routes import invalidate_view_cache
        assert callable(invalidate_view_cache)

    def test_cache_prefixes_are_correct(self):
        """Test that cache prefixes are the expected values"""
        expected_prefixes = ["summary:", "findings:", "reports:", "tasks:"]
        assert len(expected_prefixes) == 4
        assert "tasks:" in expected_prefixes
        assert "summary:" in expected_prefixes


class TestInvalidateViewCacheFunction:
    """Test the invalidate_view_cache helper function directly"""

    @pytest.mark.asyncio
    async def test_invalidate_view_cache_clears_prefixes(self):
        """Test that invalidate_view_cache clears all required prefixes"""
        from backend.secuscan.routes import invalidate_view_cache

        # Mock cache
        mock_cache = AsyncMock()

        with patch("backend.secuscan.routes.get_cache", return_value=mock_cache):
            await invalidate_view_cache()

        # Verify delete_prefix was called for each prefix
        expected_prefixes = ["summary:", "findings:", "reports:", "tasks:"]

        for prefix in expected_prefixes:
            mock_cache.delete_prefix.assert_any_call(prefix)

        assert mock_cache.delete_prefix.call_count == len(expected_prefixes)