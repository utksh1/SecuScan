import pytest
from unittest.mock import patch, MagicMock
from backend.secuscan.config import settings
from backend.secuscan.network_policy import get_policy_engine, PolicyAction


class TestAdminNetworkPolicySecurity:
    """Verify security of the `/admin` surface."""

    def test_unconfigured_api_key_blocks_with_500(self, test_client, monkeypatch):
        """When admin_api_key is unconfigured, endpoints should return HTTP 500."""
        monkeypatch.setattr(settings, "admin_api_key", None)

        # GET policy config
        res = test_client.get("/api/v1/admin/network-policy")
        assert res.status_code == 500
        assert "not configured" in res.json()["detail"].lower()

        # POST allow rule
        res = test_client.post(
            "/api/v1/admin/network-policy/allow", json={"cidr": "1.1.1.1/32"}
        )
        assert res.status_code == 500

        # POST deny rule
        res = test_client.post(
            "/api/v1/admin/network-policy/deny", json={"cidr": "2.2.2.2/32"}
        )
        assert res.status_code == 500

        # GET audit log
        res = test_client.get("/api/v1/admin/network-audit-log")
        assert res.status_code == 500

        # GET audit log export
        res = test_client.get("/api/v1/admin/network-audit-log/export")
        assert res.status_code == 500

    def test_weak_api_key_blocks_with_500(self, test_client, monkeypatch):
        """When admin_api_key is too short/weak (< 16 chars), endpoints should return HTTP 500."""
        monkeypatch.setattr(settings, "admin_api_key", "too-short-key")  # 13 chars

        res = test_client.get("/api/v1/admin/network-policy")
        assert res.status_code == 500
        assert "too weak" in res.json()["detail"].lower()

    def test_missing_api_key_returns_401(self, test_client, monkeypatch):
        """When key is configured but missing in request, return HTTP 401."""
        monkeypatch.setattr(settings, "admin_api_key", "valid-admin-key-long")

        res = test_client.get("/api/v1/admin/network-policy")
        assert res.status_code == 401
        assert "missing" in res.json()["detail"].lower()

    def test_invalid_api_key_returns_401(self, test_client, monkeypatch):
        """When key is configured but invalid key is sent, return HTTP 401."""
        monkeypatch.setattr(settings, "admin_api_key", "valid-admin-key-long")

        # Invalid key in X-API-Key header
        res = test_client.get(
            "/api/v1/admin/network-policy", headers={"X-API-Key": "wrong-key"}
        )
        assert res.status_code == 401

        # Invalid key in Authorization Bearer header
        res = test_client.get(
            "/api/v1/admin/network-policy",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert res.status_code == 401

        # Invalid key in raw Authorization header
        res = test_client.get(
            "/api/v1/admin/network-policy", headers={"Authorization": "wrong-key"}
        )
        assert res.status_code == 401

    def test_valid_api_key_in_header_allows_access(self, test_client, monkeypatch):
        """Valid key in X-API-Key header should allow access."""
        monkeypatch.setattr(settings, "admin_api_key", "valid-admin-key-long")

        res = test_client.get(
            "/api/v1/admin/network-policy",
            headers={"X-API-Key": "valid-admin-key-long"},
        )
        assert res.status_code == 200
        assert "allowlist" in res.json()

    def test_valid_api_key_in_bearer_token_allows_access(
        self, test_client, monkeypatch
    ):
        """Valid key in Authorization Bearer header should allow access."""
        monkeypatch.setattr(settings, "admin_api_key", "valid-admin-key-long")

        res = test_client.get(
            "/api/v1/admin/network-policy",
            headers={"Authorization": "Bearer valid-admin-key-long"},
        )
        assert res.status_code == 200

    def test_valid_api_key_in_auth_header_allows_access(self, test_client, monkeypatch):
        """Valid key in raw Authorization header should allow access."""
        monkeypatch.setattr(settings, "admin_api_key", "valid-admin-key-long")

        res = test_client.get(
            "/api/v1/admin/network-policy",
            headers={"Authorization": "valid-admin-key-long"},
        )
        assert res.status_code == 200


class TestAdminNetworkPolicyOperations:
    """Verify CRUD endpoints for allowlist/denylist rules."""

    @pytest.fixture(autouse=True)
    def configure_auth(self, monkeypatch):
        monkeypatch.setattr(settings, "admin_api_key", "secret-test-key-long")

    def test_add_and_retrieve_rules(self, test_client):
        """Verify we can add rules and get the current configuration."""
        headers = {"X-API-Key": "secret-test-key-long"}

        # Empty configuration check
        engine = get_policy_engine()
        engine.allowlist.clear()
        engine.denylist.clear()

        # Add allow rule
        res = test_client.post(
            "/api/v1/admin/network-policy/allow",
            json={"cidr": "8.8.8.0/24", "reason": "Google DNS Subnet"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # Add deny rule
        res = test_client.post(
            "/api/v1/admin/network-policy/deny",
            json={"cidr": "10.0.0.0/8", "reason": "Internal"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # Get policy config and verify rules
        res = test_client.get("/api/v1/admin/network-policy", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["allowlist"]) == 1
        assert data["allowlist"][0]["cidr"] == "8.8.8.0/24"
        assert len(data["denylist"]) == 1
        assert data["denylist"][0]["cidr"] == "10.0.0.0/8"

    def test_add_invalid_cidr_returns_400(self, test_client):
        """Verify adding an invalid CIDR network returns HTTP 400."""
        headers = {"X-API-Key": "secret-test-key-long"}

        res = test_client.post(
            "/api/v1/admin/network-policy/allow",
            json={"cidr": "invalid-cidr"},
            headers=headers,
        )
        assert res.status_code == 400
        assert "invalid" in res.json()["detail"].lower()


class TestAdminNetworkAuditLog:
    """Verify auditing and log querying/exporting."""

    @pytest.fixture(autouse=True)
    def configure_auth(self, monkeypatch):
        monkeypatch.setattr(settings, "admin_api_key", "secret-test-key-long")

    def test_query_and_export_audit_logs(self, test_client):
        """Verify querying audit log entries and exporting them."""
        headers = {"X-API-Key": "secret-test-key-long"}

        engine = get_policy_engine()
        engine.allowlist.clear()
        engine.denylist.clear()
        engine.audit_entries.clear()

        # Generate some audit log entries
        engine.check_access("1.1.1.1", plugin_id="scanner_a", task_id="task_123")
        engine.check_access("8.8.8.8", plugin_id="scanner_b", task_id="task_456")

        # Query audit logs
        res = test_client.get("/api/v1/admin/network-audit-log", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["entries"]) == 2

        # Query with plugin filtering
        res = test_client.get(
            "/api/v1/admin/network-audit-log?plugin_id=scanner_a", headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["entries"][0]["plugin_id"] == "scanner_a"

        # Query with action filtering
        res = test_client.get(
            "/api/v1/admin/network-audit-log?action=deny", headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert (
            len(data["entries"]) == 2
        )  # Denied by default because allowlist was empty

        # Export audit log as JSON
        res = test_client.get(
            "/api/v1/admin/network-audit-log/export?format=json", headers=headers
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/json"
        exported_data = res.json()
        assert len(exported_data) == 2

        # Export audit log as CSV
        res = test_client.get(
            "/api/v1/admin/network-audit-log/export?format=csv", headers=headers
        )
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        csv_text = res.text
        assert "timestamp,plugin_id,task_id" in csv_text
        assert "scanner_a" in csv_text
        assert "scanner_b" in csv_text
