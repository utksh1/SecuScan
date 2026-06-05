"""
Tests for tamper-evident audit log hash chaining (issue #207).

Covers:
  - Hash is written on every log_audit call.
  - The chain is valid for a clean sequence of events.
  - Modifying a row's message is detected as 'modified'.
  - Deleting a row from the middle is detected as 'gap'.
  - Reordering rows (simulated by swapping entry_hash values) is detected.
  - Pre-migration rows (all-zeros in both columns) are skipped without false positives.
  - Concurrent log_audit calls produce a linear chain with no forked prev_hash.
  - get_audit_log returns entries and the correct total count.
  - Filters (event_type, severity, task_id) restrict get_audit_log correctly.
  - verify_audit_chain returns ok=True for an empty log.
  - sentinel rows (zeros in entry_hash only) are flagged.
"""

import asyncio
import pytest
import pytest_asyncio

from backend.secuscan.database import Database, _GENESIS_HASH, _compute_entry_hash


@pytest_asyncio.fixture
async def db(tmp_path):
    instance = Database(str(tmp_path / "test.db"))
    await instance.connect()
    yield instance
    await instance.disconnect()


async def _write_event(db: Database, event_type: str = "test_event", message: str = "msg",
                       severity: str = "info", task_id: str = None, plugin_id: str = None):
    await db.log_audit(event_type, message, severity=severity,
                       task_id=task_id, plugin_id=plugin_id)


def _recompute_hash(row: dict) -> str:
    return _compute_entry_hash(
        row_id=row["id"],
        timestamp=row["timestamp"],
        event_type=row["event_type"],
        severity=row["severity"],
        user_id=row.get("user_id"),
        ip_address=row.get("ip_address"),
        message=row["message"],
        context_json=row.get("context_json"),
        task_id=row.get("task_id"),
        plugin_id=row.get("plugin_id"),
        prev_hash=row["prev_hash"],
    )


class TestChainIntegrity:
    @pytest.mark.asyncio
    async def test_first_row_anchors_to_genesis(self, db):
        await _write_event(db, "login", "user logged in")
        row = await db.fetchone("SELECT * FROM audit_log ORDER BY id ASC LIMIT 1")
        assert row["prev_hash"] == _GENESIS_HASH
        assert row["entry_hash"] != _GENESIS_HASH
        assert len(row["entry_hash"]) == 64

    @pytest.mark.asyncio
    async def test_each_row_links_to_predecessor(self, db):
        for i in range(5):
            await _write_event(db, f"event_{i}", f"message {i}")
        rows = await db.fetchall("SELECT * FROM audit_log ORDER BY id ASC")
        assert rows[0]["prev_hash"] == _GENESIS_HASH
        for idx in range(1, len(rows)):
            assert rows[idx]["prev_hash"] == rows[idx - 1]["entry_hash"], (
                f"Row {rows[idx]['id']} prev_hash does not match row {rows[idx-1]['id']} entry_hash"
            )

    @pytest.mark.asyncio
    async def test_entry_hash_matches_recomputed(self, db):
        for i in range(4):
            await _write_event(db, "scan_started", f"target {i}")
        rows = await db.fetchall("SELECT * FROM audit_log ORDER BY id ASC")
        for row in rows:
            assert row["entry_hash"] == _recompute_hash(row)

    @pytest.mark.asyncio
    async def test_clean_chain_verifies_ok(self, db):
        for i in range(6):
            await _write_event(db, "task_complete", f"task {i} done", severity="info")
        report = await db.verify_audit_chain()
        assert report["ok"] is True
        assert report["rows_checked"] == 6
        assert report["chain_breaks"] == []

    @pytest.mark.asyncio
    async def test_empty_log_verifies_ok(self, db):
        report = await db.verify_audit_chain()
        assert report["ok"] is True
        assert report["total_rows"] == 0
        assert report["chain_breaks"] == []


class TestTamperDetection:
    @pytest.mark.asyncio
    async def test_modified_row_detected(self, db):
        for i in range(4):
            await _write_event(db, "scan", f"original message {i}")
        # Tamper with a middle row without updating its hash.
        await db.connection.execute(
            "UPDATE audit_log SET message = 'TAMPERED' WHERE id = (SELECT id FROM audit_log ORDER BY id LIMIT 1 OFFSET 1)"
        )
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is False
        reasons = {b["reason"] for b in report["chain_breaks"]}
        assert "modified" in reasons

    @pytest.mark.asyncio
    async def test_deleted_row_detected_as_gap(self, db):
        for i in range(5):
            await _write_event(db, "event", f"msg {i}")
        rows = await db.fetchall("SELECT id FROM audit_log ORDER BY id ASC")
        middle_id = rows[2]["id"]
        await db.connection.execute("DELETE FROM audit_log WHERE id = ?", (middle_id,))
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is False
        reasons = {b["reason"] for b in report["chain_breaks"]}
        assert "gap" in reasons

    @pytest.mark.asyncio
    async def test_reordered_rows_detected(self, db):
        for i in range(4):
            await _write_event(db, "event", f"msg {i}")
        rows = await db.fetchall("SELECT id, entry_hash FROM audit_log ORDER BY id ASC")
        # Swap the entry_hash of rows 0 and 1 to simulate reordering.
        id_a, hash_a = rows[0]["id"], rows[0]["entry_hash"]
        id_b, hash_b = rows[1]["id"], rows[1]["entry_hash"]
        await db.connection.execute("UPDATE audit_log SET entry_hash = ? WHERE id = ?", (hash_b, id_a))
        await db.connection.execute("UPDATE audit_log SET entry_hash = ? WHERE id = ?", (hash_a, id_b))
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is False

    @pytest.mark.asyncio
    async def test_first_row_tampered_detected(self, db):
        await _write_event(db, "login", "first event")
        await _write_event(db, "login", "second event")
        await db.connection.execute(
            "UPDATE audit_log SET message = 'HACKED' WHERE id = (SELECT MIN(id) FROM audit_log)"
        )
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is False
        reasons = {b["reason"] for b in report["chain_breaks"]}
        assert "modified" in reasons

    @pytest.mark.asyncio
    async def test_last_row_tampered_detected(self, db):
        for i in range(3):
            await _write_event(db, "event", f"msg {i}")
        await db.connection.execute(
            "UPDATE audit_log SET message = 'ALTERED' WHERE id = (SELECT MAX(id) FROM audit_log)"
        )
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is False

    @pytest.mark.asyncio
    async def test_all_rows_deleted_verifies_ok(self, db):
        for i in range(3):
            await _write_event(db, "event", f"msg {i}")
        await db.connection.execute("DELETE FROM audit_log")
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is True
        assert report["total_rows"] == 0


class TestPreMigrationRows:
    @pytest.mark.asyncio
    async def test_sentinel_rows_skipped(self, db):
        # Insert two rows that look like pre-migration (both hash fields are zeros).
        await db.connection.execute(
            "INSERT INTO audit_log (event_type, severity, message, prev_hash, entry_hash) "
            "VALUES ('old_event', 'info', 'pre-migration msg', ?, ?)",
            (_GENESIS_HASH, _GENESIS_HASH),
        )
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is True
        assert report["pre_migration_rows"] == 1
        assert report["rows_checked"] == 0

    @pytest.mark.asyncio
    async def test_mixed_old_and_new_rows(self, db):
        # Pre-migration row.
        await db.connection.execute(
            "INSERT INTO audit_log (event_type, severity, message, prev_hash, entry_hash) "
            "VALUES ('legacy', 'info', 'old row', ?, ?)",
            (_GENESIS_HASH, _GENESIS_HASH),
        )
        await db.connection.commit()
        # New rows written through log_audit.
        await _write_event(db, "new_event", "after migration")
        await _write_event(db, "new_event", "second after migration")
        report = await db.verify_audit_chain()
        assert report["ok"] is True
        assert report["pre_migration_rows"] == 1
        assert report["rows_checked"] == 2

    @pytest.mark.asyncio
    async def test_sentinel_only_in_entry_hash_flagged(self, db):
        # Insert a row where prev_hash is real but entry_hash is zeros — update
        # never committed, i.e. a sentinel violation.
        real_prev = "a" * 64
        await db.connection.execute(
            "INSERT INTO audit_log (event_type, severity, message, prev_hash, entry_hash) "
            "VALUES ('bad_insert', 'info', 'incomplete', ?, ?)",
            (real_prev, _GENESIS_HASH),
        )
        await db.connection.commit()
        report = await db.verify_audit_chain()
        assert report["ok"] is False
        reasons = {b["reason"] for b in report["chain_breaks"]}
        assert "sentinel" in reasons


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_writes_produce_linear_chain(self, db):
        # Fire 10 coroutines simultaneously; the lock must serialise them.
        await asyncio.gather(*[
            _write_event(db, f"concurrent_{i}", f"msg {i}") for i in range(10)
        ])
        rows = await db.fetchall("SELECT * FROM audit_log ORDER BY id ASC")
        assert len(rows) == 10
        # The first row must anchor to genesis.
        assert rows[0]["prev_hash"] == _GENESIS_HASH
        # Every subsequent row must link to its predecessor.
        for idx in range(1, len(rows)):
            assert rows[idx]["prev_hash"] == rows[idx - 1]["entry_hash"], (
                f"Broken chain between rows {rows[idx-1]['id']} and {rows[idx]['id']}"
            )
        # Every stored hash must match the recomputed value.
        for row in rows:
            assert row["entry_hash"] == _recompute_hash(row)
        # verify_audit_chain must report ok after concurrent writes.
        report = await db.verify_audit_chain()
        assert report["ok"] is True


class TestGetAuditLog:
    @pytest.mark.asyncio
    async def test_returns_all_rows_and_total(self, db):
        for i in range(5):
            await _write_event(db, "event", f"msg {i}")
        result = await db.get_audit_log(limit=10)
        assert result["total"] == 5
        assert len(result["entries"]) == 5

    @pytest.mark.asyncio
    async def test_pagination(self, db):
        for i in range(8):
            await _write_event(db, "event", f"msg {i}")
        page1 = await db.get_audit_log(limit=3, offset=0)
        page2 = await db.get_audit_log(limit=3, offset=3)
        assert len(page1["entries"]) == 3
        assert len(page2["entries"]) == 3
        ids_p1 = {r["id"] for r in page1["entries"]}
        ids_p2 = {r["id"] for r in page2["entries"]}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_filter_by_event_type(self, db):
        await _write_event(db, "login", "user login")
        await _write_event(db, "logout", "user logout")
        await _write_event(db, "login", "another login")
        result = await db.get_audit_log(event_type="login")
        assert result["total"] == 2
        for entry in result["entries"]:
            assert entry["event_type"] == "login"

    @pytest.mark.asyncio
    async def test_filter_by_severity(self, db):
        await _write_event(db, "err", "problem", severity="error")
        await _write_event(db, "ok", "fine", severity="info")
        await _write_event(db, "warn", "watch", severity="warning")
        result = await db.get_audit_log(severity="error")
        assert result["total"] == 1
        assert result["entries"][0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_filter_by_task_id(self, db):
        await _write_event(db, "task_done", "task A done", task_id="task-aaa")
        await _write_event(db, "task_done", "task B done", task_id="task-bbb")
        result = await db.get_audit_log(task_id="task-aaa")
        assert result["total"] == 1
        assert result["entries"][0]["task_id"] == "task-aaa"

    @pytest.mark.asyncio
    async def test_context_json_parsed(self, db):
        await db.log_audit("ctx_event", "has context", context={"key": "value", "num": 42})
        result = await db.get_audit_log(event_type="ctx_event")
        assert result["entries"][0]["context"]["key"] == "value"
        assert result["entries"][0]["context"]["num"] == 42

    @pytest.mark.asyncio
    async def test_empty_log_returns_zero_total(self, db):
        result = await db.get_audit_log()
        assert result["total"] == 0
        assert result["entries"] == []


class TestHashFunction:
    def test_different_fields_produce_different_hashes(self):
        base = dict(
            row_id=1, timestamp="2024-01-01 00:00:00", event_type="ev",
            severity="info", user_id=None, ip_address=None,
            message="msg", context_json=None, task_id=None,
            plugin_id=None, prev_hash=_GENESIS_HASH,
        )
        h1 = _compute_entry_hash(**base)
        h2 = _compute_entry_hash(**{**base, "message": "DIFFERENT"})
        h3 = _compute_entry_hash(**{**base, "row_id": 2})
        h4 = _compute_entry_hash(**{**base, "prev_hash": "a" * 64})
        assert len({h1, h2, h3, h4}) == 4

    def test_hash_is_deterministic(self):
        kwargs = dict(
            row_id=99, timestamp="2024-06-01 12:00:00", event_type="scan",
            severity="warning", user_id="u1", ip_address="127.0.0.1",
            message="some msg", context_json='{"k":"v"}',
            task_id="tid", plugin_id="pid", prev_hash="b" * 64,
        )
        assert _compute_entry_hash(**kwargs) == _compute_entry_hash(**kwargs)

    def test_genesis_hash_is_all_zeros(self):
        assert _GENESIS_HASH == "0" * 64
        assert len(_GENESIS_HASH) == 64
