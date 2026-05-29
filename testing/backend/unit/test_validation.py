import pytest
from backend.secuscan.validation import (
    validate_target, validate_port, validate_port_range, validate_url,
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
    assert validate_target("10.0.0.0/24")[0] is True  # Private CIDR ranges are allowed in safe mode
    assert validate_target("not!a!valid!hostname")[0] is False


def test_validate_port():
    assert validate_port(80) == (True, "")
    assert validate_port(65535) == (True, "")
    assert validate_port(1) == (True, "")

    assert validate_port(0)[0] is False
    assert validate_port(65536)[0] is False
    assert validate_port(-1)[0] is False

    # Type guard: non-integer inputs must be rejected cleanly, not raise TypeError
    assert validate_port("80")[0] is False       # string
    assert validate_port(80.5)[0] is False       # float
    assert validate_port(True)[0] is False       # bool (subclass of int)
    assert validate_port(None)[0] is False       # None


def test_validate_url():
    assert validate_url("http://localhost:8080")[0] is True
    assert validate_url("https://localhost/path?param=value")[0] is True
    assert validate_url("http://192.168.1.1:8080/path")[0] is True
    assert validate_url("https://127.0.0.1/secure?x=1")[0] is True

    assert validate_url("ftp://example.com")[0] is False
    assert validate_url("http:///path")[0] is False
    assert validate_url("http://example.com /path")[0] is False
    assert validate_url("http://localhost:99999")[0] is False
    assert validate_url("http://example.com:port")[0] is False
    assert validate_url("not_a_url")[0] is False
    assert validate_url("http://")[0] is False


def test_sanitize_input():
    # Regular input should be unchanged
    assert sanitize_input("nmap -sV -p 80") == "nmap -sV -p 80"

    # Dangerous shell metacharacters should be removed
    assert sanitize_input("127.0.0.1; rm -rf /") == "127.0.0.1 rm -rf /"
    assert sanitize_input("target.com | wget malicious.com") == "target.com  wget malicious.com"
    assert sanitize_input("test & echo hacked") == "test  echo hacked"

    # Null byte: can truncate strings in C-backed tools (e.g. nmap)
    assert "\x00" not in sanitize_input("target\x00evil")

    # Tab: usable in argument injection in some shell contexts
    assert "\t" not in sanitize_input("target\t--evil-flag")

    # Output should be a plain string with no leading/trailing whitespace
    assert sanitize_input("  192.168.1.1  ") == "192.168.1.1"


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


def test_validate_port_range():
    # Single port
    assert validate_port_range("80") == (True, "")
    assert validate_port_range("1") == (True, "")
    assert validate_port_range("65535") == (True, "")

    # Plain range
    assert validate_port_range("1-1000") == (True, "")
    assert validate_port_range("443-443") == (True, "")

    # Comma-separated single ports
    assert validate_port_range("80,443") == (True, "")
    assert validate_port_range("22,80,443") == (True, "")

    # Mixed comma + range — this was the bug
    assert validate_port_range("80,443-8080") == (True, "")
    assert validate_port_range("22,80,443-8080") == (True, "")
    assert validate_port_range("22,80-90,443,8000-9000") == (True, "")

    # Invalid: out-of-range port
    assert validate_port_range("99999")[0] is False
    assert validate_port_range("80,99999")[0] is False

    # Invalid: inverted range
    assert validate_port_range("1000-80")[0] is False

    # Invalid: non-numeric
    assert validate_port_range("abc")[0] is False
    assert validate_port_range("80,bad")[0] is False