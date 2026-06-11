import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.secuscan import auth as auth_module
from backend.secuscan.config import settings
from backend.secuscan.database import get_db, init_db
from backend.secuscan.main import app
from backend.secuscan.vault import VaultCrypto



def _derive_prev_new_keys(tmp_path, monkeypatch):
    # Keep seeds short; VaultCrypto expects base64url-encoded 32-byte keys.
    # The rotation endpoint derives 32-byte keys internally from seeds.
    monkeypatch.setattr(settings, "vault_key_previous", "old-seed")
    monkeypatch.setattr(settings, "vault_key", "new-seed")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "raw_output_dir", f"{tmp_path}/raw")
    monkeypatch.setattr(settings, "reports_dir", f"{tmp_path}/reports")
    monkeypatch.setattr(settings, "database_path", f"{tmp_path}/test_secuscan.db")

    repo_root = tmp_path.parent
    monkeypatch.setattr(settings, "plugins_dir", str(repo_root / "plugins"))

    # Provide an admin api key for the rotate endpoint
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    monkeypatch.setattr(settings, "enforce_network_policy", False)

    settings.ensure_directories()

    api_key = auth_module.init_api_key(settings.data_dir)
    with TestClient(app, headers={"X-Api-Key": api_key}) as c:
        yield c


def _insert_vault_plaintext(tmp_path, plaintext: str, *, monkeypatch):
    async def _run():
        await init_db(str(tmp_path / "test_secuscan.db"))

    asyncio.run(_run())

    async def _insert():
        db = await get_db()
        # For compatibility testing, store ciphertext under the previous key
        prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
        blob = prev_crypto.encrypt(plaintext)
        await db.execute(
            "INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "my-secret", blob, 1),
        )

    asyncio.run(_insert())


def test_rotate_requires_previous_key_is_configured(tmp_path, client, monkeypatch):
    # Intentionally do NOT set vault_key_previous
    monkeypatch.setattr(settings, "vault_key_previous", None)
    monkeypatch.setattr(settings, "vault_key", "new-seed")

    async def _run():
        await init_db(str(tmp_path / "test_secuscan.db"))

    asyncio.run(_run())

    r = client.post(
        "/api/v1/vault/rotate",
        headers={"Authorization": f"Bearer {settings.admin_api_key}"},
    )
    assert r.status_code == 400
    assert "vault_key_previous" in r.json().get("detail", "") or "requires" in r.json().get("detail", "")


def test_rotate_fails_closed_if_decrypt_fails(tmp_path, client, monkeypatch):
    _derive_prev_new_keys(tmp_path, monkeypatch)

    # Initialize DB
    asyncio.run(init_db(str(tmp_path / "test_secuscan.db")))

    async def _insert_corrupt_ciphertext():
        db = await get_db()
        # Insert invalid base64 payload so decryptor will fail
        await db.execute(
            "INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "my-secret", "not-valid-base64url!!", 1),
        )

    asyncio.run(_insert_corrupt_ciphertext())

    # Attempt rotation
    r = client.post(
        "/api/v1/vault/rotate",
        headers={"Authorization": f"Bearer {settings.admin_api_key}"},
    )
    assert r.status_code in (500, 400)

    # Verify DB row was not partially modified
    async def _fetch_cipher():
        db = await get_db()
        return await db.fetchone(
            "SELECT encrypted_value, key_version FROM credential_vault WHERE name = ?",
            ("my-secret",),
        )

    row = asyncio.run(_fetch_cipher())
    assert row is not None
    assert row["encrypted_value"] == "not-valid-base64url!!"


def test_rotate_changes_ciphertext_and_allows_new_decrypt(tmp_path, client, monkeypatch):
    _derive_prev_new_keys(tmp_path, monkeypatch)

    # Initialize DB and insert a plaintext encrypted with previous key
    asyncio.run(init_db(str(tmp_path / "test_secuscan.db")))
    async def _insert():
        db = await get_db()
        prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
        blob = prev_crypto.encrypt("s3cr3t")
        await db.execute(
            "INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "my-secret", blob, 1),
        )

    asyncio.run(_insert())

    async def _fetch_cipher():
        db = await get_db()
        return await db.fetchone(
            "SELECT encrypted_value, key_version FROM credential_vault WHERE name = ?",
            ("my-secret",),
        )

    before = asyncio.run(_fetch_cipher())

    r = client.post(
        "/api/v1/vault/rotate",
        headers={"Authorization": f"Bearer {settings.admin_api_key}"},
    )
    assert r.status_code == 200
    assert r.json()["rotated"] == 1

    after = asyncio.run(_fetch_cipher())
    assert after["encrypted_value"] != before["encrypted_value"]

    # Old decrypt should fail (ciphertext updated), new decrypt should succeed.
    # Note: VaultCrypto decrypt expects base64 payload created using VaultCrypto.
    # Rotation endpoint uses VaultCrypto under the hood, so this should work.
    prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
    new_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)

    # The backend updates using resolved vault key (current) and encryptor version.
    # So we must re-read settings.resolved_vault_key to construct a correct decryptor.
    new_crypto = VaultCrypto(settings.resolved_vault_key, previous_keys=[settings.resolved_vault_key_previous] if settings.resolved_vault_key_previous else None, current_version=1)

    with pytest.raises(Exception):
        prev_crypto.decrypt(after["encrypted_value"])

    assert new_crypto.decrypt(after["encrypted_value"]) == "s3cr3t"

