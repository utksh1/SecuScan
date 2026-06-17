"""
Capability inventory and contract tests for the http_inspector plugin.

These tests load the real plugins/http_inspector/metadata.json, validate it
through the project PluginMetadataValidator, and assert the declared capability
inventory both directly and as surfaced by the real PluginManager (the path the
UI uses for capability-based grouping).

http_inspector performs safe, read-only HTTP requests, so the only capability it
exercises is outbound ``network``. Declaring it explicitly keeps UI grouping
predictable instead of relying on the safety-level implied fallback.

Related to issue #854: Add capability inventory notes for http_inspector
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.capabilities import (
    effective_capabilities,
    validate_capability_list,
    _SAFETY_LEVEL_IMPLIED,
)
from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager

PLUGIN_DIR = REPO_ROOT / "plugins" / "http_inspector"
PLUGINS_DIR = REPO_ROOT / "plugins"


def _load_metadata() -> dict:
    return json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_http_inspector_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_http_inspector_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    assert isinstance(_load_metadata(), dict)


def test_http_inspector_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    assert _load_metadata()["id"] == "http_inspector"


def test_http_inspector_passes_validator():
    """The full PluginMetadataValidator must accept the plugin without errors."""
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_http_inspector_is_safe_level():
    """http_inspector is a read-only HTTP tool and must stay at safety level 'safe'."""
    assert _load_metadata()["safety"]["level"] == "safe"


# ---------------------------------------------------------------------------
# Capability inventory tests (issue #854)
# ---------------------------------------------------------------------------


def test_http_inspector_declares_capabilities_explicitly():
    """Metadata must declare an explicit capabilities list (not rely on the fallback)."""
    data = _load_metadata()
    assert "capabilities" in data, "http_inspector must declare a capabilities list"
    assert data["capabilities"] == ["network"]


def test_http_inspector_capabilities_are_known_tokens():
    """Declared capabilities must all be recognised capability tokens."""
    caps = _load_metadata()["capabilities"]
    assert validate_capability_list(caps, "http_inspector") == ["network"]


def test_http_inspector_capabilities_match_implied_safe_set():
    """
    The explicit declaration must match the capability set previously implied by
    the 'safe' safety level, proving this change documents existing behavior
    rather than altering enforcement.
    """
    data = _load_metadata()
    effective = effective_capabilities(
        data["capabilities"], data["safety"]["level"], "http_inspector"
    )
    assert effective == {"network"}
    assert effective == set(_SAFETY_LEVEL_IMPLIED["safe"])


# ---------------------------------------------------------------------------
# Capability surfacing via the real PluginManager (UI grouping path)
# ---------------------------------------------------------------------------


def test_http_inspector_loaded_by_plugin_manager(setup_test_environment):
    """PluginManager must load http_inspector and expose its declared capabilities."""
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("http_inspector")
    assert plugin is not None
    assert plugin.id == "http_inspector"
    assert plugin.capabilities == ["network"]


def test_http_inspector_capabilities_surface_in_listing(setup_test_environment):
    """
    list_plugins() must report capabilities for http_inspector so the UI can group
    it predictably.
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    entry = next(
        (p for p in manager.list_plugins() if p["id"] == "http_inspector"), None
    )
    assert entry is not None
    assert entry["capabilities"] == ["network"]
