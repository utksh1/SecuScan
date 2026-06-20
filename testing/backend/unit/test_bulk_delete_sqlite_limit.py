"""
testing/backend/unit/test_bulk_delete_sqlite_limit.py

Regression tests for Issue #313 — DELETE /tasks/bulk SQLite variable-limit DoS.

Covers the four cases requested in the PR review:
  1. Empty list  → 200, deleted_count=0
  2. 500 IDs     → 200, accepted (at the limit)
  3. 501 IDs     → 422, rejected  (over the limit)
  4. delete_task_records() chunks correctly when given more than one chunk
     (i.e. > SQLITE_CHUNK_SIZE IDs) — verifies the helper never builds a
     placeholder string longer than SQLITE_LIMIT_VARIABLE_NUMBER = 999.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from backend.secuscan.models import BulkDeleteRequest, MAX_BULK_DELETE
from backend.secuscan.routes import SQLITE_CHUNK_SIZE

ENDPOINT = "/api/v1/tasks/bulk"


# Fixtures  (mirrors test_task_cleanup.py)


@pytest_asyncio.fixture
async def db_path(tmp_path):
    return str(tmp_path / "test_secuscan.db")


@pytest_asyncio.fixture
async def app_client(db_path):
    mock_executor = MagicMock()
    mock_executor.cancel_task = AsyncMock(return_value=True)
    mock_executor.get_task_status = AsyncMock(return_value={"status": "queued"})

    with patch("backend.secuscan.routes.executor", mock_executor):
        from backend.secuscan.main import app
        from backend.secuscan import database as db_module
        from backend.secuscan import cache as cache_module
        from backend.secuscan import auth as auth_module

        await cache_module.init_cache()
        test_db = await db_module.init_db(db_path)

        import tempfile, os

        with tempfile.TemporaryDirectory() as tmp_data_dir:
            api_key = auth_module.init_api_key(tmp_data_dir)

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"X-Api-Key": api_key},
            ) as client:
                client._mock_executor = mock_executor
                client._db = test_db
                client._db_path = db_path
                yield client

        await test_db.disconnect()
        db_module.db = None
        await cache_module.cache.disconnect()
        cache_module.cache = None


async def insert_task(db, status: str = "completed") -> str:
    task_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO tasks "
        "(id, plugin_id, tool_name, target, status, inputs_json, consent_granted) "
        "VALUES (?, 'nmap', 'nmap', '127.0.0.1', ?, '{}', 1)",
        (task_id, status),
    )
    return task_id


# 1. Unit tests — BulkDeleteRequest Pydantic model validation


class TestBulkDeleteRequestModel:
    """
    Validates that the Pydantic model enforces size limits before any
    database code runs.  No HTTP server needed.
    """

    def test_empty_list_is_valid(self):
        """[] must parse successfully — endpoint handles it as a no-op."""
        req = BulkDeleteRequest([])
        assert req.root == []

    def test_single_id_is_valid(self):
        req = BulkDeleteRequest([str(uuid.uuid4())])
        assert len(req.root) == 1

    def test_exactly_500_ids_is_valid(self):
        """500 IDs is the documented limit — must be accepted."""
        ids = [str(uuid.uuid4()) for _ in range(MAX_BULK_DELETE)]
        req = BulkDeleteRequest(ids)
        assert len(req.root) == MAX_BULK_DELETE

    def test_501_ids_raises_validation_error(self):
        """501 IDs must be rejected by Pydantic before reaching any SQL."""
        ids = [str(uuid.uuid4()) for _ in range(MAX_BULK_DELETE + 1)]
        with pytest.raises(ValidationError) as exc_info:
            BulkDeleteRequest(ids)
        errors = exc_info.value.errors()
        assert any(
            e["type"] in ("too_long", "value_error") for e in errors
        ), f"Expected a list-length validation error, got: {errors}"

    def test_1000_ids_raises_validation_error(self):
        """1000 IDs (the original crash threshold) must also be rejected."""
        ids = [str(uuid.uuid4()) for _ in range(1000)]
        with pytest.raises(ValidationError):
            BulkDeleteRequest(ids)


# 2. Integration — HTTP endpoint boundary tests


class TestBulkDeleteEndpointLimits:
    @pytest.mark.asyncio
    async def test_empty_list_returns_200(self, app_client):
        """[] must return 200 with deleted_count=0 — not 422."""
        resp = await app_client.request("DELETE", ENDPOINT, json=[])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_500_ids_accepted(self, app_client):
        """500 IDs (at the limit) must be accepted with 200."""
        # Use random UUIDs — they won't exist in DB so deleted_count=0,
        # but the endpoint must NOT reject the request with 422.
        ids = [str(uuid.uuid4()) for _ in range(MAX_BULK_DELETE)]
        resp = await app_client.request("DELETE", ENDPOINT, json=ids)
        assert (
            resp.status_code == 200
        ), f"Expected 200 for {MAX_BULK_DELETE} IDs, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_501_ids_rejected_with_422(self, app_client):
        """501 IDs (one over the limit) must be rejected with 422."""
        ids = [str(uuid.uuid4()) for _ in range(MAX_BULK_DELETE + 1)]
        resp = await app_client.request("DELETE", ENDPOINT, json=ids)
        assert (
            resp.status_code == 422
        ), f"Expected 422 for {MAX_BULK_DELETE + 1} IDs, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_response_shape_on_success(self, app_client):
        """Success response must always include both 'success' and 'deleted_count'."""
        resp = await app_client.request("DELETE", ENDPOINT, json=[])
        body = resp.json()
        assert "success" in body
        assert "deleted_count" in body


# 3. Unit test — delete_task_records() chunking


class TestDeleteTaskRecordsChunking:
    """
    Verifies that delete_task_records() never passes more than
    SQLITE_CHUNK_SIZE IDs in a single SQL statement.

    We mock db.execute and db.fetchall to capture the actual placeholder
    strings produced, then assert that no call ever exceeds the chunk limit.
    This is the core regression guard for the SQLite variable-number crash.
    """

    @pytest.mark.asyncio
    async def test_single_chunk_does_not_exceed_sqlite_limit(self):
        """
        For a list of exactly SQLITE_CHUNK_SIZE IDs, one chunk is produced
        and the placeholder count stays within the SQLite variable limit.
        """
        from backend.secuscan.routes import delete_task_records

        ids = [str(uuid.uuid4()) for _ in range(SQLITE_CHUNK_SIZE)]
        captured_sql: list[str] = []

        mock_db = AsyncMock()
        mock_db.fetchall = AsyncMock(return_value=[])
        mock_db.fetchone = AsyncMock(return_value=None)
        mock_db.begin = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        async def capture_execute(sql, params=()):
            captured_sql.append(sql)

        mock_db.execute_no_commit = capture_execute

        with patch("backend.secuscan.routes.get_db", return_value=mock_db):
            await delete_task_records(ids)

        for sql in captured_sql:
            placeholder_count = sql.count("?")
            assert placeholder_count <= SQLITE_CHUNK_SIZE, (
                f"SQL exceeded SQLITE_CHUNK_SIZE={SQLITE_CHUNK_SIZE}: "
                f"{placeholder_count} placeholders in:\n{sql}"
            )

    @pytest.mark.asyncio
    async def test_multi_chunk_splits_correctly(self):
        """
        For SQLITE_CHUNK_SIZE + 1 IDs, the helper must issue at least two
        batches — no single SQL call may hold all IDs at once.

        This directly reproduces the pre-fix crash path:
          OperationalError: too many SQL variables
        """
        from backend.secuscan.routes import delete_task_records

        total = SQLITE_CHUNK_SIZE + 1  # forces exactly 2 chunks
        ids = [str(uuid.uuid4()) for _ in range(total)]
        captured_sql: list[str] = []
        captured_params: list[tuple] = []

        mock_db = AsyncMock()
        mock_db.fetchall = AsyncMock(return_value=[])
        mock_db.fetchone = AsyncMock(return_value=None)
        mock_db.begin = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        async def capture_execute(sql, params=()):
            captured_sql.append(sql)
            captured_params.append(params)

        mock_db.execute_no_commit = capture_execute

        with patch("backend.secuscan.routes.get_db", return_value=mock_db):
            await delete_task_records(ids)

        # Every single execute call must respect the chunk size
        for sql, params in zip(captured_sql, captured_params):
            placeholder_count = sql.count("?")
            assert placeholder_count <= SQLITE_CHUNK_SIZE, (
                f"A single SQL call had {placeholder_count} placeholders "
                f"(limit={SQLITE_CHUNK_SIZE}):\n{sql}"
            )
            assert len(params) <= SQLITE_CHUNK_SIZE, (
                f"A single SQL call had {len(params)} bound params "
                f"(limit={SQLITE_CHUNK_SIZE})"
            )

        # Sanity: the helper must have issued more than one DELETE per table
        delete_tasks_calls = [s for s in captured_sql if "DELETE FROM tasks" in s]
        assert len(delete_tasks_calls) >= 2, (
            f"Expected ≥2 DELETE FROM tasks batches for {total} IDs, "
            f"got {len(delete_tasks_calls)}"
        )

    @pytest.mark.asyncio
    async def test_empty_list_returns_immediately(self):
        """delete_task_records([]) must return without touching the database."""
        from backend.secuscan.routes import delete_task_records

        mock_db = AsyncMock()

        with patch("backend.secuscan.routes.get_db", return_value=mock_db):
            await delete_task_records([])

        mock_db.execute.assert_not_called()
        mock_db.execute_no_commit.assert_not_called()
        mock_db.fetchall.assert_not_called()
        mock_db.fetchone.assert_not_called()
        mock_db.begin.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.rollback.assert_not_called()
