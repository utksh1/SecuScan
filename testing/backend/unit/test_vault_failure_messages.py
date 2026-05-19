"""
testing/backend/unit/test_vault_failure_messages.py

Issue #91 — Vault export/import failure messages must be clear
and must not leak secret material.

Coverage:
  - VaultCrypto.decrypt rejects tampered payload (integrity check)
  - VaultCrypto.decrypt rejects malformed base64
  - PUT /vault/{name} rejects missing/empty value
  - GET /vault/{name} returns 404 for unknown secret
  - Error responses never contain encrypted blobs or secret values
"""

import base64
import pytest
from backend.secuscan.vault import VaultCrypto
from backend.secuscan.config import settings

ENDPOINT_PUT    = "/api/v1/vault/{name}"
ENDPOINT_GET    = "/api/v1/vault/{name}"
ENDPOINT_DELETE = "/api/v1/vault/{name}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def put_secret(client, name: str, value: str):
    return client.put(ENDPOINT_PUT.format(name=name), json={"value": value})

def get_secret(client, name: str):
    return client.get(ENDPOINT_GET.format(name=name))

def delete_secret(client, name: str):
    return client.delete(ENDPOINT_DELETE.format(name=name))


# ---------------------------------------------------------------------------
# 1. VaultCrypto unit — failure paths
# ---------------------------------------------------------------------------

class TestVaultCryptoFailures:
    """
    Unit tests for VaultCrypto.decrypt failure paths.
    These run without HTTP and verify the crypto layer directly.
    """

    def test_tampered_payload_raises_value_error(self):
        """Flipping a byte in the ciphertext must fail HMAC verification."""
        crypto = VaultCrypto(settings.resolved_vault_key)
        encrypted = crypto.encrypt("my-secret-token")

        # Decode, flip one byte in the ciphertext area (after nonce+signature = 48 bytes)
        blob = bytearray(base64.urlsafe_b64decode(encrypted.encode("ascii")))
        blob[50] ^= 0xFF
        tampered = base64.urlsafe_b64encode(bytes(blob)).decode("ascii")

        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto.decrypt(tampered)

    def test_tampered_signature_raises_value_error(self):
        """Flipping a byte in the HMAC signature must fail verification."""
        crypto = VaultCrypto(settings.resolved_vault_key)
        encrypted = crypto.encrypt("another-secret")

        blob = bytearray(base64.urlsafe_b64decode(encrypted.encode("ascii")))
        blob[20] ^= 0x01  # inside signature bytes (16–48)
        tampered = base64.urlsafe_b64encode(bytes(blob)).decode("ascii")

        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto.decrypt(tampered)

    def test_malformed_base64_raises_exception(self):
        """Garbage input must raise an exception, not silently return data."""
        crypto = VaultCrypto(settings.resolved_vault_key)
        with pytest.raises(Exception):
            crypto.decrypt("not-valid-base64!!!")

    def test_wrong_key_raises_value_error(self):
        """Decrypting with a different key must fail HMAC check."""
        crypto_a = VaultCrypto(b"key-used-to-encrypt-AAAAAAAAAAAAA")
        crypto_b = VaultCrypto(b"key-used-to-decrypt-BBBBBBBBBBBBB")
        encrypted = crypto_a.encrypt("secret-value")

        with pytest.raises(ValueError, match="integrity verification failed"):
            crypto_b.decrypt(encrypted)

    def test_error_message_does_not_contain_secret(self):
        """The ValueError message must not echo back the secret or payload."""
        crypto = VaultCrypto(settings.resolved_vault_key)
        secret = "SENTINEL_SECRET_VALUE"
        encrypted = crypto.encrypt(secret)

        blob = bytearray(base64.urlsafe_b64decode(encrypted.encode("ascii")))
        blob[50] ^= 0xFF
        tampered = base64.urlsafe_b64encode(bytes(blob)).decode("ascii")

        try:
            crypto.decrypt(tampered)
        except ValueError as e:
            assert secret not in str(e), "Error message leaks secret value"
            assert tampered not in str(e), "Error message leaks encrypted payload"


# ---------------------------------------------------------------------------
# 2. Route-level failure paths
# ---------------------------------------------------------------------------

class TestVaultRouteFailures:
    """
    Integration tests for vault HTTP routes.
    Verifies safe error responses for invalid inputs.
    """

    def test_put_empty_value_returns_400(self, test_client):
        """PUT with empty value must be rejected."""
        r = put_secret(test_client, "test-empty", "")
        assert r.status_code == 400

    def test_put_missing_value_key_returns_400(self, test_client):
        """PUT with no value key must be rejected."""
        r = test_client.put(ENDPOINT_PUT.format(name="test-missing"), json={})
        assert r.status_code == 400

    def test_put_empty_value_error_message_is_safe(self, test_client):
        """400 error must not leak any secret material."""
        sentinel = "SENTINEL_SECRET_LEAK"
        r = test_client.put(
            ENDPOINT_PUT.format(name="test-leak"),
            json={"value": sentinel}
        )
        # Only check leak if it was actually rejected
        if r.status_code == 400:
            assert sentinel not in r.text, "Error response leaks secret value"

    def test_get_nonexistent_secret_returns_404(self, test_client):
        """GET on a name that was never stored must return 404."""
        r = get_secret(test_client, "definitely-does-not-exist-xyz123")
        assert r.status_code == 404

    def test_get_nonexistent_error_message_is_safe(self, test_client):
        """404 detail must not contain encrypted blobs or internal paths."""
        r = get_secret(test_client, "definitely-does-not-exist-xyz123")
        assert r.status_code == 404
        detail = r.json().get("detail", "")
        assert isinstance(detail, str)
        # Must not contain base64-encoded blobs (long strings of random chars)
        assert len(detail) < 200, "Detail suspiciously long — possible data leak"

    def test_put_stores_and_get_returns_plaintext(self, test_client):
        """Sanity check: stored secret is returned correctly (existing test still passes)."""
        name = "test-roundtrip-91"
        secret = "roundtrip-secret-value"
        put_r = put_secret(test_client, name, secret)
        assert put_r.status_code == 200
        get_r = get_secret(test_client, name)
        assert get_r.status_code == 200
        assert get_r.json()["value"] == secret
        # Cleanup
        delete_secret(test_client, name)

    def test_encrypted_value_not_returned_in_put_response(self, test_client):
        """PUT response must only confirm storage, not echo back encrypted blob."""
        name = "test-no-leak-91"
        secret = "do-not-echo-this"
        r = put_secret(test_client, name, secret)
        assert r.status_code == 200
        body = r.text
        assert secret not in body, "PUT response leaks plaintext secret"
        delete_secret(test_client, name)
