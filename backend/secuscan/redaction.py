import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Placeholder ───────────────────────────────────────────────────────────────

REDACTED = "[REDACTED]"

# ── Secret patterns ───────────────────────────────────────────────────────────
# Each tuple is (name, compiled_regex).
# Ordering matters: more specific patterns should come before catch-all ones.

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Bearer / OAuth tokens in Authorization headers
    (
        "bearer_token",
        re.compile(
            r"((?:Authorization|authorization)\s*:\s*Bearer\s+)"
            r"([A-Za-z0-9\-._~+/]{16,}={0,2})",
            re.IGNORECASE,
        ),
    ),
    # Basic auth in Authorization header
    (
        "basic_auth",
        re.compile(
            r"((?:Authorization|authorization)\s*:\s*Basic\s+)"
            r"([A-Za-z0-9+/]{8,}={0,2})",
            re.IGNORECASE,
        ),
    ),
    # Generic Authorization header value (catches other schemes)
    (
        "auth_header",
        re.compile(
            r"((?:Authorization|X-Auth-Token|X-Api-Key|X-Access-Token)\s*:\s*)"
            r"(\S{8,})",
            re.IGNORECASE,
        ),
    ),
    # Inline bearer token in URLs or JSON values
    (
        "bearer_inline",
        re.compile(
            r'((?:bearer|token)["\s:=]+)([A-Za-z0-9\-._~+/]{20,}={0,2})',
            re.IGNORECASE,
        ),
    ),
    # AWS access key id  (AKIA…)
    (
        "aws_access_key",
        re.compile(r"(AKIA[0-9A-Z]{16})", re.IGNORECASE),
    ),
    # AWS secret access key (typically 40 base64 chars after label)
    (
        "aws_secret_key",
        re.compile(
            r"(aws_secret_access_key\s*[=:]\s*)([A-Za-z0-9/+]{40})",
            re.IGNORECASE,
        ),
    ),
    # GCP / service-account private key material
    (
        "gcp_private_key",
        re.compile(
            r"(-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)"
            r"(.+?)"
            r"(-----END (?:RSA |EC )?PRIVATE KEY-----)",
            re.DOTALL,
        ),
    ),
    # API key / secret in common query-string or JSON shapes
    # e.g.  api_key=abc123  apikey: "abc"  secret_key = "xyz"
    (
        "api_key",
        re.compile(
            r"((?:api[_-]?key|apikey|api[_-]?secret|secret[_-]?key|"
            r"client[_-]?secret|app[_-]?secret)\s*[=:\"'\s]{1,4})"
            r"([A-Za-z0-9\-._~+/!@#%^&*]{8,})",
            re.IGNORECASE,
        ),
    ),
    # Password assignment strings
    # e.g.  password=hunter2  passwd: "abc"  PASSWORD = 'xyz'
    (
        "password",
        re.compile(
            r"((?:password|passwd|pass|pwd)\s*[=:\"'\s]{1,4})"
            r"([^\s\"'&;,]{6,})",
            re.IGNORECASE,
        ),
    ),
    # Session / cookie values
    # e.g.  Set-Cookie: session=abc123  Cookie: PHPSESSID=xyz
    (
        "session_cookie",
        re.compile(
            r"((?:Set-Cookie\s*:\s*|Cookie\s*:\s*)"
            r"(?:[A-Za-z0-9_\-]+\s*=\s*)*"
            r"(?:session(?:id)?|PHPSESSID|auth_token|access_token|"
            r"refresh_token|csrf[_-]?token|remember[_-]?token)\s*=\s*)"
            r"([A-Za-z0-9\-._~+/%]{8,})",
            re.IGNORECASE,
        ),
    ),
    # Private token patterns (GitLab glpat-, GitHub ghp_/ghs_/gho_)
    (
        "vcs_token",
        re.compile(
            r"(glpat-[A-Za-z0-9_\-]{20,}"
            r"|gh[pousr]_[A-Za-z0-9]{36,})",
            re.IGNORECASE,
        ),
    ),
    # Slack tokens  (xoxb-, xoxp-, xoxa-, xoxs-)
    (
        "slack_token",
        re.compile(r"(xox[bpas]-[0-9A-Za-z\-]{16,})", re.IGNORECASE),
    ),
    # Stripe secret keys  (sk_live_…  sk_test_…)
    (
        "stripe_key",
        re.compile(r"(sk_(?:live|test)_[A-Za-z0-9]{24,})", re.IGNORECASE),
    ),
    # Vault references (e.g. vault:secret_name or vault://secret_name)
    (
        "vault_ref",
        re.compile(
            r"((?:vault://|vault\s*:\s*)\s*)([A-Za-z0-9_\-\./]+)",
            re.IGNORECASE,
        ),
    ),
    # Generic long hex secrets often used as tokens (≥ 32 hex chars after label)
    (
        "hex_secret",
        re.compile(
            r"((?:token|secret|key|hash|salt)\s*[=:\"'\s]{1,4})"
            r"([0-9a-fA-F]{32,})",
            re.IGNORECASE,
        ),
    ),
]


# ── Public API ────────────────────────────────────────────────────────────────


def redact(text: str) -> str:
    if not text:
        return text

    redacted = text
    for name, pattern in _PATTERNS:
        try:
            redacted, n = _apply_pattern(name, pattern, redacted)
            if n:
                logger.debug("redaction: pattern=%s replacements=%d", name, n)
        except Exception as exc:  # pragma: no cover
            # Never let a buggy pattern break the pipeline.
            logger.warning("redaction: pattern=%s raised %s — skipped", name, exc)

    return redacted


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return data
    result: dict[str, Any] = {}
    for key, value in data.items():
        result[key] = _redact_value(value)
    return result


# Keys whose values are unconditionally redacted in task inputs regardless of
# value format.  Matched case-insensitively against the full key name.
_SENSITIVE_INPUT_KEYS: frozenset[str] = frozenset({
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "secret_key",
    "password",
    "passwd",
    "pass",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "auth",
    "auth_token",
    "authorization",
    "credentials",
    "private_key",
    "client_secret",
    "webhook_secret",
    "signing_key",
    "encryption_key",
})


def redact_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        return inputs

    result: dict[str, Any] = {}
    for key, value in inputs.items():
        if key.lower() in _SENSITIVE_INPUT_KEYS:
            result[key] = REDACTED
        else:
            result[key] = _redact_value(value)
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return redact_dict(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def _apply_pattern(
    name: str, pattern: re.Pattern[str], text: str
) -> tuple[str, int]:
    groups = pattern.groups  # number of capture groups
    count = 0

    if groups == 0:
        # No groups — replace entire match
        def _replace_full(m: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return REDACTED

        return pattern.sub(_replace_full, text), count

    if groups == 1:
        # Single group — replace only the captured group
        def _replace_g1(m: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return REDACTED

        return pattern.sub(_replace_g1, text), count

    if groups == 2:
        # Two groups: keep group 1 (label), redact group 2 (value)
        def _replace_g2(m: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return m.group(1) + REDACTED

        return pattern.sub(_replace_g2, text), count

    if groups == 3:
        # Three groups: keep groups 1 and 3, redact group 2 (e.g. PEM body)
        def _replace_g3(m: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return m.group(1) + REDACTED + m.group(3)

        return pattern.sub(_replace_g3, text), count

    # Fallback: replace whole match
    def _replace_fallback(m: re.Match[str]) -> str:  # pragma: no cover
        nonlocal count
        count += 1
        return REDACTED

    return pattern.sub(_replace_fallback, text), count