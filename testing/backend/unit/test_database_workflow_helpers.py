"""
Unit tests for workflow-related database helpers in backend.secuscan.database.
Tests the Database class async methods using unittest.mock.AsyncMock.
"""

import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.database import Database


class MockRow:
    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data.get(key)


class TestSnapshotWorkflowVersion:
    @patch("backend.secuscan.database.json")
    def test_increments_version_number(self, mock_json):
        mock_json.dumps = lambda x: json.dumps(x)
        db = Database(":memory:")
        db._connection = MagicMock()
        # Simulate no prior versions
        mock_fetchone = AsyncMock(return_value={"max_v": None})
        db.fetchone = mock_fetchone
        db.execute = AsyncMock()

        import asyncio
        async def run():
            result = await db.snapshot_workflow_version(
                workflow_id="wf-1",
                name="Test Workflow",
                schedule_seconds=3600,
                enabled=True,
                steps=[{"plugin_id": "nmap", "target": "example.com"}],
                created_by="test",
            )
            return result

        result = asyncio.run(run())
        assert result["workflow_id"] == "wf-1"
        assert result["version_number"] == 1
        assert result["created_by"] == "test"

    @patch("backend.secuscan.database.json")
    def test_increments_from_existing_versions(self, mock_json):
        mock_json.dumps = lambda x: json.dumps(x)
        db = Database(":memory:")
        db._connection = MagicMock()
        mock_fetchone = AsyncMock(return_value={"max_v": 5})
        db.fetchone = mock_fetchone
        db.execute = AsyncMock()

        import asyncio
        async def run():
            return await db.snapshot_workflow_version(
                workflow_id="wf-1",
                name="Test Workflow",
                schedule_seconds=3600,
                enabled=True,
                steps=[],
                created_by="test",
            )

        result = asyncio.run(run())
        assert result["version_number"] == 6


class TestGetWorkflowVersion:
    @patch("backend.secuscan.database.json")
    def test_returns_version_for_valid_input(self, mock_json):
        mock_json.loads = lambda x: {"name": "Test", "steps": []}
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(return_value={
            "id": "v-123",
            "workflow_id": "wf-1",
            "version_number": 2,
            "definition_json": '{"name": "Test", "steps": []}',
            "created_at": "2024-01-01",
            "created_by": "test",
        })

        import asyncio
        async def run():
            return await db.get_workflow_version("wf-1", 2)

        result = asyncio.run(run())
        assert result["version_number"] == 2
        assert result["definition"]["name"] == "Test"

    def test_returns_none_for_missing_version(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(return_value=None)

        import asyncio
        async def run():
            return await db.get_workflow_version("wf-1", 999)

        result = asyncio.run(run())
        assert result is None


class TestRecordWorkflowRun:
    @patch("backend.secuscan.database.json")
    def test_returns_run_id(self, mock_json):
        mock_json.dumps = lambda x: json.dumps(x)
        db = Database(":memory:")
        db._connection = MagicMock()
        db.execute = AsyncMock()

        import asyncio
        async def run():
            return await db.record_workflow_run(
                workflow_id="wf-1",
                version_id="v-123",
                version_number=1,
                task_ids=["task-1", "task-2"],
                triggered_by="manual",
            )

        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0


class TestFinalizeWorkflowRun:
    def test_updates_status_and_timestamp(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.execute = AsyncMock()

        import asyncio
        async def run():
            await db.finalize_workflow_run("run-123", "completed")

        asyncio.run(run())
        db.execute.assert_called_once()
        call_args = db.execute.call_args
        assert "completed" in call_args[0][0]
        assert "run-123" in call_args[0][1]


class TestCheckWorkflowRunTasks:
    def test_returns_completed_when_all_completed(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(side_effect=[
            {"task_ids_json": '["task-1", "task-2"]'},  # get run
            {"status": "completed"},  # task-1
            {"status": "completed"},  # task-2
        ])

        import asyncio
        async def run():
            return await db.check_workflow_run_tasks("run-123")

        result = asyncio.run(run())
        assert result == "completed"

    def test_returns_none_when_tasks_in_progress(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(side_effect=[
            {"task_ids_json": '["task-1", "task-2"]'},
            {"status": "completed"},
            {"status": "running"},
        ])

        import asyncio
        async def run():
            return await db.check_workflow_run_tasks("run-123")

        result = asyncio.run(run())
        assert result is None

    def test_returns_failed_when_any_failed(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(side_effect=[
            {"task_ids_json": '["task-1", "task-2"]'},
            {"status": "failed"},
            {"status": "failed"},
        ])

        import asyncio
        async def run():
            return await db.check_workflow_run_tasks("run-123")

        result = asyncio.run(run())
        assert result == "failed"

    def test_returns_cancelled_when_any_cancelled(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(side_effect=[
            {"task_ids_json": '["task-1", "task-2"]'},
            {"status": "completed"},
            {"status": "cancelled"},
        ])

        import asyncio
        async def run():
            return await db.check_workflow_run_tasks("run-123")

        result = asyncio.run(run())
        assert result == "cancelled"

    def test_returns_completed_for_empty_task_list(self):
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(return_value={"task_ids_json": "[]"})

        import asyncio
        async def run():
            return await db.check_workflow_run_tasks("run-123")

        result = asyncio.run(run())
        assert result == "completed"


class TestGetWorkflowRuns:
    @patch("backend.secuscan.database.json")
    def test_pagination(self, mock_json):
        mock_json.loads = lambda x: json.loads(x)
        db = Database(":memory:")
        db._connection = MagicMock()
        db.fetchone = AsyncMock(return_value={"total": 50})
        db.fetchall = AsyncMock(return_value=[
            {
                "id": "run-1",
                "workflow_id": "wf-1",
                "version_id": "v-1",
                "version_number": 1,
                "triggered_by": "manual",
                "status": "completed",
                "task_ids_json": '["task-1"]',
                "started_at": "2024-01-01",
                "completed_at": "2024-01-01",
                "error_message": None,
            }
        ])

        import asyncio
        async def run():
            return await db.get_workflow_runs("wf-1", limit=10, offset=20)

        result = asyncio.run(run())
        assert result["total"] == 50
        assert len(result["runs"]) == 1
        assert result["runs"][0]["task_ids"] == ["task-1"]
