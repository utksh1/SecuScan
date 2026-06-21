"""
Integration tests for GET /api/v1/admin/vault/diagnostics (issue #809).

Verifies the secure diagnostics contract:
- the route is admin-gated (401 without a valid admin key)
- it surfaces a non-secret, stable key fingerprint
- the fingerprint matches the configured key and never leaks key material
- it reports configured/false instead of erroring when no key is set.
"""

import base64

from backend.secuscan.config import settings
from backend.secuscan.vault import VaultCrypto


ADMIN_KEY = "valid-admin-key-long"  # >= 16 chars to pass the entropy check
ADMIN_HEADERS = {"X-API-Key": ADMIN_KEY}

ENDPOINT = "/api/v1/admin/vault/diagnostics"


def test_diagnostics_requires_admin_key(test_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    # No admin key supplied (the test client's default X-Api-Key is the
    # deployment key, not the admin key) -> 401.
    res = test_client.get(ENDPOINT)
    assert res.status_code == 401


def test_diagnostics_rejects_wrong_admin_key(test_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    res = test_client.get(ENDPOINT, headers={"X-API-Key": "wrong-key"})
    assert res.status_code == 401


def test_diagnostics_returns_fingerprint(test_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    res = test_client.get(ENDPOINT, headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["configured"] is True
    assert data["algorithm"] == "AES-256-GCM"
    assert data["key_source"] == "vault_key"  # conftest sets settings.vault_key
    assert data["fingerprint_algorithm"] == "sha256-trunc64"

    fingerprint = data["key_fingerprint"]
    assert fingerprint
    # Fingerprint matches the one derived from the active key.
    expected = VaultCrypto(settings.resolved_vault_key).key_fingerprint
    assert fingerprint == expected


def test_diagnostics_does_not_leak_key_material(test_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    res = test_client.get(ENDPOINT, headers=ADMIN_HEADERS)
    body = res.text
    raw_key = base64.urlsafe_b64decode(settings.resolved_vault_key)
    # Neither the configured seed, the encoded key, nor the raw key bytes
    # should appear anywhere in the response.
    assert settings.vault_key not in body
    assert settings.resolved_vault_key.decode("ascii") not in body
    assert raw_key.hex() not in body


def test_diagnostics_reports_plugin_signature_key_fallback(test_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "vault_key", None)
    monkeypatch.setattr(settings, "plugin_signature_key", "fallback-signing-key")

    res = test_client.get(ENDPOINT, headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["configured"] is True
    assert data["key_source"] == "plugin_signature_key"
    assert data["key_fingerprint"]


def test_diagnostics_reports_unconfigured_without_erroring(test_client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "vault_key", None)
    monkeypatch.setattr(settings, "plugin_signature_key", None)

    res = test_client.get(ENDPOINT, headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["configured"] is False
    assert data["key_source"] is None
    assert data["key_fingerprint"] is None
    assert data["algorithm"] == "AES-256-GCM"
