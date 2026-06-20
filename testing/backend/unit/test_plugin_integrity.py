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

    duplicate_ids = {
        plugin_id: folders for plugin_id, folders in ids.items() if len(folders) > 1
    }
    duplicate_names = {
        plugin_name: folders
        for plugin_name, folders in names.items()
        if len(folders) > 1
    }

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
