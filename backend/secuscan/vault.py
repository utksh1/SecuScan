"""Authenticated encrypted credential vault using AES-256-GCM."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """AES-256-GCM authenticated encryption for stored credentials.

    Each call to encrypt() generates a fresh random 12-byte nonce so no two
    ciphertexts ever share a nonce under the same key.  The GCM auth tag
    (16 bytes, appended by AESGCM) provides both confidentiality and integrity -
    any tampering causes decrypt() to raise ValueError.

    Wire format (base64url): nonce(12) || ciphertext || auth_tag(16)
    """

    _NONCE_LEN = 12

    # Domain-separation prefix so the fingerprint can never collide with any other use of the key material as a hash input.
    # So the digest is a dedicated identifier rather than a reusable oracle.
    _FINGERPRINT_DOMAIN = b"secuscan/vault-key-fingerprint/v1"
    # 8 bytes (64 bits) is plenty to distinguish keys for rotation checks while keeping the value short and obviously non-recoverable.
    _FINGERPRINT_BYTES = 8

    def __init__(self, key: bytes):
        """
        Args:
            key: 44-byte base64url-encoded representation of a 32-byte AES-256 key,
                 as produced by ``settings.resolved_vault_key``.
        """
        try:
            raw = base64.urlsafe_b64decode(key)
        except Exception as exc:
            raise ValueError("Vault key must be base64url-encoded") from exc
        if len(raw) != 32:
            raise ValueError(
                f"Vault key must decode to exactly 32 bytes (AES-256); got {len(raw)}"
            )
        self._aesgcm = AESGCM(raw)
        # Compute the fingerprint at construction and retain only the resulting string, never the raw key bytes.
        # So the instance keeps no extra copy of the key material beyond what AESGCM already holds internally.
        self._key_fingerprint = self._compute_fingerprint(raw)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(self._NONCE_LEN)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        blob = nonce + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        try:
            blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        except Exception as exc:
            raise ValueError("Vault payload is not valid base64url") from exc

        nonce = blob[: self._NONCE_LEN]
        ciphertext = blob[self._NONCE_LEN :]

        try:
            raw = self._aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise ValueError("Vault payload integrity verification failed") from exc

        return raw.decode("utf-8")

    @classmethod
    def _compute_fingerprint(cls, raw_key: bytes) -> str:
        """Derive the colon-separated hex fingerprint for raw 32-byte key material."""
        digest = hashlib.sha256(cls._FINGERPRINT_DOMAIN + raw_key).digest()
        truncated = digest[: cls._FINGERPRINT_BYTES]
        return ":".join(f"{byte:02x}" for byte in truncated)

    @property
    def key_fingerprint(self) -> str:
        """A non-secret, stable identifier for the active vault key.

        Computed as a domain-separated SHA-256 over the raw key material, truncated to 64 bits and rendered as colon-separated hex pairs.
        Eg: ``"1a:2b:3c:4d:5e:6f:70:81"``.

        The fingerprint is one-way - the key can't be recovered from it. But it changes whenever the underlying key is rotated.
        Operators can compare fingerprints across deployments or before/after a rotation to confirm the key state without ever handling the key itself:
        which is why it is safe to surface in diagnostics output.
        """
        return self._key_fingerprint
