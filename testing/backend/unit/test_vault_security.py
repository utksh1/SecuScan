"""
Security tests for the credential vault (issue #200).

Verifies that:
- AES-256-GCM is used (not the old XOR stream cipher)
- The hardcoded fallback key "secuscan-dev-key" is gone
- resolved_vault_key raises when no key is configured
- Each encrypt() call produces a distinct ciphertext (unique nonces)
- Wrong key always fails authentication
- Truncated / short blobs raise, not silently return garbage
"""

import base64
import hashlib
import pytest

from backend.secuscan.vault import VaultCrypto
from backend.secuscan.config import settings


def _make_key(seed: str) -> bytes:
    raw = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(raw)


class TestAesGcmProperties:
    def test_roundtrip(self):
        crypto = VaultCrypto(_make_key("test"))
        assert crypto.decrypt(crypto.encrypt("hello")) == "hello"

    def test_unique_ciphertexts_per_call(self):
        crypto = VaultCrypto(_make_key("test"))
        c1 = crypto.encrypt("same plaintext")
        c2 = crypto.encrypt("same plaintext")
        assert c1 != c2, "Each call must use a fresh nonce"

    def test_blob_structure_has_12_byte_nonce(self):
        """Blob starts with a 12-byte nonce (AES-GCM standard)."""
        crypto = VaultCrypto(_make_key("test"))
        blob = base64.urlsafe_b64decode(crypto.encrypt("x").encode())
        # nonce(12) + 1-byte plaintext + 16-byte auth_tag = 29 bytes total
        assert len(blob) == 29

    def test_tamper_ciphertext_raises(self):
        crypto = VaultCrypto(_make_key("test"))
        blob = bytearray(base64.urlsafe_b64decode(crypto.encrypt("secret").encode()))
        blob[14] ^= 0x01
        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto.decrypt(base64.urlsafe_b64encode(bytes(blob)).decode())

    def test_tamper_auth_tag_raises(self):
        crypto = VaultCrypto(_make_key("test"))
        blob = bytearray(base64.urlsafe_b64decode(crypto.encrypt("secret").encode()))
        blob[-1] ^= 0x01
        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto.decrypt(base64.urlsafe_b64encode(bytes(blob)).decode())

    def test_tamper_nonce_raises(self):
        crypto = VaultCrypto(_make_key("test"))
        blob = bytearray(base64.urlsafe_b64decode(crypto.encrypt("secret").encode()))
        blob[0] ^= 0x01
        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto.decrypt(base64.urlsafe_b64encode(bytes(blob)).decode())

    def test_wrong_key_raises(self):
        crypto_a = VaultCrypto(_make_key("key-a"))
        crypto_b = VaultCrypto(_make_key("key-b"))
        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto_b.decrypt(crypto_a.encrypt("secret"))

    def test_truncated_blob_raises(self):
        crypto = VaultCrypto(_make_key("test"))
        blob = base64.urlsafe_b64decode(crypto.encrypt("hello").encode())
        short = base64.urlsafe_b64encode(blob[:5]).decode()
        with pytest.raises(ValueError):
            crypto.decrypt(short)

    def test_garbage_input_raises(self):
        crypto = VaultCrypto(_make_key("test"))
        with pytest.raises(Exception):
            crypto.decrypt("not-valid-base64!!!")


class TestVaultKeyConfiguration:
    def test_invalid_base64_key_raises_value_error(self):
        with pytest.raises(ValueError):
            VaultCrypto(b"not-valid-base64!!!")

    def test_short_key_raises_value_error(self):
        short_b64 = base64.urlsafe_b64encode(b"only16bytes12345")
        with pytest.raises(ValueError, match="32 bytes"):
            VaultCrypto(short_b64)

    def test_resolved_vault_key_raises_without_config(self, monkeypatch):
        """resolved_vault_key must raise RuntimeError when no key is configured."""
        monkeypatch.setattr(settings, "vault_key", None)
        monkeypatch.setattr(settings, "plugin_signature_key", None)
        with pytest.raises(RuntimeError, match="SECUSCAN_VAULT_KEY"):
            _ = settings.resolved_vault_key

    def test_resolved_vault_key_works_with_vault_key_set(self, monkeypatch):
        monkeypatch.setattr(settings, "vault_key", "any-non-empty-value")
        key = settings.resolved_vault_key
        assert isinstance(key, bytes)
        assert len(base64.urlsafe_b64decode(key)) == 32

    def test_resolved_vault_key_falls_back_to_plugin_signature_key(self, monkeypatch):
        monkeypatch.setattr(settings, "vault_key", None)
        monkeypatch.setattr(settings, "plugin_signature_key", "plugin-key")
        key = settings.resolved_vault_key
        assert isinstance(key, bytes)
        assert len(base64.urlsafe_b64decode(key)) == 32

    def test_hardcoded_dev_key_no_longer_used(self, monkeypatch):
        """'secuscan-dev-key' must not be the effective key when both settings are None."""
        monkeypatch.setattr(settings, "vault_key", None)
        monkeypatch.setattr(settings, "plugin_signature_key", None)
        with pytest.raises(RuntimeError):
            _ = settings.resolved_vault_key
