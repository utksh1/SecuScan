import asyncio
import pytest
from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager


def test_plugins_list_defaults_to_enabled(setup_test_environment):
    """By default, all loaded plugins should have enabled=True."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugins = manager.list_plugins()
    assert len(plugins) > 0
    for plugin in plugins:
        assert plugin["enabled"] is True


def test_plugins_list_reflects_disabled_settings(setup_test_environment, monkeypatch):
    """Plugins specified in settings.disabled_plugins should have enabled=False."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    # Verify we have the target plugin loaded first
    target_id = "http_inspector"
    original_plugin = manager.get_plugin(target_id)
    assert original_plugin is not None

    # Disable the target plugin via settings
    monkeypatch.setattr(settings, "disabled_plugins", [target_id])

    plugins = manager.list_plugins()
    by_id = {p["id"]: p for p in plugins}

    # Verify the target plugin is reported as disabled
    assert by_id[target_id]["enabled"] is False

    # Verify other plugins remain enabled
    for p_id, plugin in by_id.items():
        if p_id != target_id:
            assert plugin["enabled"] is True


def test_disabled_plugins_remain_executable_for_compatibility(setup_test_environment, monkeypatch):
    """Disabled plugins should still build commands normally to preserve backward compatibility."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    target_id = "http_inspector"
    monkeypatch.setattr(settings, "disabled_plugins", [target_id])

    # Command generation should succeed even if disabled
    command = manager.build_command(
        target_id,
        {
            "url": "http://127.0.0.1",
            "follow_redirects": True,
        },
    )

    assert command is not None
    assert "curl" in command
