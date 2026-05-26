"""Authenticated encrypted credential vault using AES-256-GCM."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """AES-256-GCM authenticated encryption for stored credentials.

    Each call to encrypt() generates a fresh random 12-byte nonce so no two
    ciphertexts ever share a nonce under the same key.  The GCM auth tag
    (16 bytes, appended by AESGCM) provides both confidentiality and integrity —
    any tampering causes decrypt() to raise ValueError.

    Wire format (base64url): nonce(12) || ciphertext || auth_tag(16)
    """

    _NONCE_LEN = 12

    def __init__(
        self,
        current_key: bytes | None,
        previous_keys: list[bytes] | None = None,
        current_version: int = 1,
    ):
        """Initialize vault crypto with current and optional previous keys.

        Args:
            current_key: base64url-encoded 32-byte key (bytes) or None.
            previous_keys: list of base64url-encoded 32-byte keys (bytes) to try
                when decrypting older records.
            current_version: integer version assigned to values encrypted by
                `current_key`.
        """
        def _make_aesgcm(b: bytes):
            try:
                raw = base64.urlsafe_b64decode(b)
            except Exception as exc:
                raise ValueError("Vault key must be base64url-encoded") from exc
            if len(raw) != 32:
                raise ValueError(
                    f"Vault key must decode to exactly 32 bytes (AES-256); got {len(raw)}"
                )
            return AESGCM(raw)

        self._current_version = int(current_version)
        self._aesgcm = _make_aesgcm(current_key) if current_key is not None else None
        self._previous_aes = []
        if previous_keys:
            for pk in previous_keys:
                if pk is None:
                    continue
                self._previous_aes.append(_make_aesgcm(pk))

    @property
    def version(self) -> int:
        """Returns the integer version associated with the current key."""
        return self._current_version

    def encrypt(self, plaintext: str) -> str:
        if self._aesgcm is None:
            raise ValueError("No current vault key configured for encryption")
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

        # Try current key first
        if self._aesgcm is not None:
            try:
                raw = self._aesgcm.decrypt(nonce, ciphertext, None)
                return raw.decode("utf-8")
            except Exception:
                pass

        # Try previous keys in order
        for aes in self._previous_aes:
            try:
                raw = aes.decrypt(nonce, ciphertext, None)
                return raw.decode("utf-8")
            except Exception:
                continue

        raise ValueError("Vault payload integrity verification failed")
