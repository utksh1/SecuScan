import pytest
import socket
import ipaddress
from backend.secuscan import validation as validation_module
from backend.secuscan.config import settings
from backend.secuscan.validation import (
    validate_target, validate_port, validate_port_range, validate_url,
    sanitize_input, is_safe_path, match_pattern
)
from backend.secuscan.routes import is_filesystem_target

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

def test_validate_target_safe_mode_blocks_public_hostname(monkeypatch):
    def fake_getaddrinfo(_host, *_args, **_kwargs):
        return [(socket.AF_INET, None, None, None, ("8.8.8.8", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert validate_target("example.com", safe_mode=True)[0] is False

def test_validate_target_safe_mode_blocks_multi_record_when_any_public(monkeypatch):
    """If any A/AAAA record is public, safe-mode must fail closed."""
    def fake_getaddrinfo(_host, *_args, **_kwargs):
        return [
            (socket.AF_INET, None, None, None, ("192.168.1.10", 0)),
            (socket.AF_INET, None, None, None, ("8.8.8.8", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert validate_target("multirecord.example", safe_mode=True)[0] is False

def test_validate_target_safe_mode_blocks_dns_rebinding_union(monkeypatch):
    """Rebinding/round-robin: validate_target resolves twice and validates the union."""
    calls = {"n": 0}

    def fake_getaddrinfo(_host, *_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return [(socket.AF_INET, None, None, None, ("192.168.1.10", 0))]
        return [(socket.AF_INET, None, None, None, ("8.8.8.8", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    ok, _msg = validate_target("rebind.example", safe_mode=True)
    assert ok is False
    assert calls["n"] >= 2

def test_validate_target_safe_mode_blocks_url_ip_literal():
    assert validate_target("http://8.8.8.8", safe_mode=True)[0] is False

def test_validate_target_ipv4_with_ipv6_allowed_network_does_not_crash(monkeypatch):
    monkeypatch.setattr(settings, "allowed_networks", ["fc00::/7"])
    ok, msg = validate_target("127.0.0.1", safe_mode=True)

    assert ok is False
    assert msg == "Target not within allowed networks in safe mode (SecuScan Guardrail)"


def test_validate_target_ipv6_with_ipv4_allowed_network_does_not_crash(monkeypatch):
    monkeypatch.setattr(settings, "allowed_networks", ["127.0.0.0/8"])
    ok, msg = validate_target("::1", safe_mode=True)

    assert ok is False
    assert msg == "Public IPs/networks not allowed in safe mode (SecuScan Guardrail)"


def test_validate_target_mixed_allowed_networks_uses_later_same_version_entry(monkeypatch):
    monkeypatch.setattr(settings, "allowed_networks", ["fc00::/7", "127.0.0.0/8"])
    ok, msg = validate_target("127.0.0.1", safe_mode=True)

    assert ok is True
    assert msg == ""

def test_validate_target_mixed_allowed_networks_uses_later_same_version_ipv6_entry(monkeypatch):
    monkeypatch.setattr(validation_module, "ALLOWED_PRIVATE", [ipaddress.ip_network("fc00::/7")])
    monkeypatch.setattr(settings, "allowed_networks", ["127.0.0.0/8", "fc00::/7"])

    ok, msg = validate_target("fd00::1", safe_mode=True)

    assert ok is True
    assert msg == ""

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

class TestIsFilesystemTarget:
    """
    Unit tests for is_filesystem_target().

    This function is the gatekeeper that decides whether a target
    should bypass validate_target(). Getting it wrong in the permissive
    direction causes safe-mode bypass (CVE-equivalent: issue #267).

    Rule: the function must return False for ANYTHING that is not
    unambiguously a local filesystem path. When in doubt, return False
    and let validate_target() do its job.
    """

    # ── Network addresses — must all return False ──────────────────────

    def test_cidr_public_ipv4_is_not_filesystem(self):
        """8.8.8.8/32 is the canonical attack payload from issue #267."""
        assert is_filesystem_target("8.8.8.8/32") is False

    def test_cidr_public_class_b_is_not_filesystem(self):
        assert is_filesystem_target("1.1.1.1/16") is False

    def test_cidr_private_is_not_filesystem(self):
        """Even private CIDRs must go through validate_target — not our call here."""
        assert is_filesystem_target("192.168.1.0/24") is False

    def test_cidr_rfc1918_10_is_not_filesystem(self):
        assert is_filesystem_target("10.0.0.0/8") is False

    def test_cidr_loopback_is_not_filesystem(self):
        assert is_filesystem_target("127.0.0.1/32") is False

    def test_bare_ipv4_is_not_filesystem(self):
        assert is_filesystem_target("192.168.1.1") is False

    def test_bare_public_ip_is_not_filesystem(self):
        assert is_filesystem_target("8.8.8.8") is False

    def test_hostname_is_not_filesystem(self):
        assert is_filesystem_target("example.com") is False

    def test_hostname_with_path_is_not_filesystem(self):
        """A hostname with a URL path should NOT be treated as a local path."""
        assert is_filesystem_target("example.com/robots.txt") is False

    def test_http_url_is_not_filesystem(self):
        assert is_filesystem_target("http://192.168.1.1/path") is False

    def test_https_url_is_not_filesystem(self):
        assert is_filesystem_target("https://example.com/path") is False

    def test_bare_tilde_is_not_filesystem(self):
        """Bare ~ alone is NOT a valid home-relative path — must not match."""
        assert is_filesystem_target("~") is False

    def test_tilde_without_slash_is_not_filesystem(self):
        """~evil.com would have matched the old '~' prefix — must not match now."""
        assert is_filesystem_target("~evil.com") is False

    def test_empty_string_is_not_filesystem(self):
        assert is_filesystem_target("") is False

    # ── Filesystem paths — must all return True ────────────────────────

    def test_unix_absolute_path(self):
        assert is_filesystem_target("/home/user/repo") is True

    def test_unix_root(self):
        assert is_filesystem_target("/") is True

    def test_unix_absolute_path_with_spaces(self):
        assert is_filesystem_target("/home/my user/project") is True

    def test_relative_path_dot_slash(self):
        assert is_filesystem_target("./src") is True

    def test_relative_path_dot(self):
        assert is_filesystem_target("./") is True

    def test_relative_path_parent(self):
        assert is_filesystem_target("../lib") is True

    def test_relative_path_deep(self):
        assert is_filesystem_target("../../etc/config") is True

    def test_home_relative_path(self):
        assert is_filesystem_target("~/projects") is True

    def test_home_relative_path_deep(self):
        assert is_filesystem_target("~/code/secuscan/backend") is True

    def test_windows_path_backslash(self):
        assert is_filesystem_target(r"C:\Users\repo") is True

    def test_windows_path_forward_slash(self):
        assert is_filesystem_target("C:/Users/repo") is True

    def test_windows_path_other_drive(self):
        assert is_filesystem_target(r"D:\work\project") is True

    def test_windows_lowercase_drive(self):
        assert is_filesystem_target(r"c:\users\repo") is True

def test_validate_command_network_egress_log_only(monkeypatch):
    """Test that validate_command_network_egress permits execution with a warning when failure mode is 'log_only'"""
    from backend.secuscan.validation import validate_command_network_egress
    from backend.secuscan.config import settings

    # Setup monkeypatch for configuration settings
    monkeypatch.setattr(settings, "enforce_network_policy", True)
    monkeypatch.setattr(settings, "network_policy_failure_mode", "log_only")

    # Command containing a blocked destination (e.g. 10.0.0.1)
    command = ["curl", "http://10.0.0.1/"]

    # Under 'log_only' mode, egress violation is logged as a warning but allowed
    ok, err = validate_command_network_egress(command, safe_mode=False, plugin_id="test", task_id="test-task")
    assert ok is True
    assert err == ""

    # Under 'block' mode, it should be denied
    monkeypatch.setattr(settings, "network_policy_failure_mode", "block")
    ok, err = validate_command_network_egress(command, safe_mode=False, plugin_id="test", task_id="test-task")
    assert ok is False
    assert "network policy" in err.lower()


def test_validate_command_network_egress_ignores_malformed_urls():
    """Malformed URLs without a valid hostname should be ignored."""

    from backend.secuscan.validation import validate_command_network_egress

    malformed_commands = [
        ["curl", "http://"],
        ["curl", "http:///abc"],
        ["curl", "https://"],
    ]

    for command in malformed_commands:
        ok, err = validate_command_network_egress(
            command,
            safe_mode=False,
            plugin_id="test",
            task_id="test-task",
        )

        assert ok is True
        assert err == ""


def test_validate_command_network_egress_resolver_failure(monkeypatch):
    from backend.secuscan.validation import validate_command_network_egress

    def fake_validate_target(*_args, **_kwargs):
        raise socket.gaierror("DNS resolution failed")

    monkeypatch.setattr(validation_module, "validate_target", fake_validate_target)

    with pytest.raises(socket.gaierror):
        validate_command_network_egress(
            ["curl", "https://example.com"],
            safe_mode=False,
            plugin_id="test",
            task_id="test-task",
        )


def test_validate_command_network_egress_network_policy_exception(monkeypatch):
    from backend.secuscan.validation import validate_command_network_egress
    from backend.secuscan.config import settings

    class FakePolicyEngine:
        def check_access(self, **_kwargs):
            raise RuntimeError("policy engine failure")

    monkeypatch.setattr(
        "backend.secuscan.network_policy.get_policy_engine",
        lambda: FakePolicyEngine(),
    )

    monkeypatch.setattr(
        validation_module,
        "validate_target",
        lambda *_args, **_kwargs: (True, ""),
    )

    old_enforce = settings.enforce_network_policy
    settings.enforce_network_policy = True

    try:
        with pytest.raises(RuntimeError, match="policy engine failure"):
            validate_command_network_egress(
                ["curl", "https://example.com"],
                safe_mode=False,
                plugin_id="test",
                task_id="test-task",
            )
    finally:
        settings.enforce_network_policy = old_enforce


def test_resolve_and_validate_target_rejects_raw_ip():
    from backend.secuscan.validation import resolve_and_validate_target
    ok, err = resolve_and_validate_target("http://10.0.0.1/webhook")
    assert ok is False
    assert "Raw IP" in err


def test_resolve_and_validate_target_rejects_bad_scheme():
    from backend.secuscan.validation import resolve_and_validate_target
    ok, err = resolve_and_validate_target("ftp://example.com/hook")
    assert ok is False
    assert "Scheme" in err


def test_resolve_and_validate_target_rejects_blocked_port(monkeypatch):
    from backend.secuscan.validation import resolve_and_validate_target
    from backend.secuscan.config import settings
    monkeypatch.setattr(settings, "notification_allowed_ports", [80, 443])
    ok, err = resolve_and_validate_target("http://example.com:22/webhook")
    assert ok is False
    assert "Port" in err


def test_resolve_and_validate_target_rejects_private_ip(monkeypatch):
    from backend.secuscan.validation import resolve_and_validate_target
    from backend.secuscan.config import settings
    monkeypatch.setattr(settings, "notification_blocked_ip_ranges", ["10.0.0.0/8"])

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("10.0.0.5", 80))]

    import socket
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    ok, err = resolve_and_validate_target("http://internal.example.com/hook")
    assert ok is False
    assert "blocked" in err


def test_resolve_and_validate_target_allows_public_ip(monkeypatch):
    from backend.secuscan.validation import resolve_and_validate_target

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 80))]

    import socket
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    ok, err = resolve_and_validate_target("http://example.com/hook")
    assert ok is True
    assert err == ""


class TestValidateWebhookTarget:
    """Tests for validate_webhook_target SSRF validation."""

    def test_rejects_no_hostname(self):
        from backend.secuscan.validation import validate_webhook_target
        ok, err = validate_webhook_target("not-a-url")
        assert ok is False
        assert "hostname" in err.lower()

    def test_rejects_private_ip_resolution(self, monkeypatch):
        from backend.secuscan.validation import validate_webhook_target

        def fake_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, None, None, None, ("10.0.0.5", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        ok, err = validate_webhook_target("http://internal.example.com/hook")
        assert ok is False
        assert "blocked" in err.lower()

    def test_rejects_metadata_ip_resolution(self, monkeypatch):
        from backend.secuscan.validation import validate_webhook_target

        def fake_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, None, None, None, ("169.254.169.254", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        ok, err = validate_webhook_target("http://metadata.example.com/hook")
        assert ok is False
        assert "blocked" in err.lower()

    def test_allows_public_ip_resolution(self, monkeypatch):
        from backend.secuscan.validation import validate_webhook_target

        def fake_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, None, None, None, ("93.184.216.34", 80))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        ok, err = validate_webhook_target("http://example.com/hook")
        assert ok is True
        assert err is None

    def test_rejects_resolution_failure(self, monkeypatch):
        from backend.secuscan.validation import validate_webhook_target

        def fake_getaddrinfo(*args, **kwargs):
            raise socket.gaierror("No address")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        ok, err = validate_webhook_target("http://nonexistent.example.com/hook")
        assert ok is False
        assert "could not be resolved" in err.lower()


# ---------------------------------------------------------------------------
# _parse_url_hostname tests
# ---------------------------------------------------------------------------


def test_parse_url_hostname_https_url():
    """Extracts hostname from a standard https URL."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname("https://example.com") == "example.com"


def test_parse_url_hostname_http_url():
    """Extracts hostname from a standard http URL."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname("http://example.com") == "example.com"


def test_parse_url_hostname_with_port():
    """Strips port from hostname when present."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname("https://example.com:8080") == "example.com"


def test_parse_url_hostname_with_path():
    """Strips path from hostname."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname("https://example.com/api/v1") == "example.com"


def test_parse_url_hostname_localhost():
    """Handles localhost URLs."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname("http://localhost:8000") == "localhost"


def test_parse_url_hostname_ipv4():
    """Handles IPv4 addresses."""
    from backend.secuscan.validation import _parse_url_hostname
    result = _parse_url_hostname("http://127.0.0.1:8000")
    assert result is not None


def test_parse_url_hostname_empty_string():
    """Returns None for empty string."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname("") is None


def test_parse_url_hostname_none():
    """Returns None for None input."""
    from backend.secuscan.validation import _parse_url_hostname
    assert _parse_url_hostname(None) is None
