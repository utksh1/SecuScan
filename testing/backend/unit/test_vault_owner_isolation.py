"""
Vault owner-isolation tests.

Verifies that credential vault operations are scoped by owner_id and
that one owner cannot read, list, overwrite, or delete another owner's
secrets.
"""

import asyncio
import pytest

from backend.secuscan.config import settings
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


class TestVaultOwnerIsolation:
    OWNER_A = {"X-User-Id": "alice"}
    OWNER_B = {"X-User-Id": "bob"}

    def test_owner_cannot_read_other_owner_secret(self, test_client):
        name = "owner-isolation-read"

        r = test_client.put(
            f"/api/v1/vault/{name}",
            json={"value": "alice-secret"},
            headers=self.OWNER_A,
        )
        assert r.status_code == 200

        r = test_client.get(
            f"/api/v1/vault/{name}",
            headers=self.OWNER_B,
        )

        assert r.status_code == 404

    def test_owner_list_only_returns_owned_secrets(self, test_client):
        test_client.put(
            "/api/v1/vault/alice-secret",
            json={"value": "a"},
            headers=self.OWNER_A,
        )

        test_client.put(
            "/api/v1/vault/bob-secret",
            json={"value": "b"},
            headers=self.OWNER_B,
        )

        r = test_client.get(
            "/api/v1/vault",
            headers=self.OWNER_B,
        )

        assert r.status_code == 200
        print(r.json())

        names = {item["name"] for item in r.json()["items"]}

        assert "bob-secret" in names
        assert "alice-secret" not in names

    def test_owner_cannot_overwrite_other_owner_secret(self, test_client):
        name = "shared-name"

        test_client.put(
            f"/api/v1/vault/{name}",
            json={"value": "alice-value"},
            headers=self.OWNER_A,
        )

        test_client.put(
            f"/api/v1/vault/{name}",
            json={"value": "bob-value"},
            headers=self.OWNER_B,
        )

        alice = test_client.get(
            f"/api/v1/vault/{name}",
            headers=self.OWNER_A,
        )

        bob = test_client.get(
            f"/api/v1/vault/{name}",
            headers=self.OWNER_B,
        )

        assert alice.status_code == 200
        assert bob.status_code == 200

        assert alice.json()["value"] == "alice-value"
        assert bob.json()["value"] == "bob-value"

    def test_owner_cannot_delete_other_owner_secret(self, test_client):
        name = "owner-isolation-delete"

        test_client.put(
            f"/api/v1/vault/{name}",
            json={"value": "alice-secret"},
            headers=self.OWNER_A,
        )

        delete_r = test_client.delete(
           f"/api/v1/vault/{name}",
           headers=self.OWNER_B,
      )
        assert delete_r.status_code in (200, 404)

        r = test_client.get(
            f"/api/v1/vault/{name}",
            headers=self.OWNER_A,
        )

        assert r.status_code == 200
        assert r.json()["value"] == "alice-secret"