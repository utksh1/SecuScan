"""Lightweight encrypted credential vault."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from itertools import cycle


class VaultCrypto:
    """Symmetric encryption helper backed by a deterministic keystream.

    This is intentionally lightweight for local-first usage where secret-at-rest
    protection is needed without adding third-party crypto dependencies.
    """

    def __init__(self, key: bytes):
        self.key = key

    def _derive_stream_key(self, nonce: bytes) -> bytes:
        return hashlib.sha256(self.key + nonce).digest()

    def encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = os.urandom(16)
        stream_key = self._derive_stream_key(nonce)
        ciphertext = bytes(b ^ k for b, k in zip(raw, cycle(stream_key)))
        signature = hmac.new(self.key, nonce + ciphertext, hashlib.sha256).digest()
        blob = nonce + signature + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        nonce = blob[:16]
        signature = blob[16:48]
        ciphertext = blob[48:]

        expected = hmac.new(self.key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Vault payload integrity verification failed")

        stream_key = self._derive_stream_key(nonce)
        raw = bytes(b ^ k for b, k in zip(ciphertext, cycle(stream_key)))
        return raw.decode("utf-8")
