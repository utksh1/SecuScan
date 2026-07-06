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


def test_plugin_interpolation_sanitizes_user_controlled_values():
    manager = PluginManager("plugins")

    assert manager._interpolate("{templates}", {"templates": "--debug;$(whoami)"}) == "debugwhoami"
    assert (
        manager._interpolate("--user-agent={user_agent}", {"user_agent": "--verbose|curl"})
        == "--user-agent=verbosecurl"
    )


def test_plugin_interpolation_single_pass_prevents_sequential_injection():
    """Single-pass substitution must not resolve placeholders injected by user values.

    This test verifies the fix for CVE-class sequential template injection:
    if field A's value contains ``{field_B}``, the single-pass approach prevents
    it from being resolved when field B is substituted.
    """
    manager = PluginManager("plugins")

    token = "use {module}; set RHOSTS {target}; set PAYLOAD {payload}; run"
    inputs = {
        "module": "exploit/multi/handler",
        "target": "10.0.0.1",
        "payload": "generic/shell_reverse_tcp",
    }
    result = manager._interpolate(token, inputs)
    assert "; set TARGET " not in result

    # A value containing brace-delimited text that matches another placeholder
    # must NOT leak into the second substitution.
    inputs2 = {
        "module": "exploit/{target}",
        "target": "EVIL_INJECTED",
        "payload": "generic/shell_reverse_tcp",
    }
    result2 = manager._interpolate(token, inputs2)
    assert result2 is not None
    # EVIL_INJECTED appears only once (from the legitimate {target})
    assert result2.count("EVIL_INJECTED") == 1
    # The injected {target} in the module value is preserved literally
    assert "{target}" in result2


def test_plugin_interpolation_preserves_braces_in_values():
    """Curly braces in user values must be preserved (not stripped by sanitize_input)."""
    manager = PluginManager("plugins")

    result = manager._interpolate("--json={payload}", {"payload": "{key: value}"})
    assert result is not None
    assert "{" in result and "}" in result
    assert result == "--json={key: value}"


def test_plugin_interpolation_preserves_legitimate_argv_values():
    manager = PluginManager("plugins")

    assert (
        manager._interpolate(
            "--url={target}",
            {"target": "https://api-v1.example.com:8443/health-check"},
        )
        == "--url=https://api-v1.example.com:8443/health-check"
    )
    assert (
        manager._interpolate(
            "--user-agent={user_agent}",
            {"user_agent": "SecuScan-CLI/1.0 api-health-check"},
        )
        == "--user-agent=SecuScan-CLI/1.0 api-health-check"
    )


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
            "timeout": 20,
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

    # dir_discovery now defaults to the bundled "small" list, so request the
    # installed "medium" alias explicitly to exercise repo-local resolution.
    command = manager.build_command(
        "dir_discovery",
        {"base_url": "https://example.com", "wordlist": "medium"},
    )

    assert command is not None
    assert (str(medium_wordlist) in command) or (medium_wordlist.as_posix() in command)


def test_plugin_manager_rejects_linux_wordlist_absolute_default(setup_test_environment):
    """Linux absolute paths in plugin defaults are now rejected for safety."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    with pytest.raises(ValueError, match="absolute"):
        manager.build_command(
            "virtual-host-finder",
            {"target": "example.com"},
        )

def test_plugin_validation_presets(setup_test_environment):
    """Test validation_type presets on field inputs."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("http_inspector")
    assert plugin is not None

    # Let's mock a field's validation properties
    target_field = plugin.fields[0]
    orig_validation = target_field.validation

    try:
        # Test 1: URL validation_type preset
        target_field.validation = {"validation_type": "url", "message": "Must be valid URL"}
        # Valid URL
        manager._validate_inputs_against_schema(plugin, {target_field.id: "https://example.com/api"})
        # Invalid URL
        with pytest.raises(ValueError, match="Must be valid URL"):
            manager._validate_inputs_against_schema(plugin, {target_field.id: "invalid-url"})

        # Test 2: Hostname preset
        target_field.validation = {"validation_type": "hostname"}
        # Valid hostname
        manager._validate_inputs_against_schema(plugin, {target_field.id: "sub.example.com"})
        # Invalid hostname
        with pytest.raises(ValueError, match="Must be a valid hostname"):
            manager._validate_inputs_against_schema(plugin, {target_field.id: "https://example.com"})

        # Test 3: Domain preset
        target_field.validation = {"validation_type": "domain"}
        # Valid domain
        manager._validate_inputs_against_schema(plugin, {target_field.id: "example.com"})
        # Invalid domain
        with pytest.raises(ValueError, match="Must be a valid domain name"):
            manager._validate_inputs_against_schema(plugin, {target_field.id: "https://example.com"})

        # Test 4: IPv4 preset
        target_field.validation = {"validation_type": "ipv4"}
        # Valid IP
        manager._validate_inputs_against_schema(plugin, {target_field.id: "192.168.1.1"})
        # Invalid IP
        with pytest.raises(ValueError, match="Must be a valid IPv4 address"):
            manager._validate_inputs_against_schema(plugin, {target_field.id: "999.999.999.999"})

        # Test 5: Port preset
        target_field.validation = {"validation_type": "port"}
        # Valid port
        manager._validate_inputs_against_schema(plugin, {target_field.id: "8080"})
        # Invalid port
        with pytest.raises(ValueError, match="Must be a valid port number"):
            manager._validate_inputs_against_schema(plugin, {target_field.id: "70000"})

        # Test 6: CIDR preset
        target_field.validation = {"validation_type": "cidr"}
        # Valid CIDR
        manager._validate_inputs_against_schema(plugin, {target_field.id: "192.168.1.0/24"})
        # Invalid CIDR
        with pytest.raises(ValueError, match="Must be a valid CIDR block"):
            manager._validate_inputs_against_schema(plugin, {target_field.id: "192.168.1.1"})

    finally:
        target_field.validation = orig_validation


def test_validate_inputs_rejects_path_traversal(setup_test_environment):
    """_validate_inputs_against_schema must reject ``../`` in STRING/TEXT fields."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    # Use secret_scanner — its target field has no validation pattern
    plugin = manager.get_plugin("secret_scanner")
    assert plugin is not None

    target_field = next(f for f in plugin.fields if f.id == "target")

    with pytest.raises(ValueError, match="traversal"):
        manager._validate_inputs_against_schema(
            plugin,
            {target_field.id: "../../../etc/passwd"},
        )

    with pytest.raises(ValueError, match="traversal"):
        manager._validate_inputs_against_schema(
            plugin,
            {target_field.id: "..\\..\\..\\etc\\passwd"},
        )

    # Legitimate values must still pass
    manager._validate_inputs_against_schema(
        plugin,
        {target_field.id: "/home/user/project"},
    )


def test_plugin_build_command_rejects_path_traversal_in_target(setup_test_environment):
    """build_command must reject ``../`` in free-form string fields like target."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    # secret_scanner has an unprotected string target field passed to --source
    for plugin_id, field_id, traversal_value in [
        ("secret_scanner", "target", "../../../etc/passwd"),
        ("nikto", "config_file", "../../../etc/nikto.conf"),
        ("semgrep_scanner", "target", "../../../etc"),
        ("yara_scan", "target", "../../../etc/passwd"),
    ]:
        plugin = manager.get_plugin(plugin_id)
        assert plugin is not None, f"Plugin {plugin_id} not found"

        with pytest.raises(ValueError, match="traversal"):
            manager.build_command(
                plugin_id,
                {field_id: traversal_value},
            )


def test_plugin_build_command_allows_legitimate_targets(setup_test_environment):
    """build_command must still allow legitimate hostnames, IPs, and URLs."""
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "http_inspector",
        {"url": "https://example.com", "follow_redirects": True},
    )
    assert command is not None
    assert "https://example.com" in command
