import pytest
import aiosqlite
import os

from secuscan.database import init_db
from secuscan import routes
from secuscan.config import settings


@pytest.mark.asyncio
async def test_credential_vault_migration_adds_key_version_and_backfills(tmp_path):
    db_file = tmp_path / "old_vault.db"
    # Create an old-style credential_vault table without key_version
    async with aiosqlite.connect(str(db_file)) as conn:
        await conn.execute(
            """
            CREATE TABLE credential_vault (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                encrypted_value TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        await conn.execute(
            "INSERT INTO credential_vault (id, name, encrypted_value) VALUES (?, ?, ?)",
            ("id-1", "legacy-secret", "oldblob"),
        )
        await conn.commit()

    # Initialize DB via application migration logic
    db = await init_db(str(db_file))

    # Ensure the migration created the key_version column
    cols = await db.fetchall("PRAGMA table_info(credential_vault)")
    names = {c["name"] for c in cols}
    assert "key_version" in names

    # Existing rows should have been backfilled to 1
    row = await db.fetchone("SELECT key_version FROM credential_vault WHERE name = ?", ("legacy-secret",))
    assert row is not None and row["key_version"] == 1


@pytest.mark.asyncio
async def test_put_and_list_do_not_expose_encrypted_value(tmp_path):
    # Ensure a deterministic test key is set
    settings.vault_key = "test-vault-key-for-unit-tests-only"

    db = await init_db(":memory:")

    # Use the route helper to insert a secret
    resp = await routes.upsert_vault_secret("sensitive", {"value": "topsecret"})
    assert isinstance(resp, dict)
    # API response must not include raw encrypted blob
    assert "encrypted_value" not in resp

    # Listing must not include encrypted_value field
    listing = await routes.list_vault_secrets()
    assert "items" in listing
    assert listing["total"] == 1
    item = listing["items"][0]
    assert "name" in item and item["name"] == "sensitive"
    assert "encrypted_value" not in item

    # Raw DB row must still contain encrypted_value (stored server-side only)
    raw = await db.fetchone("SELECT encrypted_value FROM credential_vault WHERE name = ?", ("sensitive",))
    assert raw is not None and raw["encrypted_value"].startswith("\n") is False
