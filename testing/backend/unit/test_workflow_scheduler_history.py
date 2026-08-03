"""
Tests for background scheduler workflow run recording, auto-version-snapshotting,
and run finalization lifecycle.
"""

import json
import uuid
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from backend.secuscan.database import Database
from backend.secuscan.workflows import WorkflowScheduler, _finalize_workflow_run

_STEPS = [{"plugin_id": "http_inspector", "inputs": {"url": "http://example.com"}}]


@pytest_asyncio.fixture
async def db(tmp_path):
    instance = Database(str(tmp_path / "test.db"))
    await instance.connect()
    # Mock global get_db to return this database instance
    with patch("backend.secuscan.workflows.get_db", return_value=instance):
        yield instance
    await instance.disconnect()


async def _insert_workflow(db: Database, name: str = "test-wf") -> str:
    wf_id = uuid.uuid4().hex
    await db.execute(
        "INSERT INTO workflows (id, name, steps_json, enabled, schedule_seconds) VALUES (?, ?, ?, 1, 60)",
        (wf_id, name, json.dumps(_STEPS)),
    )
    return wf_id


@pytest.mark.asyncio
async def test_scheduler_run_workflow_creates_snapshot_and_run_record(db):
    wf_id = await _insert_workflow(db)

    # Verify no version snapshot or run record exists yet
    versions = await db.get_workflow_versions(wf_id)
    assert len(versions) == 0

    runs = await db.get_workflow_runs(wf_id)
    assert runs["total"] == 0

    scheduler = WorkflowScheduler()

    # Mock plugin manager and plugin
    mock_pm = MagicMock()
    mock_plugin = MagicMock()
    mock_plugin.category = "scan"
    mock_plugin.safety = {"rate_limit": {"max_per_hour": 50}}
    mock_pm.get_plugin.return_value = mock_plugin

    # Mock executor and concurrency limiter
    mock_executor = MagicMock()
    mock_executor.create_task = AsyncMock(return_value="t-123")
    mock_executor.execute_task = AsyncMock()

    mock_concurrent = MagicMock()
    mock_concurrent.acquire = AsyncMock(return_value=(True, ""))

    with patch("backend.secuscan.plugins.get_plugin_manager", return_value=mock_pm), \
         patch("backend.secuscan.workflows.executor", mock_executor), \
         patch("backend.secuscan.workflows.concurrent_limiter", mock_concurrent), \
         patch("backend.secuscan.workflows.get_target_policy", return_value=None), \
         patch("backend.secuscan.validation.validate_target", return_value=(True, "")):

        await scheduler._run_workflow(wf_id, _STEPS, owner_id="default")

    # Check that a version snapshot was automatically created
    versions = await db.get_workflow_versions(wf_id)
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["definition"]["name"] == "test-wf"

    # Check that a workflow run was recorded with triggered_by="scheduler"
    runs = await db.get_workflow_runs(wf_id)
    assert runs["total"] == 1
    run = runs["runs"][0]
    assert run["triggered_by"] == "scheduler"
    assert run["task_ids"] == ["t-123"]
    assert run["status"] == "queued"

    # Insert the completed task in the db
    await db.execute(
        "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
        "VALUES ('t-123', 'default', 'http_inspector', 'http_inspector', 'example.com', 'completed', '{}')"
    )

    # Call _finalize_workflow_run with a fast poll to finalize it immediately
    await _finalize_workflow_run(run["id"], poll_interval=0.01, max_polls=5)

    # Verify the status is now completed
    runs = await db.get_workflow_runs(wf_id)
    assert runs["runs"][0]["status"] == "completed"
