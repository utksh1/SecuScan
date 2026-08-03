"""
Tests for issue #1812 — enforce hard failure when a plugin declares
output.parser == 'custom' but parser.py is missing from the plugin's
directory.

What we're testing:
- _validate_plugin rejects (returns False) a custom-parser plugin missing
  parser.py, instead of the old soft-warning-and-pass behavior.
- compute_plugin_digest(..., require_parser=True) raises FileNotFoundError
  when parser.py is absent.
- _verify_plugin_integrity propagates that failure for custom-parser plugins.
- Plugins using non-custom (built-in) parsers never require parser.py and
  continue to load/verify successfully — no regression for the common case.
"""

import asyncio
import json
from pathlib import Path

import pytest

from backend.secuscan.plugins import PluginManager


def make_plugin(
    tmp_path: Path,
    plugin_id: str,
    *,
    checksum: str | None = "auto",
    parser_type: str = "custom",
    parser_content: str | None = "def parse(output): return []",
    include_name: bool = True,
) -> Path:
    """Build a minimal, well-formed plugin directory under tmp_path."""
    plugin_dir = tmp_path / plugin_id
    plugin_dir.mkdir()

    metadata = {
        "id": plugin_id,
        "version": "1.0.0",
        "description": "Test plugin",
        "category": "recon",
        "engine": {"type": "cli", "binary": "echo"},
        "command_template": ["echo", "{target}"],
        "fields": [
            {"id": "target", "label": "Target", "type": "string", "required": True}
        ],
        "presets": {},
        "output": {"format": "text", "parser": parser_type},
        "safety": {"level": "safe"},
    }

    if include_name:
        metadata["name"] = f"Test Plugin {plugin_id}"

    if parser_content is not None:
        (plugin_dir / "parser.py").write_text(parser_content, encoding="utf-8")

    metadata_file = plugin_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    if checksum == "auto":
        expected = PluginManager.compute_plugin_digest(metadata_file, plugin_dir / "parser.py")
        metadata["checksum"] = expected
    elif checksum is not None:
        metadata["checksum"] = checksum

    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return plugin_dir


# ---------------------------------------------------------------------------
# 1. Happy path — custom parser present, everything passes
# ---------------------------------------------------------------------------


def test_custom_parser_present_passes_validation(tmp_path):
    manager = PluginManager(str(tmp_path))
    plugin_dir = make_plugin(tmp_path, "custom-ok")
    metadata_file = plugin_dir / "metadata.json"

    plugin_meta = asyncio.run(manager._load_plugin_metadata(metadata_file))

    assert asyncio.run(manager._validate_plugin(plugin_meta, plugin_dir)) is True


def test_custom_parser_present_plugin_loads_via_load_plugins(tmp_path):
    make_plugin(tmp_path, "custom-ok")
    manager = PluginManager(str(tmp_path))

    loaded = asyncio.run(manager.load_plugins())

    assert loaded == 1
    assert manager.get_plugin("custom-ok") is not None


# ---------------------------------------------------------------------------
# 2. Failure path — _validate_plugin hard-fails when parser.py missing
# ---------------------------------------------------------------------------


def test_validate_plugin_fails_when_custom_parser_missing(tmp_path):
    manager = PluginManager(str(tmp_path))
    plugin_dir = make_plugin(tmp_path, "custom-missing", parser_content=None, checksum=None)
    metadata_file = plugin_dir / "metadata.json"

    plugin_meta = asyncio.run(manager._load_plugin_metadata(metadata_file))

    assert asyncio.run(manager._validate_plugin(plugin_meta, plugin_dir)) is False


def test_validate_plugin_logs_error_not_warning_when_parser_missing(tmp_path, caplog):
    manager = PluginManager(str(tmp_path))
    plugin_dir = make_plugin(tmp_path, "custom-missing-log", parser_content=None, checksum=None)
    metadata_file = plugin_dir / "metadata.json"
    plugin_meta = asyncio.run(manager._load_plugin_metadata(metadata_file))

    with caplog.at_level("ERROR", logger="backend.secuscan.plugins"):
        result = asyncio.run(manager._validate_plugin(plugin_meta, plugin_dir))

    assert result is False
    assert any(
        "custom" in record.message and "parser.py" in record.message
        for record in caplog.records
        if record.levelname == "ERROR"
    )


def test_load_plugins_skips_plugin_with_missing_custom_parser(tmp_path):
    """End-to-end: load_plugins() must not register a broken custom-parser plugin."""
    make_plugin(tmp_path, "custom-missing-e2e", parser_content=None, checksum=None)
    manager = PluginManager(str(tmp_path))

    loaded = asyncio.run(manager.load_plugins())

    assert loaded == 0
    assert manager.get_plugin("custom-missing-e2e") is None


# ---------------------------------------------------------------------------
# 3. compute_plugin_digest(require_parser=True) raises FileNotFoundError
# ---------------------------------------------------------------------------


def test_compute_plugin_digest_raises_when_parser_required_but_missing(tmp_path):
    plugin_dir = make_plugin(tmp_path, "digest-missing", parser_content=None, checksum=None)
    metadata_file = plugin_dir / "metadata.json"
    parser_file = plugin_dir / "parser.py"

    assert not parser_file.exists()

    with pytest.raises(FileNotFoundError):
        PluginManager.compute_plugin_digest(metadata_file, parser_file, require_parser=True)


def test_compute_plugin_digest_succeeds_when_parser_required_and_present(tmp_path):
    plugin_dir = make_plugin(tmp_path, "digest-present", checksum=None)
    metadata_file = plugin_dir / "metadata.json"
    parser_file = plugin_dir / "parser.py"

    digest = PluginManager.compute_plugin_digest(metadata_file, parser_file, require_parser=True)

    assert isinstance(digest, str)
    assert len(digest) == 64  # sha256 hex digest


def test_compute_plugin_digest_default_does_not_require_parser(tmp_path):
    """Backward-compat: require_parser defaults to False, so existing call
    sites that never pass it keep the old lenient (empty parser digest) behavior.
    """
    plugin_dir = make_plugin(tmp_path, "digest-legacy", parser_content=None, checksum=None)
    metadata_file = plugin_dir / "metadata.json"
    parser_file = plugin_dir / "parser.py"

    digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)

    assert isinstance(digest, str)
    assert len(digest) == 64


def test_verify_plugin_integrity_fails_for_custom_parser_missing_at_verify_time(tmp_path):
    """_verify_plugin_integrity must pass require_parser=True for custom-parser
    plugins so a parser.py deleted after metadata load is still caught.
    """
    manager = PluginManager(str(tmp_path))
    plugin_dir = make_plugin(tmp_path, "verify-missing")
    metadata_file = plugin_dir / "metadata.json"
    plugin_meta = asyncio.run(manager._load_plugin_metadata(metadata_file))

    # Parser existed at checksum-computation time, but is now deleted —
    # simulates a race / tamper between metadata load and integrity check.
    (plugin_dir / "parser.py").unlink()

    assert manager._verify_plugin_integrity(plugin_meta, plugin_dir) is False


# ---------------------------------------------------------------------------
# 4. Backward compatibility — non-custom parsers never require parser.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("parser_type", ["default", "json", "regex", "builtin"])
def test_non_custom_parser_does_not_require_parser_file(tmp_path, parser_type):
    manager = PluginManager(str(tmp_path))
    plugin_dir = make_plugin(
        tmp_path, f"builtin-{parser_type}", parser_type=parser_type, parser_content=None, checksum=None
    )
    metadata_file = plugin_dir / "metadata.json"
    plugin_meta = asyncio.run(manager._load_plugin_metadata(metadata_file))

    assert not (plugin_dir / "parser.py").exists()
    assert asyncio.run(manager._validate_plugin(plugin_meta, plugin_dir)) is True


def test_non_custom_parser_plugin_loads_via_load_plugins(tmp_path):
    make_plugin(tmp_path, "builtin-ok", parser_type="default", parser_content=None, checksum=None)
    manager = PluginManager(str(tmp_path))

    loaded = asyncio.run(manager.load_plugins())

    assert loaded == 1
    assert manager.get_plugin("builtin-ok") is not None


def test_compute_plugin_digest_require_parser_false_for_builtin_parser(tmp_path):
    """Digest computation for a non-custom plugin must not raise even though
    require_parser is being decided from plugin.output.parser upstream —
    here we assert the low-level contract directly: require_parser=False
    tolerates a missing parser.py.
    """
    plugin_dir = make_plugin(
        tmp_path, "builtin-digest", parser_type="default", parser_content=None, checksum=None
    )
    metadata_file = plugin_dir / "metadata.json"
    parser_file = plugin_dir / "parser.py"

    digest = PluginManager.compute_plugin_digest(metadata_file, parser_file, require_parser=False)

    assert isinstance(digest, str)
    assert len(digest) == 64
