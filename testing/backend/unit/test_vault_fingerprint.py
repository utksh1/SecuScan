"""
Unit tests for the vault key fingerprint (issue #809).

The fingerprint must let operators confirm key-rotation state without ever
exposing key material, so it has to be:

- deterministic / stable for a given key,
- different for different keys (changes on rotation),
- one-way: it must not contain or trivially reveal the key,
- a fixed, well-formed colon-separated hex identifier.
"""

import base64
import hashlib

from backend.secuscan.config import settings
from backend.secuscan.vault import VaultCrypto


def _make_key(seed: str) -> bytes:
    """Mirror settings.resolved_vault_key: base64url(sha256(seed))."""
    raw = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(raw)


class TestKeyFingerprintProperties:
    def test_fingerprint_is_deterministic(self):
        a = VaultCrypto(_make_key("rotation-test")).key_fingerprint
        b = VaultCrypto(_make_key("rotation-test")).key_fingerprint
        assert a == b

    def test_fingerprint_changes_when_key_rotates(self):
        before = VaultCrypto(_make_key("key-v1")).key_fingerprint
        after = VaultCrypto(_make_key("key-v2")).key_fingerprint
        assert before != after

    def test_fingerprint_format_is_colon_hex(self):
        fp = VaultCrypto(_make_key("format")).key_fingerprint
        parts = fp.split(":")
        # 8 bytes -> 8 colon-separated pairs, each two lowercase hex digits.
        assert len(parts) == VaultCrypto._FINGERPRINT_BYTES
        assert all(len(p) == 2 for p in parts)
        # Round-trips back to bytes => only valid hex characters present.
        assert bytes.fromhex(fp.replace(":", ""))

    def test_fingerprint_length_matches_truncation(self):
        fp = VaultCrypto(_make_key("len")).key_fingerprint
        raw = bytes.fromhex(fp.replace(":", ""))
        assert len(raw) == VaultCrypto._FINGERPRINT_BYTES

    def test_fingerprint_does_not_reveal_key_material(self):
        key = _make_key("secret-material")
        crypto = VaultCrypto(key)
        fp = crypto.key_fingerprint
        raw_key = base64.urlsafe_b64decode(key)
        # Neither the encoded nor the raw key should appear in the fingerprint.
        assert key.decode("ascii") not in fp
        assert raw_key.hex() not in fp.replace(":", "")

    def test_fingerprint_uses_domain_separated_sha256(self):
        """Fingerprint equals the documented construction, not a bare hash."""
        key = _make_key("domain-sep")
        raw_key = base64.urlsafe_b64decode(key)
        expected_digest = hashlib.sha256(
            VaultCrypto._FINGERPRINT_DOMAIN + raw_key
        ).digest()[: VaultCrypto._FINGERPRINT_BYTES]
        expected = ":".join(f"{b:02x}" for b in expected_digest)
        assert VaultCrypto(key).key_fingerprint == expected

    def test_bare_sha256_would_differ_from_fingerprint(self):
        """Domain separation actually changes the output vs. a plain hash."""
        key = _make_key("no-domain")
        raw_key = base64.urlsafe_b64decode(key)
        bare = hashlib.sha256(raw_key).digest()[: VaultCrypto._FINGERPRINT_BYTES]
        bare_fp = ":".join(f"{b:02x}" for b in bare)
        assert VaultCrypto(key).key_fingerprint != bare_fp


class TestResolvedKeyFingerprint:
    def test_fingerprint_available_for_resolved_key(self):
        crypto = VaultCrypto(settings.resolved_vault_key)
        assert crypto.key_fingerprint
        assert ":" in crypto.key_fingerprint
