import asyncio

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager


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


def test_plugin_list_exposes_runtime_capabilities(setup_test_environment, monkeypatch):
    """Plugin list payload includes consent and availability details."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    def fake_which(binary: str):
        if binary in {"subfinder", "dnsrecon"}:
            return None
        return f"/usr/bin/{binary}"

    monkeypatch.setattr("backend.secuscan.plugins.shutil.which", fake_which)

    plugins = manager.list_plugins()
    by_id = {plugin["id"]: plugin for plugin in plugins}

    assert "subdomain_discovery" in by_id
    assert by_id["subdomain_discovery"]["availability"]["runnable"] is False
    assert "subfinder" in by_id["subdomain_discovery"]["availability"]["missing_binaries"]

    assert "scapy_recon" in by_id
    assert by_id["scapy_recon"]["requires_consent"] is True
    assert by_id["scapy_recon"]["consent_message"]
