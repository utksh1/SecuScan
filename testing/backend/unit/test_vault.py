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
