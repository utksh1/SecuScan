import asyncio

from config import settings
from plugins import PluginManager


def test_plugin_manager_loading(setup_test_environment):
    """Test that the PluginManager correctly loads plugins from the filesystem."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugins = manager.list_plugins()
    assert len(plugins) > 0

    http_plugin = manager.get_plugin("http_inspector")
    assert http_plugin is not None
    assert http_plugin.name == "HTTP Inspector"
    assert http_plugin.category == "web"

    schema = manager.get_plugin_schema("http_inspector")
    assert "fields" in schema
    assert "id" in schema


def test_plugin_manager_build_command(setup_test_environment):
    """Test building commands with inputs and default substitutions."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "http_inspector",
        {
            "url": "http://127.0.0.1",
            "follow_redirects": True,
        },
    )

    assert "curl" in command
    assert "-i" in command
    assert "-L" in command
    assert "10" in command
    assert "http://127.0.0.1" in command
