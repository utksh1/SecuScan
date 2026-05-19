"""
testing/backend/test_safe_mode_filesystem_targets.py

Issue #90 — Document safe-mode behavior for filesystem targets
in code-category plugin workflows.

Route logic (routes.py):
    should_validate_target = plugin.category != "code" and not is_filesystem_target(target_str)

Validation logic (validation.py):
    safe_mode=True  → ALLOWS private IPs (10.x, 192.168.x, 127.x), BLOCKS public IPs
    safe_mode=False → ALLOWS public IPs too
    Blocked always  → broadcast (0.0.0.0/8), link-local, multicast
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
    """Fails only if the route rejected with invalid_target — a path bypass failure."""
    if r.status_code in (400, 422):
        detail = r.json().get("detail", {})
        assert detail.get("code") != "invalid_target", (
            f"Path target incorrectly blocked by host validation: {r.text}"
        )


# ---------------------------------------------------------------------------
# 1. code_analyzer (category=code) — filesystem paths bypass host validation
# ---------------------------------------------------------------------------

class TestCodePluginFilesystemTargets:
    """
    code_analyzer has category='code'.
    Route: plugin.category != 'code' is False → validate_target() never called.
    Path targets must not produce an invalid_target error.
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
    These tests document current behavior and catch regressions.
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
        """Documents: network plugin + filesystem path → 200/202 or 400/422, never 500."""
        r = post(test_client, network_payload(path_target))
        assert r.status_code in (200, 201, 202, 400, 422), (
            f"Unexpected status {r.status_code} for '{path_target}': {r.text}"
        )


# ---------------------------------------------------------------------------
# 3. Network targets — safe-mode guardrails (actual validation.py behavior)
#
# safe_mode=True  → private IPs ALLOWED, public IPs BLOCKED
# safe_mode=False → public IPs ALLOWED
# Always blocked  → broadcast, link-local, multicast (regardless of safe_mode)
# ---------------------------------------------------------------------------

class TestNetworkTargetSafeMode:
    """
    validate_target() in validation.py:
      - safe_mode=True  blocks public IPs (not in 10/8, 172.16/12, 192.168/16, 127/8)
      - safe_mode=True  allows private IPs
      - safe_mode=False allows public IPs
    """

    # --- private IPs are ALLOWED in safe_mode ---

    @pytest.mark.parametrize("private_target", [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
    ])
    def test_private_targets_allowed_in_safe_mode(self, test_client, private_target):
        """safe_mode=True allows private/loopback ranges per validation.py ALLOWED_PRIVATE."""
        r = post(test_client, network_payload(private_target, safe_mode=True))
        assert r.status_code != 400 or r.json().get("detail", {}).get("code") != "invalid_target", (
            f"Private target '{private_target}' incorrectly blocked in safe_mode: {r.text}"
        )

    # --- public IPs are BLOCKED in safe_mode ---

    @pytest.mark.parametrize("public_target", [
        "8.8.8.8",
        "1.1.1.1",
        "93.184.216.34",  # example.com
    ])
    def test_public_targets_blocked_in_safe_mode(self, test_client, public_target):
        """safe_mode=True must block public IPs — not in any ALLOWED_PRIVATE range."""
        r = post(test_client, network_payload(public_target, safe_mode=True))
        assert r.status_code == 400, (
            f"Expected public target '{public_target}' to be blocked in safe_mode, "
            f"got {r.status_code}: {r.text}"
        )
        detail = r.json().get("detail", {})
        assert detail.get("code") == "invalid_target"
        assert detail.get("hints", {}).get("safe_mode") is True

    # --- public IPs are ALLOWED when safe_mode=False ---

    @pytest.mark.parametrize("public_target", [
        "8.8.8.8",
        "1.1.1.1",
    ])
    def test_public_targets_allowed_when_safe_mode_disabled(self, test_client, public_target):
        """safe_mode=False lifts the public IP restriction."""
        r = post(test_client, network_payload(public_target, safe_mode=False))
        assert r.status_code not in (400, 422) or (
            r.json().get("detail", {}).get("code") != "invalid_target"
        ), f"Public target '{public_target}' incorrectly blocked with safe_mode=False: {r.text}"

    # --- always-blocked ranges ---

    @pytest.mark.parametrize("blocked_target", [
        "169.254.1.1",   # link-local
        "224.0.0.1",     # multicast
        "0.0.0.1",       # broadcast range
    ])
    def test_always_blocked_ranges_rejected_regardless_of_safe_mode(self, test_client, blocked_target):
        """Broadcast, link-local, multicast blocked in all modes per BLOCKED_NETWORKS."""
        for safe_mode in (True, False):
            r = post(test_client, network_payload(blocked_target, safe_mode=safe_mode))
            assert r.status_code == 400, (
                f"Expected '{blocked_target}' to be blocked (safe_mode={safe_mode}), "
                f"got {r.status_code}: {r.text}"
            )

    def test_safe_mode_hint_present_on_block(self, test_client):
        r = post(test_client, network_payload("8.8.8.8", safe_mode=True))
        assert r.status_code == 400
        hints = r.json()["detail"].get("hints", {})
        assert "safe_mode" in hints

    def test_raw_target_not_leaked_in_response(self, test_client):
        sentinel = "8.8.SENTINEL.8"
        r = post(test_client, network_payload(sentinel, safe_mode=True))
        if r.status_code == 400:
            assert sentinel not in r.text


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_path_traversal_does_not_cause_500(self, test_client):
        """../../etc/passwd must never produce a server crash."""
        r = post(test_client, code_payload("../../etc/passwd"))
        assert r.status_code != 500

    def test_missing_target_does_not_crash(self, test_client):
        """No target key — route skips validation block. Must not 500."""
        r = post(test_client, {
            "plugin_id": "code_analyzer",
            "inputs": {},
            "consent_granted": True,
        })
        assert r.status_code != 500

    def test_consent_checked_before_target_for_code_plugin(self, test_client):
        """Consent gate runs before category/target logic."""
        r = post(test_client, {
            "plugin_id": "code_analyzer",
            "inputs": {"target": "./src"},
            "consent_granted": False,
        })
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "consent_required"

    def test_consent_checked_before_target_for_network_plugin(self, test_client):
        r = post(test_client, {
            "plugin_id": "nmap",
            "inputs": {"target": "192.168.1.1"},
            "consent_granted": False,
        })
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "consent_required"