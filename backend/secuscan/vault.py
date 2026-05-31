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
        self.key = hashlib.sha256(key).digest()

    def encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = os.urandom(16)
        padding = os.urandom(32)
        aesgcm = AESGCM(self.key)
        ciphertext = aesgcm.encrypt(nonce[:12], raw, padding)
        blob = nonce + padding + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        nonce = blob[:16]
        padding = blob[16:48]
        ciphertext = blob[48:]
        aesgcm = AESGCM(self.key)
        try:
            raw = aesgcm.decrypt(nonce[:12], ciphertext, padding)
        except InvalidTag:
            raise ValueError("Vault payload integrity verification failed")
        return raw.decode("utf-8")
