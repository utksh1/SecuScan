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
from backend.secuscan.execution_context import normalize_execution_context

@pytest.fixture
def temp_repo():
    # Create a temporary directory structure representing a project
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_generate_scan_cache_key_no_repo(temp_repo):
    # If no git or dependency files exist, it hashes target string
    target_hash, dep_hash, key = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo},
        execution_context={},
        safe_mode=False
    )
    assert len(target_hash) == 64
    assert dep_hash == "no_deps"
    assert key.startswith("scan_cache:owner_1:test_plugin:0:")

def test_generate_scan_cache_key_with_deps(temp_repo):
    # Create package-lock.json
    dep_file = os.path.join(temp_repo, "package-lock.json")
    with open(dep_file, "w") as f:
        f.write("npm-deps-v1")

    target_hash, dep_hash, key = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo},
        execution_context={},
        safe_mode=False
    )
    assert len(target_hash) == 64
    assert dep_hash != "no_deps"

    # Modify package-lock.json -> dependency hash changes!
    with open(dep_file, "w") as f:
        f.write("npm-deps-v2")

    target_hash_2, dep_hash_2, key_2 = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo},
        execution_context={},
        safe_mode=False
    )
    assert dep_hash != dep_hash_2
    assert key != key_2

def test_cache_key_tenant_isolation(temp_repo):
    # Same inputs/target, different owners -> different cache keys!
    _, _, key_owner1 = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo, "flag": "x"},
        execution_context={"profile": "admin"},
        safe_mode=False
    )
    _, _, key_owner2 = generate_scan_cache_key(
        owner_id="owner_2",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo, "flag": "x"},
        execution_context={"profile": "admin"},
        safe_mode=False
    )
    assert key_owner1 != key_owner2

def test_cache_key_inputs_isolation(temp_repo):
    # Same target/owner, different inputs/flags -> different cache keys!
    _, _, key_inputs1 = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo, "wordlist": "common.txt"},
        execution_context={},
        safe_mode=False
    )
    _, _, key_inputs2 = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo, "wordlist": "deep.txt"},
        execution_context={},
        safe_mode=False
    )
    assert key_inputs1 != key_inputs2

def test_cache_key_safe_mode_isolation(temp_repo):
    # Same inputs/owner, safe_mode toggled -> different cache keys!
    _, _, key_safe = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo},
        execution_context={},
        safe_mode=True
    )
    _, _, key_unsafe = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs={"target": temp_repo},
        execution_context={},
        safe_mode=False
    )
    assert key_unsafe != key_safe

@pytest.mark.asyncio
async def test_execute_task_cache_hit(temp_repo):
    # Initialize in-memory cache
    await init_cache()

    # We will mock the database and task run details using a SQL-inspecting side effect
    mock_db = AsyncMock()
    async def db_fetchone_mock(query, params=()):
        query_lower = query.lower()
        if "select owner_id, plugin_id" in query_lower:
            return {
                "owner_id": "owner_1",
                "plugin_id": "test_plugin",
                "inputs_json": json.dumps({"target": temp_repo}),
                "execution_context_json": "{}",
                "safe_mode": False
            }
        return None
    mock_db.fetchone = AsyncMock(side_effect=db_fetchone_mock)

    executor = TaskExecutor()

    # Pre-populate cache for this target/owner/inputs/context/safe_mode
    # Note: inputs is hydrated inside execute_task to contain normalized execution_context
    execution_context = normalize_execution_context({})
    inputs = {"target": temp_repo, "__execution_context": execution_context}
    target_hash, dep_hash, cache_key = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs=inputs,
        execution_context=execution_context,
        safe_mode=False
    )
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
    executor._execute_command = AsyncMock()

    with patch("backend.secuscan.executor.get_db", return_value=mock_db), \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_plugin = MagicMock()
        mock_plugin.name = "Test Plugin"
        mock_pm.return_value.get_plugin.return_value = mock_plugin

        await executor.execute_task("task_id_123", bypass_cache=False)

        # Verify _execute_command was never called (regression test for cache bypass)
        executor._execute_command.assert_not_called()

        # Verify db was updated with status, duration, etc.
        mock_db.execute.assert_any_call(
            """
                    UPDATE tasks SET
                        status = ?,
                        completed_at = ?,
                        duration_seconds = ?,
                        exit_code = ?,
                        raw_output_path = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
            (
                TaskStatus.COMPLETED.value,
                ANY,
                1.5,
                0,
                ANY,
                None,
                "task_id_123"
            )
        )

        # Verify it persisted the cached findings and updated structured_json
        executor._persist_finding.assert_called_once()
        mock_db.execute.assert_any_call(
            "UPDATE tasks SET structured_json = ? WHERE id = ?",
            (ANY, "task_id_123")
        )

@pytest.mark.asyncio
async def test_execute_task_transient_failure_not_cached(temp_repo):
    # Initialize in-memory cache
    await init_cache()

    mock_db = AsyncMock()
    async def db_fetchone_mock(query, params=()):
        query_lower = query.lower()
        if "select owner_id, plugin_id" in query_lower:
            return {
                "owner_id": "owner_1",
                "plugin_id": "test_plugin",
                "inputs_json": json.dumps({"target": temp_repo}),
                "execution_context_json": "{}",
                "safe_mode": False
            }
        if "select status, duration_seconds" in query_lower:
            return {
                "status": TaskStatus.FAILED.value,
                "duration_seconds": 2.0,
                "exit_code": 1,
                "error_message": "Transient network timeout",
                "structured_json": None,
                "raw_output_path": None
            }
        return None
    mock_db.fetchone = AsyncMock(side_effect=db_fetchone_mock)

    executor = TaskExecutor()
    executor._persist_findings_and_report_common = AsyncMock()
    executor._dispatch_task_notifications = AsyncMock()
    executor._invalidate_cached_views = AsyncMock()

    # Stub the actually executed command to fail
    async def fake_command(*args, **kwargs):
        return "Network timeout", 1

    execution_context = normalize_execution_context({})
    inputs = {"target": temp_repo, "__execution_context": execution_context}
    _, _, cache_key = generate_scan_cache_key(
        owner_id="owner_1",
        plugin_id="test_plugin",
        target=temp_repo,
        inputs=inputs,
        execution_context=execution_context,
        safe_mode=False
    )

    with patch("backend.secuscan.executor.get_db", return_value=mock_db), \
         patch.object(executor, "_execute_command", side_effect=fake_command), \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_plugin = MagicMock()
        mock_plugin.name = "Test Plugin"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "test_plugin"

        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["ping", temp_repo]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task("task_id_456", bypass_cache=False)

        # The cache should be empty for this key because the task status is FAILED
        cache_client = await get_cache()
        cached_val = await cache_client.get_json(cache_key)
        assert cached_val is None
