import pytest
from fastapi.testclient import TestClient
from backend.secuscan.main import app
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.plugins import init_plugins
from backend.secuscan import auth as auth_module
import asyncio

@pytest.fixture()
def client_with_key(setup_test_environment):
    asyncio.run(init_db(settings.database_path))
    asyncio.run(init_plugins(settings.plugins_dir))
    api_key = auth_module.init_api_key(settings.data_dir)
    with TestClient(app) as c:
        yield c, api_key

def test_preview_command_endpoint(client_with_key):
    client, api_key = client_with_key
    headers = {"X-API-Key": api_key}

    # Try with a valid plugin (http_inspector) and vault reference
    response = client.post(
        "/api/v1/plugin/http_inspector/preview",
        json={"inputs": {"url": "http://127.0.0.1/?token=vault:my-secret-agent"}},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "command" in data
    cmd_str = " ".join(data["command"])
    assert "vault:[REDACTED]" in cmd_str
    assert "http://127.0.0.1/?token=vault:[REDACTED]" in cmd_str

def test_preview_command_missing_required(client_with_key):
    client, api_key = client_with_key
    headers = {"X-API-Key": api_key}

    # Missing 'url' field which is required for http_inspector
    response = client.post(
        "/api/v1/plugin/http_inspector/preview",
        json={"inputs": {"timeout": 15}},
        headers=headers
    )
    assert response.status_code == 400
    assert "Missing required fields" in response.json()["detail"]
