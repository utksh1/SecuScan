from backend.secuscan.config import settings
from backend.secuscan.vault import VaultCrypto


def test_vault_encrypt_roundtrip():
    crypto = VaultCrypto(settings.resolved_vault_key)
    secret = "super-secret-token"
    encrypted = crypto.encrypt(secret)
    assert encrypted != secret
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == secret
