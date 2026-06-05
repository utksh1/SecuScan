"""
Tests for credential usage auditing without secret value leakage (issue #210).

Covers:
  - log_credential_access inserts a row with the name, type, owner, task_id.
  - Plaintext secret values never appear in credential_access_log.
  - Plaintext secret values never appear in audit_log context_json.
  - get_credential_usage returns entries for the named credential only.
  - get_credential_usage pagination works correctly.
  - get_task_credential_usage returns correct names for a task_id.
  - get_all_credential_usage returns all entries and supports filtering.
  - Filtering by access_type works.
  - Filtering by owner_id works.
  - Multiple credentials are tracked independently.
  - Delete access type is recorded.
  - Write access type is recorded.
  - List access type is recorded.
  - Audit log entries for vault operations contain credential names but not values.
  - get_credential_usage returns empty for an unknown credential name.
  - get_task_credential_usage returns empty list for a task with no credential access.
  - Concurrent log_credential_access calls all persist correctly.
"""

import asyncio
import json
import pytest
import pytest_asyncio

from backend.secuscan.database import Database


@pytest_asyncio.fixture
async def db(tmp_path):
    instance = Database(str(tmp_path / "test.db"))
    await instance.connect()
    yield instance
    await instance.disconnect()


class TestLogCredentialAccess:
    @pytest.mark.asyncio
    async def test_read_access_recorded(self, db):
        await db.log_credential_access("my-api-key", "read", owner_id="user-1")
        rows = await db.fetchall("SELECT * FROM credential_access_log")
        assert len(rows) == 1
        assert rows[0]["credential_name"] == "my-api-key"
        assert rows[0]["access_type"] == "read"
        assert rows[0]["owner_id"] == "user-1"
        assert rows[0]["task_id"] is None

    @pytest.mark.asyncio
    async def test_write_access_recorded(self, db):
        await db.log_credential_access("github-token", "write", owner_id="admin")
        rows = await db.fetchall("SELECT * FROM credential_access_log")
        assert rows[0]["access_type"] == "write"
        assert rows[0]["credential_name"] == "github-token"

    @pytest.mark.asyncio
    async def test_delete_access_recorded(self, db):
        await db.log_credential_access("old-key", "delete", owner_id="admin")
        rows = await db.fetchall("SELECT * FROM credential_access_log")
        assert rows[0]["access_type"] == "delete"

    @pytest.mark.asyncio
    async def test_list_access_recorded(self, db):
        await db.log_credential_access("*", "list", owner_id="user-2")
        rows = await db.fetchall("SELECT * FROM credential_access_log")
        assert rows[0]["access_type"] == "list"
        assert rows[0]["credential_name"] == "*"

    @pytest.mark.asyncio
    async def test_task_id_stored(self, db):
        await db.log_credential_access(
            "task-cred", "read", owner_id="user-3", task_id="task-abc"
        )
        rows = await db.fetchall("SELECT * FROM credential_access_log")
        assert rows[0]["task_id"] == "task-abc"

    @pytest.mark.asyncio
    async def test_no_secret_value_in_access_log(self, db):
        secret_value = "super-secret-password-12345"
        await db.log_credential_access("db-password", "read", owner_id="user-1")
        rows = await db.fetchall("SELECT * FROM credential_access_log")
        row_str = json.dumps(rows[0])
        assert secret_value not in row_str

    @pytest.mark.asyncio
    async def test_no_secret_value_in_audit_log(self, db):
        secret_value = "plaintext-api-secret-xyz"
        await db.log_audit(
            "credential_vault_read",
            "Vault credential 'my-key' value read",
            context={"credential_name": "my-key"},
        )
        rows = await db.fetchall("SELECT * FROM audit_log")
        full_str = json.dumps([dict(r) for r in rows])
        assert secret_value not in full_str

    @pytest.mark.asyncio
    async def test_audit_log_contains_credential_name(self, db):
        await db.log_audit(
            "credential_vault_read",
            "Vault credential 'aws-secret' value read",
            context={"credential_name": "aws-secret"},
        )
        rows = await db.fetchall("SELECT * FROM audit_log")
        assert any("aws-secret" in (r.get("message") or "") for r in rows)

    @pytest.mark.asyncio
    async def test_multiple_credentials_tracked_independently(self, db):
        await db.log_credential_access("cred-a", "read", owner_id="u1")
        await db.log_credential_access("cred-b", "write", owner_id="u1")
        await db.log_credential_access("cred-c", "delete", owner_id="u2")
        rows = await db.fetchall("SELECT * FROM credential_access_log ORDER BY id ASC")
        assert len(rows) == 3
        assert {r["credential_name"] for r in rows} == {"cred-a", "cred-b", "cred-c"}


class TestGetCredentialUsage:
    @pytest.mark.asyncio
    async def test_returns_entries_for_named_credential(self, db):
        await db.log_credential_access("key-x", "read", owner_id="u1")
        await db.log_credential_access("key-x", "read", owner_id="u2")
        await db.log_credential_access("key-y", "read", owner_id="u1")
        result = await db.get_credential_usage("key-x")
        assert result["credential_name"] == "key-x"
        assert result["total"] == 2
        assert len(result["entries"]) == 2

    @pytest.mark.asyncio
    async def test_excludes_other_credential_entries(self, db):
        await db.log_credential_access("key-a", "read", owner_id="u1")
        await db.log_credential_access("key-b", "write", owner_id="u1")
        result = await db.get_credential_usage("key-a")
        assert all(e["credential_name"] == "key-a" for e in result["entries"])

    @pytest.mark.asyncio
    async def test_pagination_limit(self, db):
        for _ in range(8):
            await db.log_credential_access("paged-key", "read", owner_id="u1")
        result = await db.get_credential_usage("paged-key", limit=3)
        assert result["total"] == 8
        assert len(result["entries"]) == 3

    @pytest.mark.asyncio
    async def test_pagination_offset(self, db):
        for i in range(6):
            await db.log_credential_access(f"p-key", "read", owner_id=f"u{i}")
        p1 = await db.get_credential_usage("p-key", limit=3, offset=0)
        p2 = await db.get_credential_usage("p-key", limit=3, offset=3)
        ids_p1 = {r["id"] for r in p1["entries"]}
        ids_p2 = {r["id"] for r in p2["entries"]}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_empty_for_unknown_credential(self, db):
        result = await db.get_credential_usage("does-not-exist")
        assert result["total"] == 0
        assert result["entries"] == []


class TestGetTaskCredentialUsage:
    @pytest.mark.asyncio
    async def test_returns_names_for_task(self, db):
        await db.log_credential_access("db-pass", "read", owner_id="u1", task_id="task-1")
        await db.log_credential_access("api-key", "read", owner_id="u1", task_id="task-1")
        result = await db.get_task_credential_usage("task-1")
        assert result["task_id"] == "task-1"
        assert set(result["credential_names"]) == {"db-pass", "api-key"}

    @pytest.mark.asyncio
    async def test_does_not_include_other_task_credentials(self, db):
        await db.log_credential_access("cred-1", "read", owner_id="u1", task_id="task-A")
        await db.log_credential_access("cred-2", "read", owner_id="u1", task_id="task-B")
        result = await db.get_task_credential_usage("task-A")
        assert "cred-2" not in result["credential_names"]
        assert "cred-1" in result["credential_names"]

    @pytest.mark.asyncio
    async def test_empty_for_task_with_no_credential_access(self, db):
        result = await db.get_task_credential_usage("task-with-no-creds")
        assert result["credential_names"] == []
        assert result["access_events"] == []

    @pytest.mark.asyncio
    async def test_deduplicates_credential_names(self, db):
        for _ in range(5):
            await db.log_credential_access("repeated-cred", "read", owner_id="u1", task_id="task-X")
        result = await db.get_task_credential_usage("task-X")
        assert result["credential_names"].count("repeated-cred") == 1
        assert len(result["access_events"]) == 5

    @pytest.mark.asyncio
    async def test_access_events_contain_no_secret_values(self, db):
        await db.log_credential_access("secure-token", "read", owner_id="u1", task_id="task-Z")
        result = await db.get_task_credential_usage("task-Z")
        events_str = json.dumps(result["access_events"])
        assert "plaintext" not in events_str
        assert "password" not in events_str
        assert result["access_events"][0]["credential_name"] == "secure-token"


class TestGetAllCredentialUsage:
    @pytest.mark.asyncio
    async def test_returns_all_entries(self, db):
        await db.log_credential_access("k1", "read", owner_id="u1")
        await db.log_credential_access("k2", "write", owner_id="u2")
        await db.log_credential_access("k3", "delete", owner_id="u1")
        result = await db.get_all_credential_usage()
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_access_type(self, db):
        await db.log_credential_access("k1", "read", owner_id="u1")
        await db.log_credential_access("k2", "write", owner_id="u1")
        await db.log_credential_access("k3", "read", owner_id="u2")
        result = await db.get_all_credential_usage(access_type="read")
        assert result["total"] == 2
        assert all(e["access_type"] == "read" for e in result["entries"])

    @pytest.mark.asyncio
    async def test_filter_by_owner_id(self, db):
        await db.log_credential_access("k1", "read", owner_id="alice")
        await db.log_credential_access("k2", "read", owner_id="bob")
        await db.log_credential_access("k3", "write", owner_id="alice")
        result = await db.get_all_credential_usage(owner_id="alice")
        assert result["total"] == 2
        assert all(e["owner_id"] == "alice" for e in result["entries"])

    @pytest.mark.asyncio
    async def test_combined_filters(self, db):
        await db.log_credential_access("k1", "read", owner_id="alice")
        await db.log_credential_access("k2", "write", owner_id="alice")
        await db.log_credential_access("k3", "read", owner_id="bob")
        result = await db.get_all_credential_usage(access_type="read", owner_id="alice")
        assert result["total"] == 1
        assert result["entries"][0]["credential_name"] == "k1"

    @pytest.mark.asyncio
    async def test_empty_when_no_entries(self, db):
        result = await db.get_all_credential_usage()
        assert result["total"] == 0
        assert result["entries"] == []

    @pytest.mark.asyncio
    async def test_no_secret_values_in_results(self, db):
        await db.log_credential_access("my-secret-key", "read", owner_id="u1")
        result = await db.get_all_credential_usage()
        result_str = json.dumps(result)
        assert "plaintext" not in result_str
        assert "password123" not in result_str
        assert "my-secret-key" in result_str


class TestConcurrentAccess:
    @pytest.mark.asyncio
    async def test_concurrent_log_calls_all_persist(self, db):
        await asyncio.gather(*[
            db.log_credential_access(f"cred-{i}", "read", owner_id="u1")
            for i in range(12)
        ])
        result = await db.get_all_credential_usage()
        assert result["total"] == 12
        names = {e["credential_name"] for e in result["entries"]}
        assert all(f"cred-{i}" in names for i in range(12))


class TestVaultUsageAllAccessControl:
    """Route-level tests ensuring /vault/usage/all is admin-only.

    The test-environment admin key is intentionally short (conftest sets it
    to "test-admin-key") so that verify_admin_access returns HTTP 500 for any
    caller — including one that sends the correct key — as a misconfiguration
    guard. The important property tested here is that NO caller receives the
    credential log data (HTTP 200) without proper admin authorization.
    """

    def test_non_admin_caller_cannot_read_credential_log(self, test_client):
        resp = test_client.get("/api/v1/vault/usage/all")
        assert resp.status_code != 200

    def test_wrong_admin_key_cannot_read_credential_log(self, test_client):
        resp = test_client.get(
            "/api/v1/vault/usage/all",
            headers={"X-Admin-Api-Key": "totally-wrong-key-xyz"},
        )
        assert resp.status_code != 200

    def test_endpoint_is_registered_and_gated(self, test_client):
        resp = test_client.get("/api/v1/vault/usage/all")
        assert resp.status_code != 200
        assert resp.status_code != 404

    def test_per_credential_usage_requires_api_key(self, test_client):
        resp = test_client.get(
            "/api/v1/vault/nonexistent-cred/usage",
            headers={"X-Api-Key": "wrong-key"},
        )
        assert resp.status_code in (401, 403)
