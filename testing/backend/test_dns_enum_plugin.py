"""
Contract tests for the dns_enum (DNS Reconnaissance) plugin.

These tests load the real plugins/dns_enum/metadata.json, validate it through
the project PluginMetadataValidator, render commands through the real
PluginManager, and exercise the real parser.py parse() function.

The focus is the example/guidance contract added for issue #856
("Add metadata examples for dns_enum"): the field help, long_description and
presets must document common domain targets and the output expectations
(grouped DNS records, and a critical finding when a zone transfer succeeds).
If that guidance, the command template, or the parser drift, these tests fail.

Related to issue #856.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager
from plugins.dns_enum.parser import parse

PLUGIN_DIR = REPO_ROOT / "plugins" / "dns_enum"
PLUGINS_DIR = REPO_ROOT / "plugins"


def _metadata() -> dict:
    return json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_dns_enum_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_dns_enum_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    assert isinstance(_metadata(), dict)


def test_dns_enum_passes_validator():
    """The full PluginMetadataValidator must accept the plugin without errors."""
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_dns_enum_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    assert _metadata()["id"] == "dns_enum"


def test_dns_enum_engine_is_dnsrecon():
    """Engine must be the dnsrecon CLI binary."""
    data = _metadata()
    assert data["engine"]["type"] == "cli"
    assert data["engine"]["binary"] == "dnsrecon"


def test_dns_enum_output_parser_is_custom():
    """Parser type must be 'custom', backed by parser.py."""
    assert _metadata()["output"]["parser"] == "custom"


def test_dns_enum_parser_file_exists():
    """parser.py must exist alongside metadata.json."""
    assert (PLUGIN_DIR / "parser.py").exists()


def test_dns_enum_has_required_target_field():
    """Plugin must declare a required 'target' field for the domain."""
    fields = {f["id"]: f for f in _metadata()["fields"]}
    assert "target" in fields, "Missing required field: target"
    assert fields["target"]["required"] is True


# ---------------------------------------------------------------------------
# Example / guidance contract (issue #856)
# ---------------------------------------------------------------------------


def test_dns_enum_target_help_documents_example_domain():
    """The target field help must show a concrete domain example and clarify
    that it is a bare domain (no scheme or path)."""
    target = next(f for f in _metadata()["fields"] if f["id"] == "target")
    help_text = target["help"].lower()
    assert "example.com" in target["placeholder"]
    assert "example.com" in help_text
    # Must steer operators away from pasting a URL.
    assert "scheme" in help_text or "no http" in help_text


def test_dns_enum_type_help_documents_output_expectations():
    """The enum-type help must describe what each mode produces."""
    type_field = next(f for f in _metadata()["fields"] if f["id"] == "type")
    help_text = type_field["help"].lower()
    # Output expectations: record types, zone transfer, subdomain discovery.
    assert "soa" in help_text and "mx" in help_text
    assert "zone transfer" in help_text or "axfr" in help_text
    assert "subdomain" in help_text


def test_dns_enum_long_description_documents_targets_and_output():
    """long_description must cover common targets and output expectations,
    and preserve the authorized-use framing."""
    long_desc = _metadata()["long_description"].lower()
    assert "example.com" in long_desc
    assert "record" in long_desc
    assert "critical" in long_desc and (
        "zone transfer" in long_desc or "axfr" in long_desc
    )
    assert "authorized" in long_desc


def test_dns_enum_presets_cover_every_enum_mode():
    """Presets must give a one-click example for each declared enum type, and
    every preset value must be a real option value."""
    data = _metadata()
    type_field = next(f for f in data["fields"] if f["id"] == "type")
    option_values = {opt["value"] for opt in type_field["options"]}

    presets = data["presets"]
    preset_types = {preset.get("type") for preset in presets.values()}

    assert {"standard", "zone_transfer", "subdomain_bruteforce"} <= set(presets)
    # Each enum option is represented by at least one preset...
    assert option_values <= preset_types
    # ...and no preset references an undeclared option value.
    assert preset_types <= option_values


# ---------------------------------------------------------------------------
# Command rendering tests via the real PluginManager
# ---------------------------------------------------------------------------


def test_dns_enum_command_renders_with_default_type(setup_test_environment):
    """With only a target, the default enum type ('std') is applied."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command("dns_enum", {"target": "example.com"})

    assert command == ["dnsrecon", "-d", "example.com", "-t", "std"], (
        f"Command template drift detected. Got: {command}"
    )


def test_dns_enum_command_renders_explicit_zone_transfer(setup_test_environment):
    """An explicit AXFR selection must flow through to '-t axfr'."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        "dns_enum", {"target": "example.com", "type": "axfr"}
    )

    assert command == ["dnsrecon", "-d", "example.com", "-t", "axfr"]


def test_dns_enum_rejects_unknown_enum_type(setup_test_environment):
    """A type outside the declared option set must be rejected, not rendered."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    with pytest.raises(ValueError):
        manager.build_command(
            "dns_enum", {"target": "example.com", "type": "not-a-real-mode"}
        )


def test_dns_enum_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must load dns_enum (this also verifies the checksum)."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("dns_enum")
    assert plugin is not None
    assert plugin.id == "dns_enum"
    assert plugin.name == "DNS Reconnaissance"


# ---------------------------------------------------------------------------
# Parser checks that back the documented output expectations
# ---------------------------------------------------------------------------


def test_dns_enum_standard_output_groups_records_per_host():
    """The metadata promises records 'grouped per host' — verify the parser
    collapses repeated values into one finding per (type, host)."""
    output = "\n".join(
        [
            "[*] NS adi.ns.cloudflare.com 173.245.58.56",
            "[*] NS adi.ns.cloudflare.com 172.64.32.56",
            "[*] MX route1.mx.cloudflare.net 162.159.205.11",
            "[*] A example.com 93.184.216.34",
        ]
    )
    result = parse(output)

    assert result["count"] == 4  # raw record values
    assert len(result["findings"]) == 3  # grouped per (type, host)
    ns = next(f for f in result["findings"] if f["title"].startswith("DNS NS Record"))
    assert ns["metadata"]["record_count"] == 2


def test_dns_enum_zone_transfer_success_raises_critical_finding():
    """The metadata promises a critical finding when AXFR succeeds — verify it."""
    result = parse("[*] A example.com 93.184.216.34\nZone Transfer Successful")

    critical = [f for f in result["findings"] if f["severity"] == "critical"]
    assert critical, "Expected a critical finding for a successful zone transfer"
    assert "Zone Transfer" in critical[0]["title"]
