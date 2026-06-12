import uuid

import pytest
from fastapi.testclient import TestClient

from backend.secuscan import auth as auth_module
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.main import app
from backend.secuscan.vault import VaultCrypto


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Configure isolated settings
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "raw_output_dir", f"{tmp_path}/raw")
    monkeypatch.setattr(settings, "reports_dir", f"{tmp_path}/reports")
    monkeypatch.setattr(settings, "database_path", f"{tmp_path}/test_secuscan.db")

    # Ensure plugins dir exists for app startup
    repo_root = tmp_path.parent
    monkeypatch.setattr(settings, "plugins_dir", str(repo_root / "plugins"))

    monkeypatch.setattr(settings, "vault_key", "test-vault-key-for-unit-tests-only")
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    monkeypatch.setattr(settings, "enforce_network_policy", False)

    settings.ensure_directories()

    api_key = auth_module.init_api_key(settings.data_dir)
    with TestClient(app, headers={"X-Api-Key": api_key}) as c:
        yield c








def test_rotate_requires_admin_key(tmp_path, monkeypatch):
    # Setup keys
    monkeypatch.setattr(settings, "vault_key_previous", "old-seed")
    monkeypatch.setattr(settings, "vault_key", "new-seed")

    # Create DB
    import asyncio

    async def run():
        await init_db(str(tmp_path / "test_secuscan.db"))
    asyncio.run(run())

    # Insert a vault entry using DB directly
    from backend.secuscan.database import get_db

    async def insert():
        db = await get_db()
        prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
        blob = prev_crypto.encrypt("s3cr3t")
        await db.execute(
            "INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "my-secret", blob, 1),
        )

    asyncio.run(insert())

    api_client_key = auth_module.init_api_key(str(tmp_path))
    with TestClient(app, headers={"X-Api-Key": api_client_key}) as c:
        # No admin header
        r = c.post("/api/v1/vault/rotate")
        assert r.status_code in (401, 403)

        # Wrong admin key
        r2 = c.post(
            "/api/v1/vault/rotate",
            headers={"Authorization": "wrong-admin-key"},
        )
        assert r2.status_code in (401, 403)


def test_rotate_succeeds_with_admin_key(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vault_key_previous", "old-seed")
    monkeypatch.setattr(settings, "vault_key", "new-seed")
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key-1234")

    import asyncio
    async def run_init():
        await init_db(str(tmp_path / "test_secuscan.db"))
    asyncio.run(run_init())

    from backend.secuscan.database import get_db

    async def insert():
        db = await get_db()
        prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
        blob = prev_crypto.encrypt("s3cr3t")
        await db.execute(
            "INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "my-secret", blob, 1),
        )
    asyncio.run(insert())

    api_client_key = auth_module.init_api_key(str(tmp_path))
    with TestClient(app, headers={"X-Api-Key": api_client_key}) as c:
        r = c.post(
            "/api/v1/vault/rotate",
            headers={"Authorization": f"Bearer {settings.admin_api_key}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["rotated"] == 1



