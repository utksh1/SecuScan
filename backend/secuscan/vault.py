"""Authenticated encrypted credential vault using AES-256-GCM."""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Dict, List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultCrypto:
    """AES-256-GCM authenticated encryption for stored credentials.

    Each call to encrypt() generates a fresh random 12-byte nonce so no two
    ciphertexts ever share a nonce under the same key.  The GCM auth tag
    (16 bytes, appended by AESGCM) provides both confidentiality and integrity -
    any tampering causes decrypt() to raise ValueError.

    Wire format v1 (base64url):
        header_prefix(4) || key_id_bytes(8) || nonce(12) || ciphertext || auth_tag(16)

    Legacy wire format (base64url):
        nonce(12) || ciphertext || auth_tag(16)
    """

    _HEADER_PREFIX = b"SV1:"
    _NONCE_LEN = 12
    _TAG_LEN = 16
    _FINGERPRINT_DOMAIN = b"secuscan/vault-key-fingerprint/v1"
    _FINGERPRINT_BYTES = 8

    # Minimum payload lengths:
    # Legacy: 12 (nonce) + 16 (tag) = 28 bytes
    # Versioned: 4 (prefix) + 8 (key_id) + 12 (nonce) + 16 (tag) = 40 bytes
    _MIN_LEGACY_LEN = _NONCE_LEN + _TAG_LEN
    _MIN_VERSIONED_LEN = len(_HEADER_PREFIX) + _FINGERPRINT_BYTES + _NONCE_LEN + _TAG_LEN

    def __init__(self, key: bytes, fallback_keys: Optional[List[bytes]] = None):
        """
        Args:
            key: 44-byte base64url-encoded representation of a 32-byte AES-256 key,
                 as produced by ``settings.resolved_vault_key``.
            fallback_keys: Optional list of secondary/old 44-byte base64url-encoded AES-256 keys
                 used to support decryption during key rotation.
        """
        raw_primary = self._decode_key(key)
        self._primary_key_id_bytes = self._compute_fingerprint_bytes(raw_primary)
        self._key_fingerprint = self._format_fingerprint(self._primary_key_id_bytes)

        # Map key_id_bytes -> AESGCM cipher
        self._keyring: Dict[bytes, AESGCM] = {}
        self._keyring_list: List[AESGCM] = []

        primary_cipher = AESGCM(raw_primary)
        self._keyring[self._primary_key_id_bytes] = primary_cipher
        self._keyring_list.append(primary_cipher)

        if fallback_keys:
            for f_key in fallback_keys:
                raw_fb = self._decode_key(f_key)
                fb_key_id = self._compute_fingerprint_bytes(raw_fb)
                fb_cipher = AESGCM(raw_fb)
                if fb_key_id not in self._keyring:
                    self._keyring[fb_key_id] = fb_cipher
                    self._keyring_list.append(fb_cipher)

    @classmethod
    def _decode_key(cls, key: bytes) -> bytes:
        try:
            raw = base64.urlsafe_b64decode(key)
        except Exception as exc:
            raise ValueError("Vault key must be base64url-encoded") from exc
        if len(raw) != 32:
            raise ValueError(
                f"Vault key must decode to exactly 32 bytes (AES-256); got {len(raw)}"
            )
        return raw

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(self._NONCE_LEN)
        primary_cipher = self._keyring[self._primary_key_id_bytes]
        ciphertext = primary_cipher.encrypt(nonce, plaintext.encode("utf-8"), None)
        header = self._HEADER_PREFIX + self._primary_key_id_bytes
        blob = header + nonce + ciphertext
        return base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, payload: str) -> str:
        try:
            blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        except Exception as exc:
            raise ValueError("Vault payload is not valid base64url") from exc

        if len(blob) < self._MIN_LEGACY_LEN:
            raise ValueError("Vault payload is too short")

        # Attempt versioned decryption if header is present
        if blob.startswith(self._HEADER_PREFIX) and len(blob) >= self._MIN_VERSIONED_LEN:
            prefix_len = len(self._HEADER_PREFIX)
            key_id = blob[prefix_len : prefix_len + self._FINGERPRINT_BYTES]
            nonce_start = prefix_len + self._FINGERPRINT_BYTES
            nonce = blob[nonce_start : nonce_start + self._NONCE_LEN]
            ciphertext = blob[nonce_start + self._NONCE_LEN :]

            cipher = self._keyring.get(key_id)
            if cipher is not None:
                try:
                    raw = cipher.decrypt(nonce, ciphertext, None)
                    return raw.decode("utf-8")
                except Exception:
                    # GCM failure on versioned payload; will attempt legacy fallback below
                    pass

        # Legacy unversioned format fallback (nonce(12) || ciphertext) or 1-in-2^32 header collision fallback
        nonce = blob[: self._NONCE_LEN]
        ciphertext = blob[self._NONCE_LEN :]

        for cipher in self._keyring_list:
            try:
                raw = cipher.decrypt(nonce, ciphertext, None)
                return raw.decode("utf-8")
            except Exception:
                continue

        raise ValueError("Vault payload integrity verification failed")

    @classmethod
    def _compute_fingerprint_bytes(cls, raw_key: bytes) -> bytes:
        """Derive the 8-byte raw fingerprint for 32-byte key material."""
        digest = hashlib.sha256(cls._FINGERPRINT_DOMAIN + raw_key).digest()
        return digest[: cls._FINGERPRINT_BYTES]

    @classmethod
    def _format_fingerprint(cls, fingerprint_bytes: bytes) -> str:
        """Format 8-byte raw fingerprint as colon-separated hex pairs."""
        return ":".join(f"{byte:02x}" for byte in fingerprint_bytes)

    @classmethod
    def _compute_fingerprint(cls, raw_key: bytes) -> str:
        """Derive the colon-separated hex fingerprint for raw 32-byte key material."""
        return cls._format_fingerprint(cls._compute_fingerprint_bytes(raw_key))

    @classmethod
    def extract_key_id(cls, payload: str) -> Optional[str]:
        """Extract the colon-separated hex key fingerprint from a versioned vault blob payload if present.

        Returns None if the payload is legacy/unversioned or invalid.
        """
        try:
            blob = base64.urlsafe_b64decode(payload.encode("ascii"))
        except Exception:
            return None

        if blob.startswith(cls._HEADER_PREFIX) and len(blob) >= cls._MIN_VERSIONED_LEN:
            prefix_len = len(cls._HEADER_PREFIX)
            key_id_bytes = blob[prefix_len : prefix_len + cls._FINGERPRINT_BYTES]
            return cls._format_fingerprint(key_id_bytes)
        return None

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
