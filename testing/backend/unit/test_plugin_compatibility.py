import asyncio
import pytest
from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager, LEGACY_PLUGIN_ID_ALIASES

def test_legacy_plugin_id_aliases_resolve(setup_test_environment):
    """Test that all defined legacy plugin ID aliases successfully resolve to valid, loaded plugins."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    for legacy_id, canonical_id in LEGACY_PLUGIN_ID_ALIASES.items():
        # Get plugin metadata by legacy ID
        plugin_by_legacy = manager.get_plugin(legacy_id)
        assert plugin_by_legacy is not None, f"Legacy ID {legacy_id} returned None"
        assert plugin_by_legacy.id == canonical_id, f"Legacy ID {legacy_id} resolved to {plugin_by_legacy.id} instead of {canonical_id}"

        # Get plugin metadata by canonical ID
        plugin_by_canonical = manager.get_plugin(canonical_id)
        assert plugin_by_canonical is not None, f"Canonical ID {canonical_id} returned None"
        assert plugin_by_legacy == plugin_by_canonical

        # Get schema by legacy and canonical ID
        schema_by_legacy = manager.get_plugin_schema(legacy_id)
        schema_by_canonical = manager.get_plugin_schema(canonical_id)
        assert schema_by_legacy == schema_by_canonical
        assert schema_by_legacy["id"] == canonical_id

def test_build_command_with_legacy_id(setup_test_environment):
    """Test that building commands with legacy IDs works and generates the exact same command as the canonical ID."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    # Test subdomain-finder
    cmd_legacy = manager.build_command("subdomain-finder", {"target": "example.com"})
    cmd_canonical = manager.build_command("subdomain_finder", {"target": "example.com"})
    assert cmd_legacy == cmd_canonical
    assert cmd_legacy is not None
    assert "subfinder" in cmd_legacy
    assert "example.com" in cmd_legacy

    # Test google-dorking
    cmd_legacy = manager.build_command("google-dorking", {"target": "example.com"})
    cmd_canonical = manager.build_command("google_dorking", {"target": "example.com"})
    assert cmd_legacy == cmd_canonical
    assert cmd_legacy is not None
    assert "google" in cmd_legacy or "python3" in cmd_legacy

def test_task_start_via_api_resolves_legacy_id(test_client):
    """Test that submitting a task with a legacy plugin ID via the API succeeds and stores the task with the canonical ID."""
    # Submit task with legacy ID "subdomain-finder"
    response = test_client.post(
        "/api/v1/task/start",
        json={
            "plugin_id": "subdomain-finder",
            "consent_granted": True,
            "inputs": {
                "target": "127.0.0.1"
            }
        }
    )
    assert response.status_code == 200, f"Task start failed: {response.text}"
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]

    # Verify task details via the status API
    status_response = test_client.get(f"/api/v1/task/{task_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    # The plugin_id stored on the task must be the canonical/standardized one
    assert status_data["plugin_id"] == "subdomain_finder"
