"""Encrypted credential vault backed by AES-256-GCM."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """AES-256-GCM authenticated encryption for vault secrets.

    Each call to encrypt() generates a fresh 12-byte nonce so ciphertexts are
    never reused, even for identical plaintexts. The 16-byte GCM auth tag
    provides integrity — decryption raises ValueError on any tampering.
    """

    _NONCE_LEN = 12

    def __init__(self, key: bytes):
        # key is the raw Fernet-encoded 32-byte value from config.resolved_vault_key.
        # We base64-decode it to get the 32 raw bytes that AESGCM expects.
        raw = base64.urlsafe_b64decode(key)
        if len(raw) != 32:
            raise ValueError("Vault key must be exactly 32 raw bytes (256 bits)")
        self._aesgcm = AESGCM(raw)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(self._NONCE_LEN)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        blob = nonce + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        nonce = blob[: self._NONCE_LEN]
        ciphertext = blob[self._NONCE_LEN :]
        try:
            raw = self._aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise ValueError("Vault payload integrity verification failed") from exc
        return raw.decode("utf-8")
