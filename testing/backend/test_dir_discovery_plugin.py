"""
Wordlist guidance and safe-default contract tests for the dir_discovery plugin.

These tests load the real plugins/dir_discovery/metadata.json, validate it through
the project PluginMetadataValidator, and assert the wordlist field's safe default
and source guidance both directly and as resolved by the real PluginManager (the
path the executor uses to turn a wordlist alias into an on-disk file).

dir_discovery brute-forces web paths with ffuf and is therefore ``intrusive``.
Only ``small.txt`` ships with SecuScan; ``medium``/``large`` must be installed from
SecLists. The field default must therefore be the bundled ``small`` list so an
out-of-the-box scan resolves to a real wordlist and stays fast and low-traffic.

Related to issue #855: Add safer default wordlist guidance for dir_discovery
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.config import settings
from backend.secuscan.plugin_validator import PluginMetadataValidator
from backend.secuscan.plugins import PluginManager

PLUGIN_DIR = REPO_ROOT / "plugins" / "dir_discovery"
PLUGINS_DIR = REPO_ROOT / "plugins"
WORDLISTS_DIR = REPO_ROOT / "wordlists"


def _load_metadata() -> dict:
    return json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))


def _wordlist_field(metadata: dict) -> dict:
    return next(f for f in metadata["fields"] if f["id"] == "wordlist")


# ---------------------------------------------------------------------------
# Metadata contract tests
# ---------------------------------------------------------------------------


def test_dir_discovery_metadata_file_exists():
    """metadata.json must exist at the expected plugin path."""
    assert (PLUGIN_DIR / "metadata.json").exists()


def test_dir_discovery_metadata_is_valid_json():
    """metadata.json must be valid, parseable JSON."""
    assert isinstance(_load_metadata(), dict)


def test_dir_discovery_metadata_id_matches_directory():
    """Plugin id in metadata.json must match the directory name."""
    assert _load_metadata()["id"] == "dir_discovery"


def test_dir_discovery_passes_validator():
    """The full PluginMetadataValidator must accept the plugin without errors."""
    result = PluginMetadataValidator(PLUGIN_DIR).validate()
    assert result.valid, "Plugin validation errors:\n" + "\n".join(
        e.display() for e in result.errors
    )


def test_dir_discovery_is_intrusive_and_consented():
    """dir_discovery brute-forces paths, so it must stay intrusive + consent-gated."""
    safety = _load_metadata()["safety"]
    assert safety["level"] == "intrusive"
    assert safety["requires_consent"] is True


# ---------------------------------------------------------------------------
# Wordlist safe-default + source guidance (issue #855)
# ---------------------------------------------------------------------------


def test_wordlist_options_are_small_medium_large():
    """The wordlist field must expose exactly the small/medium/large aliases."""
    field = _wordlist_field(_load_metadata())
    assert [opt["value"] for opt in field["options"]] == ["small", "medium", "large"]


def test_wordlist_default_is_bundled_small():
    """
    The safe default must be the bundled 'small' list. 'medium'/'large' are not
    shipped, so defaulting to them would resolve to a missing file and fail.
    """
    field = _wordlist_field(_load_metadata())
    assert field["default"] == "small"
    assert field["default"] in {opt["value"] for opt in field["options"]}


def test_wordlist_help_explains_source_and_default():
    """Help text must name the expected source and the bundled-default behavior."""
    help_text = _wordlist_field(_load_metadata())["help"].lower()
    assert "seclists" in help_text
    assert "wordlists/readme.md" in help_text
    assert "small" in help_text


def test_command_template_consumes_wordlist_field():
    """The wordlist field must actually feed ffuf's -w argument."""
    assert "{wordlist}" in _load_metadata()["command_template"]


# ---------------------------------------------------------------------------
# Bundled asset + resolution behavior
# ---------------------------------------------------------------------------


def test_bundled_small_wordlist_exists_and_is_nonempty():
    """small.txt must be committed and contain at least one path entry."""
    small = WORDLISTS_DIR / "small.txt"
    assert small.exists(), "wordlists/small.txt must be bundled"
    entries = [
        ln for ln in small.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert entries, "wordlists/small.txt must contain at least one entry"


def test_default_wordlist_resolves_to_real_bundled_file(monkeypatch):
    """
    The default alias ('small') must resolve through the real PluginManager to an
    existing file inside the wordlists directory — proving the safe default is
    backed by a shipped wordlist, not a missing external one. Point wordlists_dir
    at the directory that holds the bundled list so the check is deterministic.
    """
    monkeypatch.setattr(settings, "wordlists_dir", str(WORDLISTS_DIR))
    manager = PluginManager(str(PLUGINS_DIR))
    default_value = _wordlist_field(_load_metadata())["default"]

    resolved = manager._resolve_wordlist_path(default_value)

    assert os.path.exists(
        resolved
    ), f"default wordlist {default_value!r} must resolve to a real file"
    assert os.path.basename(resolved) == "small.txt"
    resolved_parent = Path(resolved).resolve().parent
    assert resolved_parent == WORDLISTS_DIR.resolve()


def test_dir_discovery_loads_with_refreshed_checksum(setup_test_environment):
    """
    PluginManager must load dir_discovery, which only succeeds if the metadata
    checksum was refreshed after the edit (integrity check rejects mismatches).
    """
    manager = PluginManager(str(PLUGINS_DIR))
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("dir_discovery")
    assert plugin is not None
    assert plugin.id == "dir_discovery"
