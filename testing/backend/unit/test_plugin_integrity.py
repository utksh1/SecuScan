import asyncio
import json
from collections import defaultdict
from pathlib import Path

import pytest

from backend.secuscan.plugins import PluginManager
from backend.secuscan.config import settings


def test_plugins_load_without_signature_enforcement(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    loaded = asyncio.run(manager.load_plugins())
    assert loaded > 0


def test_plugins_have_checksums():
    metadata_files = list(Path(settings.plugins_dir).glob("*/metadata.json"))
    assert metadata_files, "Expected plugin metadata files"
    for path in metadata_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("checksum"), f"Missing checksum in {path}"


def test_cli_plugins_declare_engine_binary_as_dependency():
    metadata_files = list(Path(settings.plugins_dir).glob("*/metadata.json"))
    assert metadata_files, "Expected plugin metadata files"

    for path in metadata_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        engine = data.get("engine", {})
        if engine.get("type") != "cli":
            continue

        binary = engine.get("binary")
        dependency_binaries = data.get("dependencies", {}).get("binaries", [])
        assert binary in dependency_binaries, (
            f"{path.parent.name} must declare engine binary {binary!r} "
            "in dependencies.binaries"
        )


def test_plugin_metadata_ids_and_names_are_unique():
    metadata_files = list(Path(settings.plugins_dir).glob("*/metadata.json"))
    assert metadata_files, "Expected plugin metadata files"

    ids = defaultdict(list)
    names = defaultdict(list)

    for path in metadata_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        plugin_id = data.get("id")
        plugin_name = data.get("name")
        assert plugin_id, f"Missing plugin id in {path}"
        assert plugin_name, f"Missing plugin name in {path}"

        ids[plugin_id].append(path.parent.name)
        names[plugin_name].append(path.parent.name)

    duplicate_ids = {plugin_id: folders for plugin_id, folders in ids.items() if len(folders) > 1}
    duplicate_names = {plugin_name: folders for plugin_name, folders in names.items() if len(folders) > 1}

    if duplicate_ids or duplicate_names:
        messages = []
        if duplicate_ids:
            messages.append("Duplicate plugin IDs found:")
            for plugin_id, folders in sorted(duplicate_ids.items()):
                messages.append(f"  {plugin_id}: {', '.join(sorted(folders))}")
        if duplicate_names:
            messages.append("Duplicate plugin display names found:")
            for plugin_name, folders in sorted(duplicate_names.items()):
                messages.append(f"  {plugin_name}: {', '.join(sorted(folders))}")

        pytest.fail("\n".join(messages))


def test_malformed_plugin_missing_required_fields_is_skipped(setup_test_environment, tmp_path):
    """
    A plugin with missing required fields must raise a validation error
    when loaded, not crash silently.
    """
    plugin_dir = tmp_path / "plugins" / "bad_plugin"
    plugin_dir.mkdir(parents=True)
    malformed = {"id": "bad_plugin"}
    (plugin_dir / "metadata.json").write_text(
        json.dumps(malformed), encoding="utf-8"
    )

    manager = PluginManager(str(tmp_path / "plugins"))

    with pytest.raises(Exception):
        asyncio.run(manager._load_plugin_metadata(plugin_dir / "metadata.json"))


def test_malformed_plugin_does_not_crash_loader(setup_test_environment, tmp_path):
    """
    When one plugin has malformed metadata, the loader must skip it and
    continue without crashing.
    """
    plugin_dir = tmp_path / "plugins" / "bad_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "metadata.json").write_text(
        json.dumps({"id": "bad_plugin"}), encoding="utf-8"
    )

    good_dir = tmp_path / "plugins" / "good_plugin"
    good_dir.mkdir(parents=True)
    valid = {
        "id": "good_plugin",
        "name": "Good Plugin",
        "version": "1.0.0",
        "description": "A valid test plugin",
        "category": "recon",
        "engine": {"type": "python", "entrypoint": "python3"},
        "command_template": ["echo", "{target}"],
        "fields": [
            {
                "id": "target",
                "label": "Target",
                "type": "string",
                "required": True,
                "placeholder": "example.com",
                "validation": {},
            }
        ],
        "presets": {},
        "output": {"parser": "none", "format": "text"},
        "safety": {
            "level": "safe",
            "requires_consent": False,
        },
        "dependencies": {"binaries": []},
        "checksum": None,
    }
    (good_dir / "metadata.json").write_text(
        json.dumps(valid), encoding="utf-8"
    )

    manager = PluginManager(str(tmp_path / "plugins"))
    loaded = asyncio.run(manager.load_plugins())

    assert loaded == 1, (
        f"Expected 1 plugin to load (good_plugin), got {loaded}. "
        "Malformed plugin should be skipped, not crash the loader."
    )


def test_malformed_plugin_logs_clear_error(setup_test_environment, tmp_path, caplog):
    """
    When a plugin fails to load, the error log must identify the plugin directory.
    """
    import logging

    plugin_dir = tmp_path / "plugins" / "broken_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "metadata.json").write_text(
        json.dumps({"id": "broken_plugin"}), encoding="utf-8"
    )

    manager = PluginManager(str(tmp_path / "plugins"))

    with caplog.at_level(logging.ERROR, logger="backend.secuscan.plugins"):
        asyncio.run(manager.load_plugins())

    assert any(
        "broken_plugin" in record.message for record in caplog.records
    ), "Expected error log mentioning the broken plugin directory"
