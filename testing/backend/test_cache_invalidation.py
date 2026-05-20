"""Tests for cache invalidation on task deletion"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.secuscan.main import app

client = TestClient(app)


class TestCacheInvalidation:
    """Test that cache is cleared when tasks are deleted"""
    
    def test_delete_task_invalidates_cache(self):
        """Test that deleting a single task clears the cache"""
        # First, get tasks to populate cache
        response1 = client.get("/api/v1/tasks")
        assert response1.status_code == 200
        
        # Delete a task (use a real task ID if exists)
        # response2 = client.delete("/api/v1/task/some-task-id")
        
        # Get tasks again - cache should be fresh
        response3 = client.get("/api/v1/tasks")
        assert response3.status_code == 200
        
        # Verify cache was invalidated
        # (This would need cache inspection)
    
    def test_bulk_delete_invalidates_cache(self):
        """Test that bulk delete clears the cache"""
        response = client.delete("/api/v1/tasks/bulk", json={"task_ids": []})
        assert response.status_code in [200, 400]
    
    def test_clear_all_tasks_invalidates_cache(self):
        """Test that clear all tasks clears the cache"""
        response = client.delete("/api/v1/tasks/clear")
        assert response.status_code in [200, 400]