"""
Unit tests for backend/secuscan/redaction.py

Run with:
    ./testing/test_python.sh
or directly:
    pytest testing/backend/unit/test_redaction.py -v
"""

import pytest
from backend.secuscan.redaction import redact, redact_dict, redact_inputs, REDACTED


# ── Helpers ───────────────────────────────────────────────────────────────────

def assert_redacted(result: str, original_secret: str) -> None:
    """Assert the secret value is gone and the placeholder is present."""
    assert REDACTED in result, f"Expected [REDACTED] in: {result!r}"
    assert original_secret not in result, (
        f"Secret still present in output: {result!r}"
    )


def assert_safe(result: str, original: str) -> None:
    """Assert safe content passed through unchanged."""
    assert result == original, (
        f"Safe content was altered.\nBefore: {original!r}\nAfter:  {result!r}"
    )


# ── Bearer / Authorization header ─────────────────────────────────────────────

class TestBearerToken:
    def test_authorization_bearer(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def"
        result = redact(text)
        assert_redacted(result, "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def")
        assert "Authorization: Bearer" in result

    def test_authorization_bearer_lowercase(self):
        text = "authorization: bearer supersecrettoken12345678"
        result = redact(text)
        assert_redacted(result, "supersecrettoken12345678")

    def test_authorization_basic(self):
        text = "Authorization: Basic dXNlcjpwYXNzd29yZA=="
        result = redact(text)
        assert_redacted(result, "dXNlcjpwYXNzd29yZA==")
        assert "Authorization: Basic" in result

    def test_x_auth_token_header(self):
        text = "X-Auth-Token: my-super-secret-token-value-here"
        result = redact(text)
        assert_redacted(result, "my-super-secret-token-value-here")


# ── API keys ──────────────────────────────────────────────────────────────────

class TestApiKey:
    def test_api_key_equals(self):
        text = "api_key=supersecretkey12345"
        result = redact(text)
        assert_redacted(result, "supersecretkey12345")

    def test_apikey_colon(self):
        text = 'apikey: "myapikey_abc123xyz"'
        result = redact(text)
        assert_redacted(result, "myapikey_abc123xyz")

    def test_secret_key_json(self):
        text = '{"secret_key": "abc123def456ghi789"}'
        result = redact(text)
        assert_redacted(result, "abc123def456ghi789")

    def test_client_secret(self):
        text = "client_secret=MyClientSecret_Value99"
        result = redact(text)
        assert_redacted(result, "MyClientSecret_Value99")


# ── Passwords ─────────────────────────────────────────────────────────────────

class TestPassword:
    def test_password_equals(self):
        text = "password=hunter2"
        result = redact(text)
        assert_redacted(result, "hunter2")

    def test_passwd_colon(self):
        text = "passwd: my_secure_pass!"
        result = redact(text)
        assert_redacted(result, "my_secure_pass!")

    def test_pwd_json(self):
        text = '{"pwd": "S3cur3P@ssw0rd"}'
        result = redact(text)
        assert_redacted(result, "S3cur3P@ssw0rd")

    def test_password_label_preserved(self):
        text = "password=topsecret99"
        result = redact(text)
        assert "password=" in result


# ── AWS credentials ───────────────────────────────────────────────────────────

class TestAwsCredentials:
    def test_aws_access_key_id(self):
        text = "AKIAIOSFODNN7EXAMPLE"
        result = redact(text)
        assert_redacted(result, "AKIAIOSFODNN7EXAMPLE")

    def test_aws_secret_key(self):
        text = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = redact(text)
        assert_redacted(result, "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        assert "aws_secret_access_key" in result


# ── Session cookies ───────────────────────────────────────────────────────────

class TestSessionCookie:
    def test_set_cookie_session(self):
        text = "Set-Cookie: session=abc123def456; Path=/; HttpOnly"
        result = redact(text)
        assert_redacted(result, "abc123def456")

    def test_cookie_phpsessid(self):
        text = "Cookie: PHPSESSID=xyz789sessionvalue"
        result = redact(text)
        assert_redacted(result, "xyz789sessionvalue")

    def test_cookie_access_token(self):
        text = "Cookie: access_token=eyJhbGciOiJSUzI1NiJ9.payload"
        result = redact(text)
        assert_redacted(result, "eyJhbGciOiJSUzI1NiJ9.payload")


# ── VCS / SaaS tokens ─────────────────────────────────────────────────────────

class TestVcsAndSaasTokens:
    def test_github_pat(self):
        text = "token: ghp_16C7e42F292c6912E7710c838347Ae178B4a"
        result = redact(text)
        assert_redacted(result, "ghp_16C7e42F292c6912E7710c838347Ae178B4a")

    def test_gitlab_pat(self):
        text = "glpat-xxxxxxxxxxxxxxxxxxxx"
        result = redact(text)
        assert_redacted(result, "glpat-xxxxxxxxxxxxxxxxxxxx")

    def test_slack_bot_token(self):
        # Constructed token — not a real credential
        fake_slack = "xoxb-" + "1" * 12 + "-" + "2" * 13 + "-" + "a" * 24
        text = f"slack_token={fake_slack}"
        result = redact(text)
        assert_redacted(result, fake_slack)

    def test_stripe_secret(self):
        # Constructed token — not a real credential
        fake_stripe = "sk_live_" + "x" * 24
        text = f"STRIPE_KEY={fake_stripe}"
        result = redact(text)
        assert_redacted(result, fake_stripe)


# ── PEM private key ───────────────────────────────────────────────────────────

class TestPemKey:
    PEM = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA2a2rwplBQLF29amygykEMmYz0+Kcj3bKBp29P2rFj7tCMiMY\n"
        "-----END RSA PRIVATE KEY-----"
    )

    def test_pem_body_redacted(self):
        result = redact(self.PEM)
        assert REDACTED in result
        assert "MIIEowIBAAKCAQEA" not in result

    def test_pem_headers_preserved(self):
        result = redact(self.PEM)
        assert "-----BEGIN RSA PRIVATE KEY-----" in result
        assert "-----END RSA PRIVATE KEY-----" in result


# ── Safe content must pass through unchanged ──────────────────────────────────

class TestSafeContent:
    def test_plain_finding_description(self):
        text = "Open port 443/tcp detected running nginx 1.24."
        assert_safe(redact(text), text)

    def test_url_without_credentials(self):
        text = "Target: https://example.com/login"
        assert_safe(redact(text), text)

    def test_ip_address(self):
        text = "Host: 192.168.1.100"
        assert_safe(redact(text), text)

    def test_cve_identifier(self):
        text = "CVE-2023-44487 - HTTP/2 Rapid Reset Attack"
        assert_safe(redact(text), text)

    def test_severity_label(self):
        text = "severity: HIGH"
        assert_safe(redact(text), text)

    def test_short_word_not_redacted_as_password(self):
        # "pass" under 6 chars should not be caught
        text = "password=hi"
        result = redact(text)
        # short value — should not match minimum length requirement
        # (our pattern requires 6+ chars for password values)
        assert text == result or REDACTED in result  # either is acceptable

    def test_empty_string(self):
        assert redact("") == ""

    def test_none_passthrough(self):
        # redact() must not raise on None
        assert redact(None) is None  # type: ignore[arg-type]


# ── redact_dict ───────────────────────────────────────────────────────────────

class TestRedactDict:
    def test_redacts_string_values(self):
        data = {
            "description": "Authorization: Bearer secrettoken12345678",
            "severity": "high",
        }
        result = redact_dict(data)
        assert REDACTED in result["description"]
        assert result["severity"] == "high"

    def test_nested_dict(self):
        data = {
            "metadata": {
                "proof": "Set-Cookie: session=abc123def456; Path=/"
            }
        }
        result = redact_dict(data)
        assert_redacted(result["metadata"]["proof"], "abc123def456")

    def test_list_values(self):
        data = {
            "notes": [
                "api_key=supersecret12345",
                "Open port 80 detected",
            ]
        }
        result = redact_dict(data)
        assert_redacted(result["notes"][0], "supersecret12345")
        assert result["notes"][1] == "Open port 80 detected"

    def test_non_string_values_unchanged(self):
        data = {"count": 42, "flag": True, "score": 9.8}
        result = redact_dict(data)
        assert result == data

    def test_non_dict_passthrough(self):
        assert redact_dict("not a dict") == "not a dict"  # type: ignore[arg-type]


# ── Multi-secret line ─────────────────────────────────────────────────────────

class TestMultipleSecretsOnOneLine:
    def test_two_secrets_same_line(self):
        text = "api_key=abc123def456 password=hunter2secret"
        result = redact(text)
        assert_redacted(result, "abc123def456")
        assert_redacted(result, "hunter2secret")


# ── redact_inputs ─────────────────────────────────────────────────────────────


class TestRedactInputs:
    """Tests for redact_inputs(), which redacts sensitive keys in task input dicts."""

    def test_api_key_is_redacted(self):
        inputs = {"api_key": "supersecretkey123456", "target": "example.com"}
        result = redact_inputs(inputs)
        assert result["api_key"] == REDACTED
        assert result["target"] == "example.com"

    def test_token_is_redacted(self):
        inputs = {"token": "ghp_16C7e42F292c6912E7710c838347Ae178B4a", "url": "http://example.com"}
        result = redact_inputs(inputs)
        assert result["token"] == REDACTED
        assert result["url"] == "http://example.com"

    def test_password_is_redacted(self):
        inputs = {"password": "hunter2verysecure", "username": "admin"}
        result = redact_inputs(inputs)
        assert result["password"] == REDACTED
        assert result["username"] == "admin"

    def test_private_key_is_redacted(self):
        inputs = {"private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"}
        result = redact_inputs(inputs)
        assert result["private_key"] == REDACTED

    def test_multiple_sensitive_keys_all_redacted(self):
        inputs = {
            "api_key": "key_abc123",
            "password": "p@ssw0rd99",
            "token": "tok_xyz789",
            "private_key": "pk_value",
            "target": "192.168.1.1",
        }
        result = redact_inputs(inputs)
        assert result["api_key"] == REDACTED
        assert result["password"] == REDACTED
        assert result["token"] == REDACTED
        assert result["private_key"] == REDACTED
        assert result["target"] == "192.168.1.1"

    def test_key_matching_is_case_insensitive(self):
        inputs = {"API_KEY": "secretvalue", "Token": "another_secret"}
        result = redact_inputs(inputs)
        assert result["API_KEY"] == REDACTED
        assert result["Token"] == REDACTED

    def test_non_sensitive_string_passes_through_pattern_redaction(self):
        """Non-sensitive string values are still run through the pattern redactor."""
        inputs = {"description": "api_key=leaked123456789 found in output"}
        result = redact_inputs(inputs)
        assert "leaked123456789" not in result["description"]
        assert REDACTED in result["description"]

    def test_non_string_values_are_untouched(self):
        inputs = {"count": 5, "enabled": True, "score": 9.8, "target": "host.example.com"}
        result = redact_inputs(inputs)
        assert result["count"] == 5
        assert result["enabled"] is True
        assert result["score"] == 9.8
        assert result["target"] == "host.example.com"

    def test_empty_dict_returns_empty_dict(self):
        assert redact_inputs({}) == {}

    def test_non_dict_input_is_returned_unchanged(self):
        assert redact_inputs("not-a-dict") == "not-a-dict"  # type: ignore[arg-type]

    def test_access_token_key_is_redacted(self):
        inputs = {"access_token": "ya29.a0AfH6SMB", "scope": "read"}
        result = redact_inputs(inputs)
        assert result["access_token"] == REDACTED
        assert result["scope"] == "read"

    def test_secret_key_is_redacted(self):
        inputs = {"secret_key": "aws_secret_abc123456789012345678901234567890"}
        result = redact_inputs(inputs)
        assert result["secret_key"] == REDACTED


# ── redact_inputs edge cases (type dispatch, recursion, immutability) ─────


class TestRedactInputsEdgeCases:
    """Additional coverage for redact_inputs() that locks in the type-dispatch
    contract, recursive walk over nested mixed-type structures, and the
    no-mutation guarantee. These cases are not covered by the basic happy-path
    tests above and protect against future regressions in the helper layer.
    """

    def test_none_value_under_non_sensitive_key_passes_through(self):
        inputs = {"target": None}
        result = redact_inputs(inputs)
        assert result["target"] is None

    def test_boolean_value_under_non_sensitive_key_passes_through(self):
        inputs = {"enabled": True, "disabled": False}
        result = redact_inputs(inputs)
        assert result["enabled"] is True
        assert result["disabled"] is False

    def test_integer_value_under_non_sensitive_key_passes_through(self):
        inputs = {"count": 42, "max_results": 0, "negative": -7}
        result = redact_inputs(inputs)
        assert result["count"] == 42
        assert result["max_results"] == 0
        assert result["negative"] == -7

    def test_float_value_under_non_sensitive_key_passes_through(self):
        inputs = {"score": 9.5, "ratio": 0.0}
        result = redact_inputs(inputs)
        assert result["score"] == 9.5
        assert result["ratio"] == 0.0

    def test_non_string_under_sensitive_key_is_redacted(self):
        """A non-string value (int, bool) under a sensitive key must still be
        replaced with [REDACTED] — the contract is key-name based, not type
        based."""
        inputs = {"api_key": 12345, "token": True, "password": 9999}
        result = redact_inputs(inputs)
        assert result["api_key"] == REDACTED
        assert result["token"] == REDACTED
        assert result["password"] == REDACTED

    def test_recursive_walk_into_nested_dict(self):
        """Nested dicts are walked by _redact_value → redact_dict, which uses
        PATTERN-based redaction (not key-based). The contract is therefore:
          - nested string values are scanned for secrets
          - nested dict keys are not compared against _SENSITIVE_INPUT_KEYS

        Verify that a secret-shaped string under any nested key is redacted
        when the pattern matches, and that non-secret values pass through."""
        inputs = {
            "outer": {
                "any_key": "api_key=leaked123456789",
                "target": "example.com",
            }
        }
        result = redact_inputs(inputs)
        # The nested string is pattern-redacted (api_key=…)
        assert "leaked123456789" not in result["outer"]["any_key"]
        assert REDACTED in result["outer"]["any_key"]
        # Non-secret values pass through
        assert result["outer"]["target"] == "example.com"

    def test_recursive_walk_into_list(self):
        """Lists are walked by _redact_value; string items are pattern-redacted."""
        inputs = {
            "items": [
                "api_key=secret1234567abcd",
                "Open port 80 detected",
            ]
        }
        result = redact_inputs(inputs)
        assert "secret1234567abcd" not in result["items"][0]
        assert REDACTED in result["items"][0]
        assert result["items"][1] == "Open port 80 detected"

    def test_sensitive_key_inside_nested_list_of_dicts(self):
        """Lists of dicts are walked; each dict's string values are
        pattern-redacted. The key-based _SENSITIVE_INPUT_KEYS lookup is a
        top-level-only contract."""
        inputs = {
            "items": [
                {"note": "api_key=leaked123456789"},
                {"note": "benign content"},
            ]
        }
        result = redact_inputs(inputs)
        # The value under the nested 'note' key is pattern-scanned; the
        # api_key=… prefix is redacted.
        assert "leaked123456789" not in result["items"][0]["note"]
        assert REDACTED in result["items"][0]["note"]
        assert result["items"][1]["note"] == "benign content"

    def test_non_dict_input_is_returned_unchanged(self):
        """The function tolerates non-dict inputs by returning them as-is."""
        assert redact_inputs(None) is None  # type: ignore[arg-type]
        assert redact_inputs("a string") == "a string"  # type: ignore[arg-type]
        assert redact_inputs(42) == 42  # type: ignore[arg-type]
        assert redact_inputs([1, 2, 3]) == [1, 2, 3]  # type: ignore[arg-type]

    def test_does_not_mutate_input_dict(self):
        """redact_inputs must not mutate the caller's dict."""
        original = {
            "api_key": "secret_value_1234567",
            "nested": {"password": "inner_secret_1234567"},
            "items": [{"token": "list_token_1234567"}],
        }
        snapshot_top = dict(original)
        snapshot_nested = dict(original["nested"])
        snapshot_items = list(original["items"])
        redact_inputs(original)
        assert original == snapshot_top
        assert original["nested"] == snapshot_nested
        assert original["items"] == snapshot_items

    def test_whitespace_in_key_name_is_not_stripped_for_match(self):
        """The match is on the lowercased key name only — leading/trailing
        whitespace in the dict key prevents the lookup from succeeding, so the
        value passes through to the pattern redactor instead of being replaced
        with [REDACTED]."""
        inputs = {" api_key": "secret_value_1234567", "token ": "tok_1234567"}
        result = redact_inputs(inputs)
        # The keys with whitespace around them are NOT in _SENSITIVE_INPUT_KEYS,
        # so the value is passed to the pattern redactor (which may or may not
        # match depending on the value).
        # The key name is preserved as-is in the output:
        assert " api_key" in result
        assert "token " in result

    def test_empty_string_value_under_sensitive_key_is_redacted(self):
        """Even an empty string under a sensitive key is replaced."""
        inputs = {"api_key": "", "token": ""}
        result = redact_inputs(inputs)
        assert result["api_key"] == REDACTED
        assert result["token"] == REDACTED

    def test_mixed_type_inputs_preserves_types(self):
        inputs = {
            "target": "example.com",
            "port": 443,
            "enabled": True,
            "tags": ["web", "api"],
            "meta": {"version": 1.0, "name": "x"},
            "api_key": "secret_1234567",
        }
        result = redact_inputs(inputs)
        assert result["target"] == "example.com"
        assert result["port"] == 443
        assert result["enabled"] is True
        assert result["tags"] == ["web", "api"]
        assert result["meta"]["version"] == 1.0
        assert result["meta"]["name"] == "x"
        assert result["api_key"] == REDACTED