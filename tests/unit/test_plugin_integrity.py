import asyncio
import json
from pathlib import Path

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
