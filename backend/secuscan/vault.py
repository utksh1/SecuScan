"""Lightweight encrypted credential vault."""
from __future__ import annotations
import base64
import hashlib
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class VaultCrypto:
    """Symmetric encryption helper using AES-256-GCM."""

    def __init__(self, key: bytes):
        if len(key) < 16:
            raise ValueError("Vault key must be at least 16 bytes")
        self.key = hashlib.sha256(key).digest()

    def encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = os.urandom(12)
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce, raw, None)
        blob = nonce + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        if len(blob) < 13:
            raise ValueError("Vault payload integrity verification failed")
        nonce = blob[:12]
        ciphertext = blob[12:]
        aesgcm = AESGCM(self.key)
        try:
            raw = aesgcm.decrypt(nonce, ciphertext, None)
        except InvalidTag:
            raise ValueError("Vault payload integrity verification failed")
        return raw.decode("utf-8")
