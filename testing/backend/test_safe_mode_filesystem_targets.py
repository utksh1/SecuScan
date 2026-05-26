"""
testing/backend/test_safe_mode_filesystem_targets.py

Issue #90 — Document safe-mode behavior for filesystem targets
in code-category plugin workflows.

Route logic (upstream/main routes.py):
    should_validate_target = plugin.category != "code" and not is_filesystem_target(target_str)

Error format: detail is a plain string (not a dict).

Validation logic (validation.py):
    safe_mode=True  → ALLOWS private IPs, BLOCKS public IPs
    safe_mode=False → ALLOWS public IPs
    Always blocked  → broadcast, link-local, multicast
"""

import pytest

ENDPOINT = "/api/v1/task/start"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def post(client, payload: dict):
    return client.post(ENDPOINT, json=payload)


def code_payload(target: str) -> dict:
    return {
        "plugin_id": "code_analyzer",
        "inputs": {"target": target},
        "consent_granted": True,
    }


def network_payload(target: str, safe_mode: bool = True) -> dict:
    return {
        "plugin_id": "nmap",
        "inputs": {"target": target, "safe_mode": safe_mode},
        "consent_granted": True,
    }


def assert_not_blocked_by_host_validation(r):
    """Fails only if route returned 400 with an error_msg from validate_target."""
    if r.status_code == 400:
        detail = r.json().get("detail", "")
        # validate_target returns messages like "Public IPs/networks not allowed"
        # consent failure returns "Consent required..."
        # We only fail if it looks like a target validation rejection
        assert "not allowed" not in detail.lower() and "invalid" not in detail.lower(), (
            f"Path target incorrectly blocked by host validation: {r.text}"
        )


# ---------------------------------------------------------------------------
# 1. code_analyzer (category=code) — filesystem paths bypass host validation
# ---------------------------------------------------------------------------

class TestCodePluginFilesystemTargets:
    """
    code_analyzer has category='code'.
    Route: plugin.category != 'code' is False → validate_target() never called.
    """

    @pytest.mark.parametrize("path_target", [
        "./src",
        "./",
        "/tmp/project",
        "/home/user/myapp",
        "relative/path/to/code",
    ])
    def test_path_targets_bypass_host_validation(self, test_client, path_target):
        r = post(test_client, code_payload(path_target))
        assert_not_blocked_by_host_validation(r)

    def test_absolute_path_not_blocked(self, test_client):
        r = post(test_client, code_payload("/tmp/project"))
        assert_not_blocked_by_host_validation(r)

    def test_relative_dotslash_not_blocked(self, test_client):
        r = post(test_client, code_payload("./src"))
        assert_not_blocked_by_host_validation(r)


# ---------------------------------------------------------------------------
# 2. nmap (category=network) — filesystem path-like targets
# ---------------------------------------------------------------------------

class TestNonCodePluginFilesystemTargets:
    """
    nmap has category='network'.
    Route also checks is_filesystem_target() — if True, validation is skipped.
    """

    @pytest.mark.parametrize("path_target", [
        "./src",
        "/tmp/project",
    ])
    def test_path_target_does_not_cause_server_error(self, test_client, path_target):
        r = post(test_client, network_payload(path_target))
        assert r.status_code != 500, (
            f"Server crashed on path target '{path_target}': {r.text}"
        )

    @pytest.mark.parametrize("path_target", [
        "./src",
        "/tmp/project",
    ])
    def test_path_target_produces_expected_status(self, test_client, path_target):
        r = post(test_client, network_payload(path_target))
        assert r.status_code in (200, 201, 202, 400, 422), (
            f"Unexpected status {r.status_code} for '{path_target}': {r.text}"
        )


# ---------------------------------------------------------------------------
# 3. Network targets — safe-mode guardrails (validation.py behavior)
#
# safe_mode=True  → private IPs ALLOWED, public IPs BLOCKED
# safe_mode=False → public IPs ALLOWED
# Always blocked  → broadcast, link-local, multicast
# ---------------------------------------------------------------------------

class TestNetworkTargetSafeMode:

    @pytest.mark.parametrize("private_target", [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
    ])
    def test_private_targets_allowed_in_safe_mode(self, test_client, private_target):
        """safe_mode=True allows private/loopback ranges."""
        r = post(test_client, network_payload(private_target, safe_mode=True))
        assert r.status_code != 400, (
            f"Private target '{private_target}' incorrectly blocked: {r.text}"
        )

    @pytest.mark.parametrize("public_target", [
        "8.8.8.8",
        "1.1.1.1",
        "93.184.216.34",
    ])
    def test_public_targets_blocked_in_safe_mode(self, test_client, public_target):
        """safe_mode=True must block public IPs."""
        r = post(test_client, network_payload(public_target, safe_mode=True))
        assert r.status_code == 400, (
            f"Expected public target '{public_target}' blocked, got {r.status_code}: {r.text}"
        )
        detail = r.json().get("detail", "")
        assert isinstance(detail, str) and len(detail) > 0

    @pytest.mark.parametrize("public_target", [
        "8.8.8.8",
        "1.1.1.1",
    ])
    def test_public_targets_allowed_when_safe_mode_disabled(self, test_client, public_target):
        """safe_mode=False lifts the public IP restriction."""
        r = post(test_client, network_payload(public_target, safe_mode=False))
        assert r.status_code != 400, (
            f"Public target '{public_target}' incorrectly blocked with safe_mode=False: {r.text}"
        )

    @pytest.mark.parametrize("blocked_target", [
        "169.254.1.1",   # link-local
        "224.0.0.1",     # multicast
        "0.0.0.1",       # broadcast range
    ])
    def test_always_blocked_ranges_rejected(self, test_client, blocked_target):
        """Broadcast, link-local, multicast blocked in all modes."""
        for safe_mode in (True, False):
            r = post(test_client, network_payload(blocked_target, safe_mode=safe_mode))
            assert r.status_code == 400, (
                f"Expected '{blocked_target}' blocked (safe_mode={safe_mode}), "
                f"got {r.status_code}: {r.text}"
            )

    def test_raw_target_not_leaked_in_response(self, test_client):
        """Sentinel value must not appear in error response."""
        sentinel = "8.8.SENTINEL.8"
        r = post(test_client, network_payload(sentinel, safe_mode=True))
        if r.status_code == 400:
            assert sentinel not in r.text


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_path_traversal_does_not_cause_500(self, test_client):
        r = post(test_client, code_payload("../../etc/passwd"))
        assert r.status_code != 500

    def test_missing_target_does_not_crash(self, test_client):
        r = post(test_client, {
            "plugin_id": "code_analyzer",
            "inputs": {},
            "consent_granted": True,
        })
        assert r.status_code != 500

    def test_consent_checked_before_target_for_code_plugin(self, test_client):
        r = post(test_client, {
            "plugin_id": "code_analyzer",
            "inputs": {"target": "./src"},
            "consent_granted": False,
        })
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "consent" in detail.lower()

    def test_consent_checked_before_target_for_network_plugin(self, test_client):
        r = post(test_client, {
            "plugin_id": "nmap",
            "inputs": {"target": "192.168.1.1"},
            "consent_granted": False,
        })
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "consent" in detail.lower()