"""
Vault owner-isolation tests.

Verifies that credential vault operations are scoped by owner_id.
Since X-User-Id is not trusted for ownership (security fix), isolation is
verified by seeding data directly with different owner_ids and confirming the
API only exposes data belonging to the authenticated principal (DEFAULT_OWNER_ID).
"""

import asyncio
import sqlite3
import pytest

from backend.secuscan.config import settings
from backend.secuscan.auth import DEFAULT_OWNER_ID
from backend.secuscan.ratelimit import (
    reset_all_endpoint_limiters,
    vault_limiter,
)


@pytest.fixture(autouse=True)
def isolate_vault_tests(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_vault_limit", 100)
    monkeypatch.setattr(settings, "rate_limit_vault_window", 60)

    vault_limiter.limit = 100
    vault_limiter.window_seconds = 60

    asyncio.run(reset_all_endpoint_limiters())


def _seed_vault_secret(owner_id: str, name: str, encrypted_value: str) -> None:
    """Insert a vault secret directly with an explicit owner_id."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT INTO credential_vault (name, owner_id, encrypted_value) VALUES (?, ?, ?)",
            (name, owner_id, encrypted_value),
        )
        conn.commit()
    finally:
        conn.close()


class TestVaultOwnerIsolation:
    """Test that vault CRUD is scoped by the authenticated owner."""

    def test_read_does_not_expose_other_owner_secret(self, test_client):
        """Secrets seeded under a different owner are invisible via the API."""
        other_owner = "user:other-tenant"
        _seed_vault_secret(other_owner, "other-secret", "encrypted-blob")

        r = test_client.get("/api/v1/vault/other-secret")
        assert r.status_code == 404

    def test_list_only_returns_authenticated_owner_secrets(self, test_client):
        """Listing only returns secrets belonging to the authenticated owner."""
        other_owner = "user:other-tenant"
        _seed_vault_secret(other_owner, "other-secret-1", "encrypted-1")

        r = test_client.get("/api/v1/vault")
        assert r.status_code == 200
        names = {item["name"] for item in r.json()["items"]}
        assert "other-secret-1" not in names

    def test_delete_does_not_remove_other_owner_secret(self, test_client):
        """Deleting as authenticated owner does not affect other owner's secrets."""
        other_owner = "user:other-tenant"
        _seed_vault_secret(other_owner, "other-secret-del", "encrypted-del")

        r = test_client.delete("/api/v1/vault/other-secret-del")
        assert r.status_code == 404

        # Verify the secret still exists in the DB
        conn = sqlite3.connect(settings.database_path)
        try:
            cur = conn.execute(
                "SELECT 1 FROM credential_vault WHERE name = ? AND owner_id = ?",
                ("other-secret-del", other_owner),
            )
            assert cur.fetchone() is not None
        finally:
            conn.close()

    def test_upsert_updates_existing_secret_for_same_owner(self, test_client):
        name = "duplicate-secret"

        test_client.put(
            f"/api/v1/vault/{name}",
            json={"value": "first"},
        )

        test_client.put(
            f"/api/v1/vault/{name}",
            json={"value": "second"},
        )

        secret = test_client.get(f"/api/v1/vault/{name}")

        assert secret.status_code == 200
        assert secret.json()["value"] == "second"

        listing = test_client.get("/api/v1/vault")

        matches = [
            item
            for item in listing.json()["items"]
            if item["name"] == name
        ]

        assert len(matches) == 1

    def test_x_user_id_spoofing_cannot_access_other_owner_vault(self, test_client):
        """Spoofed X-User-Id header cannot access another owner's vault secrets."""
        other_owner = "user:victim"
        _seed_vault_secret(other_owner, "victim-secret", "stolen-credentials")

        r = test_client.get(
            "/api/v1/vault/victim-secret",
            headers={"X-User-Id": "victim"},
        )
        assert r.status_code == 404, (
            "Spoofed X-User-Id header allowed access to another owner's vault secret"
        )
