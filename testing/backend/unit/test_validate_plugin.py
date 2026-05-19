"""
Tests for scripts/validate_plugin.py

What we're testing:
- Valid plugin passes validation
- Missing or mismatched checksum fails
- Custom parser import requirements are enforced
- Invalid metadata fails schema validation
"""

import json
import sys
from pathlib import Path

import pytest

# Add repo root to sys.path so we can import the script directly
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root))

from backend.secuscan.plugins import PluginManager
from scripts.validate_plugin import validate_plugin


def make_plugin(
    tmp_path: Path,
    plugin_id: str,
    *,
    checksum: str | None = "auto",
    parser_type: str = "custom",
    parser_content: str | None = "def parse(output): return []",
    include_name: bool = True,
) -> Path:
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


def test_validate_plugin_success(tmp_path):
    plugin_dir = make_plugin(tmp_path, "test-plugin")
    assert validate_plugin(plugin_dir) is True


def test_fails_when_checksum_missing(tmp_path):
    plugin_dir = make_plugin(tmp_path, "missing-checksum", checksum=None)
    assert validate_plugin(plugin_dir) is False


def test_fails_when_checksum_mismatch(tmp_path):
    plugin_dir = make_plugin(tmp_path, "bad-checksum", checksum="wrong")
    assert validate_plugin(plugin_dir) is False


def test_fails_when_custom_parser_missing(tmp_path):
    plugin_dir = make_plugin(tmp_path, "missing-parser", parser_content=None)
    assert validate_plugin(plugin_dir) is False


def test_fails_when_parser_missing_parse_function(tmp_path):
    plugin_dir = make_plugin(tmp_path, "bad-parser", parser_content="def nope(): return []")
    assert validate_plugin(plugin_dir) is False


def test_fails_on_invalid_metadata(tmp_path):
    plugin_dir = make_plugin(tmp_path, "invalid-metadata", include_name=False)
    assert validate_plugin(plugin_dir) is False
