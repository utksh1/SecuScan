from backend.secuscan.vault import VaultCrypto


def _make_key():
    """Return a valid 32-byte key encoded as base64url."""
    import base64
    return base64.urlsafe_b64encode(b"0" * 32).decode("ascii")


def test_vault_key_not_base64_raises():
    bad_keys = [
        "not-base64!!!",
        "====invalid===",
        "YWJj",
    ]
    for key in bad_keys:
        try:
            VaultCrypto(key)
            raise AssertionError(f"Expected ValueError for key: {key!r}")
        except ValueError:
            pass


def test_vault_key_wrong_length_raises():
    import base64
    for length in [16, 31, 33, 64]:
        key = base64.urlsafe_b64encode(b"x" * length).decode("ascii")
        try:
            VaultCrypto(key)
            raise AssertionError(f"Expected ValueError for key length {length}")
        except ValueError as exc:
            assert "32 bytes" in str(exc)


def test_encrypt_produces_different_ciphertext_each_call():
    key = _make_key()
    crypto = VaultCrypto(key)
    ct1 = crypto.encrypt("same plaintext")
    ct2 = crypto.encrypt("same plaintext")
    assert ct1 != ct2


def test_decrypt_bad_base64_raises():
    key = _make_key()
    crypto = VaultCrypto(key)
    for bad_payload in ["not-valid!!!", "=!!!=", "YWJjZGVm"]:
        try:
            crypto.decrypt(bad_payload)
            raise AssertionError(f"Expected ValueError for payload: {bad_payload!r}")
        except ValueError:
            pass


def test_decrypt_tampered_ciphertext_raises():
    import base64
    key = _make_key()
    crypto = VaultCrypto(key)
    ciphertext = crypto.encrypt("secret data")
    # Flip a byte in the middle (tamper with the ciphertext, not just the nonce)
    blob = base64.urlsafe_b64decode(ciphertext)
    tampered = blob[:-1] + bytes([blob[-1] ^ 0xFF])
    tampered_b64 = base64.urlsafe_b64encode(tampered).decode("ascii")
    try:
        crypto.decrypt(tampered_b64)
        raise AssertionError("Expected ValueError for tampered ciphertext")
    except ValueError:
        pass


def test_decrypt_roundtrip_unicode():
    key = _make_key()
    crypto = VaultCrypto(key)
    plaintexts = [
        "",
        "hello world",
        "hello \u00e9\u00e0\u00fc",
        "\u4e2d\u6587\u5b57\u7b26",
        "emoji \U0001F4BB",
        "mixed: english + \u0d85\u0d86\u0d87",
    ]
    for pt in plaintexts:
        encrypted = crypto.encrypt(pt)
        assert encrypted != pt
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == pt


def test_decrypt_roundtrip_empty_string():
    key = _make_key()
    crypto = VaultCrypto(key)
    encrypted = crypto.encrypt("")
    assert encrypted
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == ""


class TestKeyFingerprint:
    def test_key_fingerprint_is_accessible(self):
        """key_fingerprint property is accessible on VaultCrypto instance."""
        import base64
        key_bytes = b"a1" + b"b2" * 15  # exactly 32 bytes
        key = base64.urlsafe_b64encode(key_bytes).decode("ascii")
        crypto = VaultCrypto(key)
        assert hasattr(crypto, "key_fingerprint")
        assert crypto.key_fingerprint is not None

    def test_key_fingerprint_matches_compute_fingerprint(self):
        """key_fingerprint returns the same value as _compute_fingerprint on the raw key."""
        import base64
        key_bytes = b"c3" + b"d4" * 15  # exactly 32 bytes
        key = base64.urlsafe_b64encode(key_bytes).decode("ascii")
        crypto = VaultCrypto(key)
        expected = VaultCrypto._compute_fingerprint(key_bytes)
        assert crypto.key_fingerprint == expected

    def test_key_fingerprint_is_stable(self):
        """Calling key_fingerprint multiple times returns the same value."""
        key = _make_key()
        crypto = VaultCrypto(key)
        fp1 = crypto.key_fingerprint
        fp2 = crypto.key_fingerprint
        fp3 = crypto.key_fingerprint
        assert fp1 == fp2 == fp3

    def test_key_fingerprint_is_colon_separated_hex(self):
        """Fingerprint is formatted as 8 colon-separated lowercase hex pairs."""
        import base64
        key_bytes = b"0123456789abcdef0123456789abcdef"
        key = base64.urlsafe_b64encode(key_bytes).decode("ascii")
        crypto = VaultCrypto(key)
        fp = crypto.key_fingerprint
        parts = fp.split(":")
        assert len(parts) == 8
        for part in parts:
            assert len(part) == 2
            int(part, 16)  # raises ValueError if not valid hex

    def test_different_keys_produce_different_fingerprints(self):
        """Two distinct keys produce two distinct fingerprints."""
        import base64
        key1 = base64.urlsafe_b64encode(b"11111111111111111111111111111111").decode("ascii")
        key2 = base64.urlsafe_b64encode(b"22222222222222222222222222222222").decode("ascii")
        crypto1 = VaultCrypto(key1)
        crypto2 = VaultCrypto(key2)
        assert crypto1.key_fingerprint != crypto2.key_fingerprint

    def test_key_fingerprint_property_is_read_only(self):
        """key_fingerprint has no setter — it cannot be overwritten."""
        key = _make_key()
        crypto = VaultCrypto(key)
        assert not hasattr(type(crypto).key_fingerprint, "fset") or type(crypto).key_fingerprint.fset is None


def test_encrypt_includes_header_prefix_and_key_id():
    """encrypt() output wire format starts with SV1: header prefix and key ID bytes."""
    import base64
    key = _make_key()
    crypto = VaultCrypto(key)
    encrypted = crypto.encrypt("my_secret")
    raw = base64.urlsafe_b64decode(encrypted.encode("ascii"))
    assert raw.startswith(b"SV1:")
    extracted_key_id = crypto.extract_key_id(encrypted)
    assert extracted_key_id == crypto.key_fingerprint


def test_extract_key_id_returns_none_for_legacy_payload():
    """extract_key_id returns None when passed a legacy unversioned payload."""
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _make_key()
    crypto = VaultCrypto(key)
    raw_key = base64.urlsafe_b64decode(key)

    # Construct legacy blob manually: nonce(12) + ciphertext + tag(16)
    nonce = b"123456789012"
    aesgcm = AESGCM(raw_key)
    ct = aesgcm.encrypt(nonce, b"secret", None)
    legacy_payload = base64.urlsafe_b64encode(nonce + ct).decode("ascii")

    assert crypto.extract_key_id(legacy_payload) is None
    # Decrypting legacy payload must still succeed
    assert crypto.decrypt(legacy_payload) == "secret"


def test_vault_keyring_rotation():
    """VaultCrypto with fallback_keys decrypts blobs encrypted with primary or fallback keys."""
    import base64
    key_old = base64.urlsafe_b64encode(b"11111111111111111111111111111111").decode("ascii")
    key_new = base64.urlsafe_b64encode(b"22222222222222222222222222222222").decode("ascii")

    crypto_old = VaultCrypto(key_old)
    encrypted_old = crypto_old.encrypt("old_secret")

    # New active crypto instance with fallback_keys
    crypto_new = VaultCrypto(key_new, fallback_keys=[key_old])

    encrypted_new = crypto_new.encrypt("new_secret")

    # Should decrypt both old and new encrypted payloads
    assert crypto_new.decrypt(encrypted_new) == "new_secret"
    assert crypto_new.decrypt(encrypted_old) == "old_secret"


def test_header_prefix_collision_fallback():
    """A legacy blob whose nonce starts with b'SV1:' is correctly decrypted via fallback."""
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _make_key()
    crypto = VaultCrypto(key)
    raw_key = base64.urlsafe_b64decode(key)

    # Construct legacy nonce that starts with b"SV1:"
    nonce = b"SV1:12345678"  # exactly 12 bytes
    aesgcm = AESGCM(raw_key)
    ct = aesgcm.encrypt(nonce, b"collision_secret", None)
    legacy_collision_payload = base64.urlsafe_b64encode(nonce + ct).decode("ascii")

    # decrypt must not raise ValueError, but successfully decrypt via legacy fallback
    assert crypto.decrypt(legacy_collision_payload) == "collision_secret"


def test_payload_length_guards():
    """decrypt raises ValueError when payload length is below minimum required bytes."""
    import base64
    key = _make_key()
    crypto = VaultCrypto(key)

    # 1. Below 28 bytes (below minimum legacy length)
    short_raw = b"x" * 20
    short_payload = base64.urlsafe_b64encode(short_raw).decode("ascii")
    try:
        crypto.decrypt(short_payload)
        raise AssertionError("Expected ValueError for short payload")
    except ValueError as exc:
        assert "too short" in str(exc)

    # 2. Versioned header present (SV1:) but total length < 40 bytes
    short_versioned_raw = b"SV1:" + b"x" * 25
    short_versioned_payload = base64.urlsafe_b64encode(short_versioned_raw).decode("ascii")
    try:
        crypto.decrypt(short_versioned_payload)
        raise AssertionError("Expected ValueError for short versioned payload")
    except ValueError as exc:
        assert "verification failed" in str(exc) or "too short" in str(exc)

