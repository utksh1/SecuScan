import pytest
from validation import (
    validate_target, validate_port, validate_url,
    sanitize_input, is_safe_path, match_pattern
)


def test_validate_target():
    # Valid IP target
    assert validate_target("192.168.1.1", safe_mode=True) == (True, "")

    # Valid hostname target
    assert validate_target("example.com", safe_mode=False) == (True, "")

    # Safe mode restrictions
    assert validate_target("8.8.8.8", safe_mode=True)[0] is False  # Public IP blocked in safe mode
    assert validate_target("military.mil", safe_mode=True)[0] is False  # Blocked TLD

    # Invalid targets
    assert validate_target("10.0.0.0/24")[0] is False  # Cannot pass CIDR as target directly
    assert validate_target("not!a!valid!hostname")[0] is False


def test_validate_port():
    assert validate_port(80) == (True, "")
    assert validate_port(65535) == (True, "")

    assert validate_port(0)[0] is False
    assert validate_port(65536)[0] is False
    assert validate_port(-1)[0] is False


def test_validate_url():
    assert validate_url("http://localhost:8080")[0] is True
    assert validate_url("https://example.com/path?param=value")[0] is True
    assert validate_url("http://192.168.1.1")[0] is True

    assert validate_url("ftp://example.com")[0] is False
    assert validate_url("not_a_url")[0] is False
    assert validate_url("http://")[0] is False


def test_sanitize_input():
    # Regular input should be unchanged
    assert sanitize_input("nmap -sV -p 80") == "nmap -sV -p 80"

    # Dangerous characters should be removed
    assert sanitize_input("127.0.0.1; rm -rf /") == "127.0.0.1 rm -rf /"
    assert sanitize_input("target.com | wget malicious.com") == "target.com  wget malicious.com"
    assert sanitize_input("test & echo hacked") == "test  echo hacked"


def test_is_safe_path():
    base = "/opt/secuscan/data"

    assert is_safe_path("report.txt", base) is True
    assert is_safe_path("subdir/file.json", base) is True

    # Absolute paths outside base
    assert is_safe_path("/etc/passwd", base) is False

    # Path traversal attempts
    assert is_safe_path("../../../etc/passwd", base) is False
    assert is_safe_path("subdir/../../etc/passwd", base) is False


def test_match_pattern():
    assert match_pattern("http_inspector", "http_*") is True
    assert match_pattern("nmap", "nmap") is True
    assert match_pattern("tls_inspector", "*inspector") is True
    assert match_pattern("dirb", "http_*") is False
