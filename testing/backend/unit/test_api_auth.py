"""
Unit tests for API key authentication (issue #199).
"""

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.secuscan import auth as auth_module
from backend.secuscan.main import app
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.plugins import init_plugins


@pytest.fixture()
def client_with_key(setup_test_environment):
    """TestClient with a valid API key pre-seeded."""
    api_key = auth_module.init_api_key(settings.data_dir)
    with TestClient(app) as c:
        yield c, api_key


class TestApiKeyInit:
    def test_key_file_created(self, tmp_path):
        key = auth_module.init_api_key(str(tmp_path))
        assert (tmp_path / ".api_key").exists()
        assert len(key) == 64  # 32 bytes → 64 hex chars

    def test_existing_key_reloaded(self, tmp_path):
        k1 = auth_module.init_api_key(str(tmp_path))
        k2 = auth_module.init_api_key(str(tmp_path))
        assert k1 == k2

    def test_key_file_permissions(self, tmp_path):
        import sys
        auth_module.init_api_key(str(tmp_path))
        mode = (tmp_path / ".api_key").stat().st_mode & 0o777
        if sys.platform == "win32":
            assert mode == 0o666
        else:
            assert mode == 0o600

    def test_secuscan_api_key_file_env_var(self, tmp_path, monkeypatch):
        custom_path = tmp_path / "secrets" / "my_api_key"
        monkeypatch.setenv("SECUSCAN_API_KEY_FILE", str(custom_path))
        key = auth_module.init_api_key(str(tmp_path))
        assert custom_path.exists()
        assert custom_path.read_text().strip() == key

    def test_secuscan_api_key_file_loads_existing(self, tmp_path, monkeypatch):
        custom_path = tmp_path / "my_key"
        custom_path.write_text("preset-key-abc123")
        monkeypatch.setenv("SECUSCAN_API_KEY_FILE", str(custom_path))
        key = auth_module.init_api_key(str(tmp_path))
        assert key == "preset-key-abc123"


class TestAuthDependency:
    def test_no_credentials_returns_401(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/api/v1/plugins", headers={})
        assert resp.status_code == 401

    def test_wrong_key_returns_401(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/api/v1/plugins", headers={"X-Api-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_valid_x_api_key_header(self, client_with_key):
        client, api_key = client_with_key
        resp = client.get("/api/v1/plugins", headers={"X-Api-Key": api_key})
        assert resp.status_code == 200

    def test_valid_bearer_token(self, client_with_key):
        client, api_key = client_with_key
        resp = client.get("/api/v1/plugins", headers={"Authorization": f"Bearer {api_key}"})
        assert resp.status_code == 200

    def test_bearer_wrong_key_returns_401(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/api/v1/plugins", headers={"Authorization": "Bearer bad"})
        assert resp.status_code == 401

    def test_health_endpoint_not_protected(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/api/v1/health", headers={})
        # health check is defined on `app` directly, not inside the authenticated router
        assert resp.status_code == 200

    def test_root_endpoint_not_protected(self, client_with_key):
        client, _ = client_with_key
        resp = client.get("/", headers={})
        assert resp.status_code == 200


class TestIsFilesystemTarget:
    """Regression tests for is_filesystem_target — CIDR must not be treated as a path."""

    from backend.secuscan.routes import is_filesystem_target

    @pytest.mark.parametrize("target,expected", [
        ("/etc/passwd", True),
        ("./relative/path", True),
        ("../parent/path", True),
        ("~/home/dir", True),
        ("C:\\Windows\\System32", True),
        ("C:/Windows/System32", True),
        # These are NOT filesystem targets
        ("8.8.8.8/32", False),
        ("192.168.1.0/24", False),
        ("example.com", False),
        ("http://example.com/path", False),
        ("https://example.com/path", False),
        ("10.0.0.1", False),
    ])
    def test_filesystem_target_detection(self, target, expected):
        from backend.secuscan.routes import is_filesystem_target
        assert is_filesystem_target(target) == expected
