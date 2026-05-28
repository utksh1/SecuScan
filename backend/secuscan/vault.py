"""Lightweight encrypted credential vault backed by AES-256-GCM."""
from __future__ import annotations
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """Symmetric encryption helper using AES-256-GCM.

    AES-256-GCM is an authenticated encryption scheme that provides:
    - Confidentiality regardless of secret length (no keystream cycling)
    - Built-in integrity verification via authentication tag
    - Replaces the previous XOR stream cipher which was trivially breakable
      via crib-dragging for secrets longer than 32 bytes.
    """

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("VaultCrypto requires a 32-byte key")
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = os.urandom(12)  # 96-bit nonce recommended for GCM
        ciphertext = self.aesgcm.encrypt(nonce, raw, None)
        blob = nonce + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        nonce = blob[:12]
        ciphertext = blob[12:]
        try:
            raw = self.aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise ValueError("Vault payload integrity verification failed") from exc
        return raw.decode("utf-8")
