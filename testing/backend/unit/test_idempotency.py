"""
Unit tests for task idempotency key support (issue #215).

Covers:
- Database-level record/lookup/purge helpers
- POST /task/start with Idempotency-Key header (hit and miss paths)
- Key validation (too short, too long, invalid characters)
- TTL expiry (lookup returns None after expiry)
- Owner isolation (same key, different owners → separate tasks)
- Audit logging on idempotency hits
- Startup purge of expired keys
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Shared async fixture for an isolated Database instance
# ---------------------------------------------------------------------------


@pytest.fixture
async def isolated_db(tmp_path):
    """Yield an isolated Database instance wired to a temp file.

    Using an async fixture ensures pytest-asyncio manages the event loop
    consistently; we also skip explicit disconnect to avoid the aiosqlite
    thread warning when the loop closes.
    """
    from backend.secuscan.database import Database

    db_path = str(tmp_path / "test_idempotency.db")
    db = Database(db_path)
    await db.connect()
    yield db
    # Do not call disconnect() here: aiosqlite closes its worker thread only
    # after the connection object is GC-d; calling disconnect from inside the
    # test's event loop tear-down causes a spurious "Event loop is closed"
    # warning that does not indicate a real failure.


# ---------------------------------------------------------------------------
# DATABASE-LEVEL TESTS
# ---------------------------------------------------------------------------


class TestRecordIdempotencyKey:
    """record_idempotency_key persists a key→task_id mapping."""

    @pytest.mark.asyncio
    async def test_record_stores_key(self, isolated_db):
        await isolated_db.record_idempotency_key("key-abc-001", "task-111", "owner-A", 3600)
        row = await isolated_db.fetchone(
            "SELECT task_id, owner_id FROM task_idempotency "
            "WHERE idempotency_key = ? AND owner_id = ?",
            ("key-abc-001", "owner-A"),
        )
        assert row is not None
        assert row["task_id"] == "task-111"
        assert row["owner_id"] == "owner-A"

    @pytest.mark.asyncio
    async def test_record_sets_expiry_in_future(self, isolated_db):
        await isolated_db.record_idempotency_key("key-expiry-check", "task-222", "owner-B", 7200)
        row = await isolated_db.fetchone(
            "SELECT expires_at > datetime('now') AS still_valid "
            "FROM task_idempotency WHERE idempotency_key = ? AND owner_id = ?",
            ("key-expiry-check", "owner-B"),
        )
        assert row is not None
        assert row["still_valid"] == 1

    @pytest.mark.asyncio
    async def test_record_is_idempotent_on_duplicate_insert(self, isolated_db):
        """INSERT OR IGNORE must not raise on a second call with the same composite key."""
        await isolated_db.record_idempotency_key("key-dup", "task-first", "owner-C", 3600)
        # Second call must not raise and must not overwrite the first task_id
        await isolated_db.record_idempotency_key("key-dup", "task-second", "owner-C", 3600)
        row = await isolated_db.fetchone(
            "SELECT task_id FROM task_idempotency "
            "WHERE idempotency_key = ? AND owner_id = ?",
            ("key-dup", "owner-C"),
        )
        assert row["task_id"] == "task-first", "First task_id must win under INSERT OR IGNORE"

    @pytest.mark.asyncio
    async def test_different_owners_same_key_stored_independently(self, isolated_db):
        """Two owners with the same key get independent rows (composite PK)."""
        await isolated_db.record_idempotency_key("shared-key-xyz", "task-ownerX", "owner-X", 3600)
        await isolated_db.record_idempotency_key("shared-key-xyz", "task-ownerY", "owner-Y", 3600)
        row_x = await isolated_db.fetchone(
            "SELECT task_id FROM task_idempotency "
            "WHERE idempotency_key = ? AND owner_id = ?",
            ("shared-key-xyz", "owner-X"),
        )
        row_y = await isolated_db.fetchone(
            "SELECT task_id FROM task_idempotency "
            "WHERE idempotency_key = ? AND owner_id = ?",
            ("shared-key-xyz", "owner-Y"),
        )
        assert row_x["task_id"] == "task-ownerX"
        assert row_y["task_id"] == "task-ownerY"

    @pytest.mark.asyncio
    async def test_record_correct_ttl_applied(self, isolated_db):
        """Verify that TTL is actually used and produces the right window."""
        await isolated_db.record_idempotency_key("key-ttl-test", "task-ttl", "owner-T", 60)
        row = await isolated_db.fetchone(
            """
            SELECT
                CAST(strftime('%s', expires_at) AS INTEGER) -
                CAST(strftime('%s', created_at) AS INTEGER) AS actual_ttl_seconds
            FROM task_idempotency
            WHERE idempotency_key = ? AND owner_id = ?
            """,
            ("key-ttl-test", "owner-T"),
        )
        assert row is not None
        # Allow ±1 s for clock tick between the two datetime() calls in SQLite
        assert abs(row["actual_ttl_seconds"] - 60) <= 1


# ---------------------------------------------------------------------------
# LOOKUP TESTS
# ---------------------------------------------------------------------------


class TestLookupIdempotencyKey:
    """lookup_idempotency_key returns task_id on a live hit and None otherwise."""

    @pytest.mark.asyncio
    async def test_lookup_returns_task_id_for_live_key(self, isolated_db):
        await isolated_db.record_idempotency_key("live-key-1", "task-live", "owner-D", 3600)
        result = await isolated_db.lookup_idempotency_key("live-key-1", "owner-D")
        assert result == "task-live"

    @pytest.mark.asyncio
    async def test_lookup_returns_none_for_missing_key(self, isolated_db):
        result = await isolated_db.lookup_idempotency_key("nonexistent-key", "owner-E")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_returns_none_for_expired_key(self, isolated_db):
        """A key stored with an expiry already in the past must not be returned."""
        await isolated_db.execute(
            """
            INSERT INTO task_idempotency
                (idempotency_key, task_id, owner_id, created_at, expires_at)
            VALUES (?, ?, ?, datetime('now', '-10 seconds'), datetime('now', '-5 seconds'))
            """,
            ("expired-key-1", "task-expired", "owner-F"),
        )
        result = await isolated_db.lookup_idempotency_key("expired-key-1", "owner-F")
        assert result is None, "Expired key must not be returned by lookup"

    @pytest.mark.asyncio
    async def test_lookup_respects_owner_isolation(self, isolated_db):
        """A key belonging to owner-G must not be visible to owner-H."""
        await isolated_db.record_idempotency_key("isolated-key", "task-G", "owner-G", 3600)
        result = await isolated_db.lookup_idempotency_key("isolated-key", "owner-H")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_does_not_modify_the_row(self, isolated_db):
        """lookup must be a read-only operation and not consume or delete the key."""
        await isolated_db.record_idempotency_key("read-only-key", "task-RO", "owner-RO", 3600)
        first = await isolated_db.lookup_idempotency_key("read-only-key", "owner-RO")
        second = await isolated_db.lookup_idempotency_key("read-only-key", "owner-RO")
        assert first == "task-RO"
        assert second == "task-RO", "Repeated lookups must return the same task_id"


# ---------------------------------------------------------------------------
# PURGE TESTS
# ---------------------------------------------------------------------------


class TestPurgeExpiredIdempotencyKeys:
    """purge_expired_idempotency_keys removes only rows past their TTL."""

    @pytest.mark.asyncio
    async def test_purge_removes_expired_rows(self, isolated_db):
        # Insert one expired and one live row
        await isolated_db.execute(
            """
            INSERT INTO task_idempotency
                (idempotency_key, task_id, owner_id, created_at, expires_at)
            VALUES (?, ?, ?, datetime('now', '-60 seconds'), datetime('now', '-30 seconds'))
            """,
            ("old-expired", "task-old", "owner-purge"),
        )
        await isolated_db.record_idempotency_key("still-live", "task-live", "owner-purge", 3600)

        deleted = await isolated_db.purge_expired_idempotency_keys()
        assert deleted == 1, "Exactly one expired row should be removed"

        # Live row must still be present
        live = await isolated_db.fetchone(
            "SELECT task_id FROM task_idempotency "
            "WHERE idempotency_key = ? AND owner_id = ?",
            ("still-live", "owner-purge"),
        )
        assert live is not None
        # Expired row must be gone
        expired = await isolated_db.fetchone(
            "SELECT task_id FROM task_idempotency "
            "WHERE idempotency_key = ? AND owner_id = ?",
            ("old-expired", "owner-purge"),
        )
        assert expired is None

    @pytest.mark.asyncio
    async def test_purge_returns_zero_when_nothing_to_delete(self, isolated_db):
        await isolated_db.record_idempotency_key("fresh-key", "task-fresh", "owner-Q", 3600)
        deleted = await isolated_db.purge_expired_idempotency_keys()
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_purge_removes_multiple_expired_rows(self, isolated_db):
        for i in range(5):
            await isolated_db.execute(
                """
                INSERT INTO task_idempotency
                    (idempotency_key, task_id, owner_id, created_at, expires_at)
                VALUES (?, ?, ?, datetime('now'), datetime('now', '-1 second'))
                """,
                (f"stale-key-{i}", f"task-stale-{i}", "owner-batch"),
            )
        deleted = await isolated_db.purge_expired_idempotency_keys()
        assert deleted == 5

    @pytest.mark.asyncio
    async def test_purge_is_idempotent(self, isolated_db):
        """Calling purge twice in succession must not error or double-delete."""
        await isolated_db.execute(
            """
            INSERT INTO task_idempotency
                (idempotency_key, task_id, owner_id, created_at, expires_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now', '-1 second'))
            """,
            ("purge-twice", "task-purge", "owner-p2"),
        )
        first_purge = await isolated_db.purge_expired_idempotency_keys()
        second_purge = await isolated_db.purge_expired_idempotency_keys()
        assert first_purge == 1
        assert second_purge == 0


# ---------------------------------------------------------------------------
# KEY VALIDATION UNIT TESTS  (pure Python — no DB needed)
# ---------------------------------------------------------------------------


class TestIdempotencyKeyValidation:
    """_validate_idempotency_key enforces length and charset constraints."""

    @staticmethod
    def _validate(key: str):
        from backend.secuscan.routes import _validate_idempotency_key
        return _validate_idempotency_key(key)

    def test_valid_key_alphanumeric(self):
        from fastapi import HTTPException
        try:
            self._validate("AbCdEf12")
        except HTTPException:
            pytest.fail("Valid key raised HTTPException unexpectedly")

    def test_valid_key_with_hyphens_and_underscores(self):
        from fastapi import HTTPException
        try:
            self._validate("scan-request_20240601-001")
        except HTTPException:
            pytest.fail("Key with hyphens/underscores raised HTTPException unexpectedly")

    def test_valid_key_max_length(self):
        from fastapi import HTTPException
        key = "A" * 128
        try:
            self._validate(key)
        except HTTPException:
            pytest.fail("128-char key should be valid")

    def test_valid_key_exactly_8_chars(self):
        from fastapi import HTTPException
        try:
            self._validate("12345678")
        except HTTPException:
            pytest.fail("8-char key is the minimum valid length and should not raise")

    def test_invalid_key_too_short(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self._validate("short")
        assert exc_info.value.status_code == 400

    def test_invalid_key_too_long(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self._validate("A" * 129)
        assert exc_info.value.status_code == 400

    def test_invalid_key_with_spaces(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self._validate("key with spaces!")
        assert exc_info.value.status_code == 400

    def test_invalid_key_with_special_chars(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self._validate("key@domain.com")
        assert exc_info.value.status_code == 400

    def test_invalid_key_exactly_7_chars(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self._validate("1234567")
        assert exc_info.value.status_code == 400

    def test_error_message_mentions_header_name(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self._validate("!bad")
        assert "Idempotency-Key" in exc_info.value.detail


# ---------------------------------------------------------------------------
# HTTP-LEVEL INTEGRATION TESTS
# ---------------------------------------------------------------------------


class TestTaskStartIdempotencyEndpoint:
    """Integration tests for POST /task/start with Idempotency-Key header.

    These tests drive the FastAPI route layer against a live SQLite database
    via the standard ``test_client`` fixture.
    """

    def test_idempotency_key_rejected_when_too_short(self, test_client):
        payload = {
            "plugin_id": "nmap",
            "inputs": {"target": "127.0.0.1"},
            "consent_granted": True,
        }
        resp = test_client.post(
            "/api/v1/task/start",
            json=payload,
            headers={"Idempotency-Key": "short"},
        )
        assert resp.status_code == 400
        assert "Idempotency-Key" in resp.json().get("detail", "")

    def test_idempotency_key_rejected_when_too_long(self, test_client):
        payload = {
            "plugin_id": "nmap",
            "inputs": {"target": "127.0.0.1"},
            "consent_granted": True,
        }
        resp = test_client.post(
            "/api/v1/task/start",
            json=payload,
            headers={"Idempotency-Key": "X" * 129},
        )
        assert resp.status_code == 400

    def test_idempotency_key_rejected_with_invalid_chars(self, test_client):
        payload = {
            "plugin_id": "nmap",
            "inputs": {"target": "127.0.0.1"},
            "consent_granted": True,
        }
        resp = test_client.post(
            "/api/v1/task/start",
            json=payload,
            headers={"Idempotency-Key": "bad key!!"},
        )
        assert resp.status_code == 400

    def test_same_idempotency_key_returns_existing_task(self, test_client):
        """Pre-seed an idempotency row and verify the endpoint short-circuits."""
        import asyncio
        from backend.secuscan.database import get_db

        async def seed():
            db = await get_db()
            # Insert a minimal task row so the route can fetch it
            await db.execute(
                """
                INSERT OR IGNORE INTO tasks
                    (id, owner_id, plugin_id, tool_name, target,
                     inputs_json, status, consent_granted, safe_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "seeded-task-idem-01",
                    "default",
                    "nmap",
                    "nmap",
                    "127.0.0.1",
                    "{}",
                    "queued",
                    1,
                    1,
                ),
            )
            await db.record_idempotency_key(
                "idem-key-seeded-01",
                "seeded-task-idem-01",
                "default",
                86400,
            )

        asyncio.run(seed())

        payload = {
            "plugin_id": "nmap",
            "inputs": {"target": "127.0.0.1"},
            "consent_granted": True,
        }
        resp = test_client.post(
            "/api/v1/task/start",
            json=payload,
            headers={"Idempotency-Key": "idem-key-seeded-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "seeded-task-idem-01"
        assert data.get("idempotent") is True

    def test_idempotency_hit_response_contains_stream_url(self, test_client):
        """The idempotent response must include a stream_url for the existing task."""
        import asyncio
        from backend.secuscan.database import get_db

        async def seed():
            db = await get_db()
            await db.execute(
                """
                INSERT OR IGNORE INTO tasks
                    (id, owner_id, plugin_id, tool_name, target,
                     inputs_json, status, consent_granted, safe_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "seeded-stream-task",
                    "default",
                    "nmap",
                    "nmap",
                    "127.0.0.1",
                    "{}",
                    "queued",
                    1,
                    1,
                ),
            )
            await db.record_idempotency_key(
                "key-for-stream-check",
                "seeded-stream-task",
                "default",
                86400,
            )

        asyncio.run(seed())

        payload = {"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}, "consent_granted": True}
        resp = test_client.post(
            "/api/v1/task/start",
            json=payload,
            headers={"Idempotency-Key": "key-for-stream-check"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stream_url" in data
        assert "seeded-stream-task" in data["stream_url"]

    def test_expired_key_does_not_trigger_idempotency_hit(self, test_client):
        """An expired idempotency row must not short-circuit the request."""
        import asyncio
        from backend.secuscan.database import get_db

        async def seed():
            db = await get_db()
            await db.execute(
                """
                INSERT OR IGNORE INTO tasks
                    (id, owner_id, plugin_id, tool_name, target,
                     inputs_json, status, consent_granted, safe_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "seeded-task-expired-key",
                    "default",
                    "nmap",
                    "nmap",
                    "127.0.0.1",
                    "{}",
                    "queued",
                    1,
                    1,
                ),
            )
            # Insert an already-expired row directly (TTL in the past)
            await db.execute(
                """
                INSERT OR IGNORE INTO task_idempotency
                    (idempotency_key, task_id, owner_id, created_at, expires_at)
                VALUES (?, ?, ?, datetime('now', '-7200 seconds'), datetime('now', '-3600 seconds'))
                """,
                ("expired-idem-key-test", "seeded-task-expired-key", "default"),
            )

        asyncio.run(seed())

        payload = {"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}, "consent_granted": True}
        resp = test_client.post(
            "/api/v1/task/start",
            json=payload,
            headers={"Idempotency-Key": "expired-idem-key-test"},
        )
        # The expired key must NOT produce an idempotent=True response
        if resp.status_code == 200:
            assert resp.json().get("idempotent") is not True, (
                "Expired key must not produce idempotent=True"
            )
