import pytest
import uuid
import os
import base64

from secuscan.config import settings
from secuscan.vault import VaultCrypto
from secuscan.database import init_db, get_db
from secuscan import routes
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_rotate_success(tmp_path, monkeypatch):
    # configure keys
    settings.vault_key_previous = "old-seed"
    settings.vault_key = "new-seed"

    # init in-memory DB
    db = await init_db(":memory:")

    # create a secret encrypted with the previous key
    prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
    blob = prev_crypto.encrypt("s3cr3t")
    secret_id = str(uuid.uuid4())
    await db.execute("INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)", (secret_id, "my-secret", blob, 1))

    # perform rotation
    resp = await routes.rotate_vault_keys()
    assert resp["rotated"] == 1

    # ensure record decrypts with new key
    row = await db.fetchone("SELECT encrypted_value FROM credential_vault WHERE id = ?", (secret_id,))
    cur_crypto = VaultCrypto(settings.resolved_vault_key, previous_keys=[settings.resolved_vault_key_previous])
    assert cur_crypto.decrypt(row["encrypted_value"]) == "s3cr3t"


@pytest.mark.asyncio
async def test_rotate_missing_previous_key(monkeypatch):
    # ensure previous key unset
    settings.vault_key_previous = None
    settings.vault_key = "new-seed"

    await init_db(":memory:")

    with pytest.raises(HTTPException) as exc:
        await routes.rotate_vault_keys()
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_rotate_rollback_on_failure(tmp_path):
    settings.vault_key_previous = "old-seed"
    settings.vault_key = "new-seed"

    db = await init_db(":memory:")

    # valid record
    prev_crypto = VaultCrypto(settings.resolved_vault_key_previous, previous_keys=None, current_version=1)
    good = prev_crypto.encrypt("ok")
    id_good = str(uuid.uuid4())
    await db.execute("INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)", (id_good, "good", good, 1))

    # invalid record (undecryptable)
    bad_blob = base64.urlsafe_b64encode(b"\x01" + os.urandom(30)).decode('ascii')
    id_bad = str(uuid.uuid4())
    await db.execute("INSERT INTO credential_vault (id, name, encrypted_value, key_version) VALUES (?, ?, ?, ?)", (id_bad, "bad", bad_blob, 1))

    with pytest.raises(HTTPException) as exc:
        await routes.rotate_vault_keys()
    assert exc.value.status_code == 500

    # Verify no changes were committed (bad record still present and good record decrypts with previous key)
    row_bad = await db.fetchone("SELECT encrypted_value FROM credential_vault WHERE id = ?", (id_bad,))
    assert row_bad is not None
    row_good = await db.fetchone("SELECT encrypted_value FROM credential_vault WHERE id = ?", (id_good,))
    assert prev_crypto.decrypt(row_good["encrypted_value"]) == "ok"