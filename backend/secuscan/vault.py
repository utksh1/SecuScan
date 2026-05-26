"""Lightweight encrypted credential vault."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """Symmetric encryption helper backed by AES-256-GCM.

    AES-GCM provides both confidentiality and authenticity in a single pass,
    replacing the previous XOR-stream + HMAC approach which was vulnerable to
    key-reuse attacks on secrets longer than 32 bytes.

    Wire format (all concatenated, then base64url-encoded):
        nonce (12 bytes) || ciphertext+tag (len(plaintext) + 16 bytes)

    The AES key is derived from the user-supplied key material via SHA-256 so
    that any-length key bytes are accepted without padding issues.
    """

    _NONCE_SIZE = 12  # 96-bit nonce recommended for AES-GCM

    def __init__(self, key: bytes):
        # Derive a fixed-length 256-bit AES key from arbitrary key material.
        self._aes_key = hashlib.sha256(key).digest()

    def encrypt(self, plaintext: str) -> str:
        raw = plaintext.encode("utf-8")
        nonce = os.urandom(self._NONCE_SIZE)
        aesgcm = AESGCM(self._aes_key)
        # AESGCM.encrypt() returns ciphertext + 16-byte authentication tag.
        ciphertext_tag = aesgcm.encrypt(nonce, raw, associated_data=None)
        blob = nonce + ciphertext_tag
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        nonce = blob[: self._NONCE_SIZE]
        ciphertext_tag = blob[self._NONCE_SIZE :]
        aesgcm = AESGCM(self._aes_key)
        # decrypt() raises cryptography.exceptions.InvalidTag if the tag
        # doesn't match — i.e. the payload was tampered with or the key is wrong.
        try:
            raw = aesgcm.decrypt(nonce, ciphertext_tag, associated_data=None)
        except Exception as exc:
            raise ValueError("Vault payload integrity verification failed") from exc
        return raw.decode("utf-8")