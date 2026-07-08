"""
Unit tests for API key rotation and expiry (issue #1619).

The client API key file previously had no created_at, TTL, or rotation
path -- once issued it was valid forever with no way to revoke it short of
deleting the file and restarting the process. These tests cover:

- The key file now stores created_at alongside the key (JSON format).
- A pre-existing plaintext key file is migrated in place without losing
  the key itself.
- POST /admin/api-key/rotate invalidates the old key immediately and
  returns a usable new one.
- GET /admin/api-key/status reports age/expiry without exposing the key.
- SECUSCAN_API_KEY_TTL_SECONDS rejects requests once the key is stale.
- Both admin endpoints are gated by the *admin* key, not the client key.
"""

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from backend.secuscan import auth as auth_module
from backend.secuscan.main import app
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.plugins import init_plugins


ADMIN_KEY = "valid-admin-key-for-rotation-tests"


@pytest.fixture()
def client_with_key(setup_test_environment, monkeypatch):
    """TestClient with a valid client API key pre-seeded and a valid
    (>= 16 char) admin key, since verify_admin_access rejects the
    conftest default ("test-admin-key", 14 chars) as too weak."""
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    asyncio.run(init_db(settings.database_path))
    asyncio.run(init_plugins(settings.plugins_dir))
    api_key = auth_module.init_api_key(settings.data_dir)
    with TestClient(app) as c:
        yield c, api_key


class TestKeyFileFormat:
    def test_key_file_stores_created_at(self, tmp_path):
        auth_module.init_api_key(str(tmp_path))
        data = json.loads((tmp_path / ".api_key").read_text())
        assert "key" in data
        assert "created_at" in data
        assert isinstance(data["created_at"], (int, float))

    def test_legacy_plaintext_key_file_is_migrated(self, tmp_path):
        key_file = tmp_path / ".api_key"
        key_file.write_text("legacy-plaintext-key-123")

        loaded = auth_module.init_api_key(str(tmp_path))

        assert loaded == "legacy-plaintext-key-123"
        data = json.loads(key_file.read_text())
        assert data["key"] == "legacy-plaintext-key-123"
        assert isinstance(data["created_at"], (int, float))

    def test_reloading_json_key_file_preserves_created_at(self, tmp_path):
        auth_module.init_api_key(str(tmp_path))
        first = json.loads((tmp_path / ".api_key").read_text())

        auth_module.init_api_key(str(tmp_path))
        second = json.loads((tmp_path / ".api_key").read_text())

        assert first["key"] == second["key"]
        assert first["created_at"] == second["created_at"]


class TestRotateEndpoint:
    def test_rotate_requires_admin_key(self, client_with_key):
        client, _ = client_with_key
        resp = client.post("/api/v1/admin/api-key/rotate", headers={})
        assert resp.status_code == 401

    def test_client_key_cannot_rotate_itself(self, client_with_key):
        client, api_key = client_with_key
        resp = client.post("/api/v1/admin/api-key/rotate", headers={"X-API-Key": api_key})
        assert resp.status_code == 401

    def test_rotate_returns_new_key(self, client_with_key):
        client, old_key = client_with_key
        resp = client.post("/api/v1/admin/api-key/rotate", headers={"X-API-Key": ADMIN_KEY})
        assert resp.status_code == 200
        body = resp.json()
        assert "key" in body
        assert body["key"] != old_key
        assert len(body["key"]) == 64  # 32 bytes -> 64 hex chars

    def test_old_key_rejected_immediately_after_rotation(self, client_with_key):
        client, old_key = client_with_key
        client.post("/api/v1/admin/api-key/rotate", headers={"X-API-Key": ADMIN_KEY})

        resp = client.get("/api/v1/plugins", headers={"X-Api-Key": old_key})
        assert resp.status_code == 401

    def test_new_key_works_after_rotation(self, client_with_key):
        client, _ = client_with_key
        rotate_resp = client.post("/api/v1/admin/api-key/rotate", headers={"X-API-Key": ADMIN_KEY})
        new_key = rotate_resp.json()["key"]

        resp = client.get("/api/v1/plugins", headers={"X-Api-Key": new_key})
        assert resp.status_code == 200

    def test_rotation_persists_to_disk(self, client_with_key):
        client, _ = client_with_key
        rotate_resp = client.post("/api/v1/admin/api-key/rotate", headers={"X-API-Key": ADMIN_KEY})
        new_key = rotate_resp.json()["key"]

        on_disk = json.loads((__import__("pathlib").Path(settings.data_dir) / ".api_key").read_text())
        assert on_disk["key"] == new_key


class TestStatusEndpoint:
    def test_status_requires_admin_key(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/api/v1/admin/api-key/status", headers={})
        assert resp.status_code == 401

    def test_status_reports_age_without_exposing_key(self, client_with_key):
        client, api_key = client_with_key
        resp = client.get("/api/v1/admin/api-key/status", headers={"X-API-Key": ADMIN_KEY})
        assert resp.status_code == 200
        body = resp.json()
        assert "created_at" in body
        assert "age_seconds" in body
        assert body["age_seconds"] >= 0
        assert api_key not in json.dumps(body)

    def test_status_ttl_disabled_by_default(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/api/v1/admin/api-key/status", headers={"X-API-Key": ADMIN_KEY})
        body = resp.json()
        assert body["ttl_seconds"] is None
        assert body["expired"] is False


class TestTTLExpiry:
    def test_expired_key_rejected(self, client_with_key, monkeypatch):
        client, api_key = client_with_key
        monkeypatch.setattr(settings, "api_key_ttl_seconds", 1)
        # Backdate the in-memory created_at so the key reads as already expired.
        monkeypatch.setattr(auth_module, "_api_key_created_at", time.time() - 10)

        resp = client.get("/api/v1/plugins", headers={"X-Api-Key": api_key})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_non_expired_key_within_ttl_is_accepted(self, client_with_key, monkeypatch):
        client, api_key = client_with_key
        monkeypatch.setattr(settings, "api_key_ttl_seconds", 3600)
        monkeypatch.setattr(auth_module, "_api_key_created_at", time.time())

        resp = client.get("/api/v1/plugins", headers={"X-Api-Key": api_key})
        assert resp.status_code == 200

    def test_session_creation_rejects_expired_key(self, client_with_key, monkeypatch):
        client, api_key = client_with_key
        monkeypatch.setattr(settings, "api_key_ttl_seconds", 1)
        monkeypatch.setattr(auth_module, "_api_key_created_at", time.time() - 10)

        resp = client.post("/api/v1/auth/session", headers={"X-Api-Key": api_key})
        assert resp.status_code == 401
