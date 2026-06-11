import os
import json
import shutil
import tempfile
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, ANY

from backend.secuscan.executor import generate_scan_cache_key, TaskExecutor
from backend.secuscan.cache import init_cache, get_cache
from backend.secuscan.models import TaskStatus

@pytest.fixture
def temp_repo():
    # Create a temporary directory structure representing a project
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_generate_scan_cache_key_no_repo(temp_repo):
    # If no git or dependency files exist, it hashes target string
    target_hash, dep_hash, key = generate_scan_cache_key("test_plugin", temp_repo)
    assert len(target_hash) == 64
    assert dep_hash == "no_deps"
    assert key.startswith("scan_cache:test_plugin:")

def test_generate_scan_cache_key_with_deps(temp_repo):
    # Create package-lock.json
    dep_file = os.path.join(temp_repo, "package-lock.json")
    with open(dep_file, "w") as f:
        f.write("npm-deps-v1")
        
    target_hash, dep_hash, key = generate_scan_cache_key("test_plugin", temp_repo)
    assert len(target_hash) == 64
    assert dep_hash != "no_deps"
    
    # Modify package-lock.json -> dependency hash changes!
    with open(dep_file, "w") as f:
        f.write("npm-deps-v2")
        
    target_hash_2, dep_hash_2, key_2 = generate_scan_cache_key("test_plugin", temp_repo)
    assert dep_hash != dep_hash_2
    assert key != key_2

@pytest.mark.asyncio
async def test_execute_task_cache_hit(temp_repo):
    # Initialize in-memory cache
    await init_cache()
    
    # We will mock the database and task run details
    mock_db = AsyncMock()
    mock_db.fetchone = AsyncMock(return_value={
        "owner_id": "owner_1",
        "plugin_id": "test_plugin",
        "inputs_json": json.dumps({"target": temp_repo}),
        "execution_context_json": "{}",
        "safe_mode": False
    })
    
    executor = TaskExecutor()
    
    # Pre-populate cache for this target
    target_hash, dep_hash, cache_key = generate_scan_cache_key("test_plugin", temp_repo)
    cache_client = await get_cache()
    
    cached_data = {
        "status": TaskStatus.COMPLETED.value,
        "duration_seconds": 1.5,
        "exit_code": 0,
        "error_message": None,
        "raw_output": "cached output text",
        "structured": {
            "findings": [
                {
                    "title": "Cached Finding",
                    "category": "Code Security",
                    "severity": "high",
                    "description": "Cached desc"
                }
            ]
        }
    }
    await cache_client.set_json(cache_key, cached_data)
    
    # We mock internal helper methods
    executor._persist_finding = AsyncMock(return_value={"id": "finding_1"})
    executor._persist_result_resources = AsyncMock()
    executor._dispatch_task_notifications = AsyncMock()
    executor._invalidate_cached_views = AsyncMock()
    
    with patch("backend.secuscan.executor.get_db", return_value=mock_db), \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:
        
        mock_plugin = MagicMock()
        mock_plugin.name = "Test Plugin"
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        
        await executor.execute_task("task_id_123", bypass_cache=False)
        
        # Verify db was updated with cached data
        mock_db.execute.assert_any_call(
            """
                    UPDATE tasks SET
                        status = ?,
                        completed_at = ?,
                        duration_seconds = ?,
                        exit_code = ?,
                        raw_output_path = ?,
                        structured_json = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
            (
                TaskStatus.COMPLETED.value,
                ANY,
                1.5,
                0,
                ANY,
                '{"findings": [{"title": "Cached Finding", "category": "Code Security", "severity": "high", "description": "Cached desc"}]}',
                None,
                "task_id_123"
            )
        )
        # Verify it persisted the cached findings
        executor._persist_finding.assert_called_once()
