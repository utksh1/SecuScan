import asyncio
from pathlib import Path

import pytest

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


def test_nikto_plugin_supports_expanded_cli_parameters(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    schema = manager.get_plugin_schema("nikto")
    assert schema is not None
    field_ids = {field["id"] for field in schema["fields"]}
    assert {"port", "scan_until", "display_options", "proxy", "config_file", "no_cache", "dbcheck", "update_plugins"} <= field_ids

    command = manager.build_command(
        "nikto",
        {
            "target": "example.com",
            "port": "80,443",
            "force_ssl": True,
            "display_options": "EPV",
            "tuning": "123b",
            "request_timeout": 20,
            "max_scan_time": 900,
            "dbcheck": True,
            "no_cache": True,
        },
    )

    assert command is not None
    assert command[:5] == ["nikto", "-nocheck", "-dbcheck", "-h", "example.com"]
    assert "-port" in command and "80,443" in command
    assert "-ssl" in command
    assert "-Display" in command and "EPV" in command
    assert "-nocache" in command


# ---------------------------------------------------------------------------
# _resolve_wordlist_path unit tests — isolated path safety & resolution
# ---------------------------------------------------------------------------


def test_resolve_wordlist_path_rejects_absolute_unix_path(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    manager = PluginManager(settings.plugins_dir)

    with pytest.raises(ValueError, match="absolute"):
        manager._resolve_wordlist_path("/etc/passwd")


def test_resolve_wordlist_path_rejects_absolute_windows_path(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    manager = PluginManager(settings.plugins_dir)

    with pytest.raises(ValueError, match="absolute"):
        manager._resolve_wordlist_path("C:\\Windows\\system32")


def test_resolve_wordlist_path_rejects_traversal(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    manager = PluginManager(settings.plugins_dir)

    with pytest.raises(ValueError, match="traversal"):
        manager._resolve_wordlist_path("../../../etc/passwd")

    with pytest.raises(ValueError, match="traversal"):
        manager._resolve_wordlist_path("..\\..\\..\\etc\\passwd")


def test_resolve_wordlist_path_blocks_escaped_existing_path(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    manager = PluginManager(settings.plugins_dir)

    with pytest.raises(ValueError, match="traversal"):
        manager._resolve_wordlist_path("..\\outside.txt")


def test_resolve_wordlist_path_alias_small_works(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    small = wordlists_dir / "small.txt"
    small.write_text("a\nb\nc")

    manager = PluginManager(settings.plugins_dir)
    result = manager._resolve_wordlist_path("small")
    assert result == str(small)


def test_resolve_wordlist_path_alias_medium_works(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    medium = wordlists_dir / "medium.txt"
    medium.write_text("a\nb\nc")

    manager = PluginManager(settings.plugins_dir)
    result = manager._resolve_wordlist_path("medium")
    assert result == str(medium)


def test_resolve_wordlist_path_alias_large_works(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    large = wordlists_dir / "large.txt"
    large.write_text("a\nb\nc")

    manager = PluginManager(settings.plugins_dir)
    result = manager._resolve_wordlist_path("large")
    assert result == str(large)


def test_resolve_wordlist_path_fallback_dirb_common(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    common = wordlists_dir / "common.txt"
    common.write_text("common")

    manager = PluginManager(settings.plugins_dir)
    result = manager._resolve_wordlist_path("dirb/common.txt")
    assert result == str(common)


def test_resolve_wordlist_path_fallback_seclists_common(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    common = wordlists_dir / "common.txt"
    common.write_text("common")

    manager = PluginManager(settings.plugins_dir)
    result = manager._resolve_wordlist_path("discovery/web-content/common.txt")
    assert result == str(common)


def test_resolve_wordlist_path_fallback_seclists_dns(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    subdomains = wordlists_dir / "subdomains-top1million-110000.txt"
    subdomains.write_text("www\napi")

    manager = PluginManager(settings.plugins_dir)
    result = manager._resolve_wordlist_path("discovery/dns/subdomains-top1million-110000.txt")
    assert result == str(subdomains)


def test_resolve_wordlist_path_returns_value_unchanged_when_not_found(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    manager = PluginManager(settings.plugins_dir)

    result = manager._resolve_wordlist_path("custom_wordlist.txt")
    assert result == "custom_wordlist.txt"


def test_resolve_wordlist_path_blocks_escaped_nonexistent_path(setup_test_environment, monkeypatch, tmp_path):
    wordlists_dir = tmp_path / "wordlists"
    wordlists_dir.mkdir()
    monkeypatch.setattr("backend.secuscan.config.settings.wordlists_dir", str(wordlists_dir))
    manager = PluginManager(settings.plugins_dir)

    with pytest.raises(ValueError, match="traversal"):
        manager._resolve_wordlist_path("../plugins/malicious_script")


# ---------------------------------------------------------------------------
# Existing wordlist integration-style tests (use real files on disk)
# ---------------------------------------------------------------------------


def test_plugin_manager_resolves_repo_local_wordlist_aliases(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    medium_wordlist = Path(settings.wordlists_dir) / "medium.txt"
    medium_wordlist.write_text("admin\nlogin\n", encoding="utf-8")

    command = manager.build_command(
        "dir_discovery",
        {"base_url": "https://example.com"},
    )

    assert command is not None
    assert str(medium_wordlist) in command


def test_plugin_manager_rejects_linux_wordlist_absolute_default(setup_test_environment):
    """Linux absolute paths in plugin defaults are now rejected for safety."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    with pytest.raises(ValueError, match="absolute"):
        manager.build_command(
            "virtual-host-finder",
            {"target": "example.com"},
        )
