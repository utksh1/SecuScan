"""
Unit tests for backend.secuscan.redaction.redact().

Covers:
- Bearer tokens in Authorization headers are redacted
- Basic auth credentials in Authorization headers are redacted
- Generic Authorization / X-Api-Key header values are redacted
- AWS keys are redacted
- GitHub tokens are redacted
- Bearer tokens in JSON values are redacted
- Private keys are redacted
- redact() is idempotent
- redact() preserves non-matching content
- Empty string is handled
"""

import pytest

from backend.secuscan.redaction import redact, REDACTED


class TestRedactBearerToken:
    def test_redacts_bearer_token_in_authorization_header(self):
        """Bearer token in Authorization header is replaced with placeholder."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
        result = redact(text)
        assert REDACTED in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_redacts_bearer_token_case_insensitive(self):
        """Bearer token redaction is case-insensitive on header name."""
        text = "authorization: Bearer secret-token-here-12345678901234567890"
        result = redact(text)
        assert REDACTED in result
        assert "secret-token-here" not in result


class TestRedactBasicAuth:
    def test_redacts_basic_auth_credentials(self):
        """Basic auth credentials are redacted."""
        text = "Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ="
        result = redact(text)
        assert REDACTED in result
        assert "dXNlcm5hbWU6cGFzc3dvcmQ=" not in result


class TestRedactApiKeyHeader:
    def test_redacts_x_api_key_header(self):
        """X-Api-Key header values are redacted."""
        text = "X-Api-Key: my-super-secret-api-key-12345"
        result = redact(text)
        assert REDACTED in result
        assert "my-super-secret-api-key-12345" not in result


class TestRedactAwsKey:
    def test_redacts_aws_access_key_id(self):
        """AWS Access Key IDs are redacted."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = redact(text)
        assert REDACTED in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result


class TestRedactGitHubToken:
    def test_redacts_github_token(self):
        """GitHub personal access tokens are redacted."""
        text = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        result = redact(text)
        assert REDACTED in result
        assert "ghp_xxx" not in result


class TestRedactJsonBearer:
    def test_redacts_bearer_token_in_json_value(self):
        """Bearer tokens embedded in JSON strings are redacted."""
        text = '{"token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}'
        result = redact(text)
        assert REDACTED in result


class TestRedactPrivateKey:
    def test_redacts_rsa_private_key(self):
        """RSA private key blocks are redacted."""
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBALRiMLAHudeSA2I3UTf3bLg4dL7n\n-----END RSA PRIVATE KEY-----"
        result = redact(text)
        assert REDACTED in result
        assert "MIIBOgIBAAJBALRiMA" not in result

    def test_redacts_ec_private_key(self):
        """EC private key blocks are redacted."""
        text = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIGK2pR1bO7l5\n-----END EC PRIVATE KEY-----"
        result = redact(text)
        assert REDACTED in result


class TestRedactAuthHeader:
    def test_redacts_x_auth_token_header(self):
        """X-Auth-Token header values are redacted."""
        text = "X-Auth-Token: my-long-auth-token-value-12345"
        result = redact(text)
        assert REDACTED in result
        assert "my-long-auth-token-value-12345" not in result


class TestRedactPreservesContent:
    def test_preserves_non_secret_content(self):
        """Non-matching content is not modified."""
        text = "GET /api/v1/users HTTP/1.1\nHost: example.com"
        result = redact(text)
        assert "GET /api/v1/users" in result
        assert "Host: example.com" in result


class TestRedactIdempotent:
    def test_idempotent(self):
        """Calling redact twice produces the same result."""
        text = "Authorization: Bearer my-secret-token-12345678901234567890"
        result1 = redact(text)
        result2 = redact(result1)
        assert result1 == result2


class TestRedactEmptyInput:
    def test_handles_empty_string(self):
        """redact handles empty string without error."""
        result = redact("")
        assert result == ""

    def test_handles_none_like_input(self):
        """redact handles strings without any secrets without error."""
        result = redact("This is a normal text with no secrets at all.")
        assert "This is a normal text" in result
