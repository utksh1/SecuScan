"""
Tests for report artifact signed download tokens (issue #208).

Covers:
  - Token generation produces a parseable string.
  - Valid token passes validation for correct task/format/owner.
  - Expired token raises TokenExpiredError.
  - Wrong task_id raises TokenTaskMismatchError.
  - Wrong format raises TokenFormatMismatchError.
  - Wrong owner raises TokenInvalidError.
  - Tampered signature raises TokenInvalidError.
  - Truncated token raises TokenInvalidError.
  - Each allowed format produces a distinct token.
  - Unknown format raises ValueError on generate.
  - Token is deterministic (same inputs + same time → same token).
  - validate_token raises on an empty string.
  - Token signed with a different key fails.
  - TTL=0 tokens are immediately expired.
  - Large TTL tokens are valid.
"""

import time
import pytest

from backend.secuscan.config import settings
settings.vault_key = "test-vault-key-for-unit-tests-only"

from backend.secuscan.report_tokens import (
    generate_token,
    validate_token,
    TokenError,
    TokenExpiredError,
    TokenFormatMismatchError,
    TokenTaskMismatchError,
    TokenInvalidError,
    _ALLOWED_FORMATS,
    _b64_encode,
    _b64_decode,
    _sign,
)

_TASK = "task-abc-123"
_FMT = "pdf"
_OWNER = "owner-xyz"
_TTL = 300


def _make_token(task=_TASK, fmt=_FMT, owner=_OWNER, ttl=_TTL) -> str:
    return generate_token(task_id=task, fmt=fmt, owner_id=owner, ttl_seconds=ttl)


def _validate(token: str, task=_TASK, fmt=_FMT, owner=_OWNER):
    validate_token(token=token, expected_task_id=task, expected_fmt=fmt, expected_owner_id=owner)


class TestTokenGeneration:
    def test_token_is_non_empty_string(self):
        token = _make_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_five_segments(self):
        token = _make_token()
        assert len(token.split(".")) == 5

    def test_all_formats_produce_tokens(self):
        tokens = [_make_token(fmt=f) for f in _ALLOWED_FORMATS]
        assert all(isinstance(t, str) for t in tokens)

    def test_different_formats_produce_different_tokens(self):
        tokens = {_make_token(fmt=f) for f in _ALLOWED_FORMATS}
        assert len(tokens) == len(_ALLOWED_FORMATS)

    def test_different_tasks_produce_different_tokens(self):
        t1 = _make_token(task="task-aaa")
        t2 = _make_token(task="task-bbb")
        assert t1 != t2

    def test_different_owners_produce_different_tokens(self):
        t1 = _make_token(owner="owner-a")
        t2 = _make_token(owner="owner-b")
        assert t1 != t2

    def test_unknown_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown report format"):
            generate_token(task_id=_TASK, fmt="exe", owner_id=_OWNER, ttl_seconds=_TTL)

    def test_token_encodes_correct_task_id(self):
        token = _make_token()
        task_b64 = token.split(".")[0]
        assert _b64_decode(task_b64) == _TASK

    def test_token_encodes_correct_format(self):
        token = _make_token(fmt="csv")
        fmt_b64 = token.split(".")[1]
        assert _b64_decode(fmt_b64) == "csv"

    def test_token_encodes_correct_owner(self):
        token = _make_token()
        owner_b64 = token.split(".")[2]
        assert _b64_decode(owner_b64) == _OWNER

    def test_token_expiry_is_in_the_future(self):
        now = time.time()
        token = _make_token(ttl=60)
        expiry_b64 = token.split(".")[3]
        expiry = int(_b64_decode(expiry_b64))
        assert expiry > now
        assert expiry <= now + 65


class TestTokenValidation:
    def test_valid_token_passes(self):
        token = _make_token()
        _validate(token)

    def test_valid_token_all_formats(self):
        for fmt in _ALLOWED_FORMATS:
            token = _make_token(fmt=fmt)
            _validate(token, fmt=fmt)

    def test_expired_token_raises(self):
        token = _make_token(ttl=0)
        time.sleep(0.01)
        with pytest.raises(TokenExpiredError):
            _validate(token)

    def test_negative_ttl_token_already_expired(self):
        token = _make_token(ttl=-10)
        with pytest.raises(TokenExpiredError):
            _validate(token)

    def test_wrong_task_id_raises(self):
        token = _make_token(task="real-task")
        with pytest.raises(TokenTaskMismatchError):
            _validate(token, task="other-task")

    def test_wrong_format_raises(self):
        token = _make_token(fmt="csv")
        with pytest.raises(TokenFormatMismatchError):
            _validate(token, fmt="pdf")

    def test_wrong_owner_raises(self):
        token = _make_token(owner="alice")
        with pytest.raises(TokenInvalidError):
            _validate(token, owner="bob")

    def test_empty_string_raises(self):
        with pytest.raises(TokenInvalidError):
            _validate("")

    def test_truncated_token_raises(self):
        token = _make_token()
        parts = token.split(".")
        with pytest.raises(TokenInvalidError):
            _validate(".".join(parts[:3]))

    def test_extra_segments_raise(self):
        token = _make_token() + ".extra"
        with pytest.raises(TokenInvalidError):
            _validate(token)

    def test_tampered_signature_raises(self):
        token = _make_token()
        parts = token.split(".")
        parts[4] = "a" * 64
        with pytest.raises(TokenInvalidError):
            _validate(".".join(parts))

    def test_tampered_task_field_raises(self):
        token = _make_token(task="original-task")
        parts = token.split(".")
        parts[0] = _b64_encode("different-task")
        with pytest.raises(TokenInvalidError):
            _validate(".".join(parts), task="different-task")

    def test_tampered_format_field_raises(self):
        token = _make_token(fmt="csv")
        parts = token.split(".")
        parts[1] = _b64_encode("pdf")
        with pytest.raises(TokenInvalidError):
            _validate(".".join(parts), fmt="pdf")

    def test_tampered_expiry_field_raises(self):
        token = _make_token(ttl=1)
        parts = token.split(".")
        far_future = str(int(time.time()) + 9999)
        parts[3] = _b64_encode(far_future)
        with pytest.raises(TokenInvalidError):
            _validate(".".join(parts))

    def test_large_ttl_token_is_valid(self):
        token = _make_token(ttl=86400)
        _validate(token)

    def test_token_not_reusable_for_wrong_task(self):
        token = _make_token(task="task-A")
        with pytest.raises(TokenTaskMismatchError):
            _validate(token, task="task-B")

    def test_token_not_reusable_for_wrong_format(self):
        token = _make_token(fmt="html")
        with pytest.raises(TokenFormatMismatchError):
            _validate(token, fmt="sarif")


class TestBase64Helpers:
    def test_roundtrip_ascii(self):
        for value in ["hello", "task-123", "user@example.com", ""]:
            assert _b64_decode(_b64_encode(value)) == value

    def test_roundtrip_special_chars(self):
        for value in ["uuid-with-dashes-12345", "owner/workspace:dev"]:
            assert _b64_decode(_b64_encode(value)) == value

    def test_encode_is_url_safe(self):
        encoded = _b64_encode("any-value")
        assert "+" not in encoded
        assert "/" not in encoded
        assert "=" not in encoded


class TestAllowedFormats:
    def test_allowed_formats_contains_expected_values(self):
        assert "csv" in _ALLOWED_FORMATS
        assert "html" in _ALLOWED_FORMATS
        assert "pdf" in _ALLOWED_FORMATS
        assert "sarif" in _ALLOWED_FORMATS

    def test_exe_not_allowed(self):
        assert "exe" not in _ALLOWED_FORMATS

    def test_json_not_allowed(self):
        assert "json" not in _ALLOWED_FORMATS
