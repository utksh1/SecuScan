import os
import shutil
import pytest
from unittest.mock import patch
from pathlib import Path
from backend.secuscan.config import settings
from backend.secuscan.scaffold import generate_scaffold
from scripts.validate_plugin import validate_plugin

@pytest.fixture
def clean_plugins_dir(tmp_path):
    """Temporary plugins directory to isolate scaffolding tests."""
    original_plugins_dir = settings.plugins_dir
    settings.plugins_dir = str(tmp_path)
    yield tmp_path
    settings.plugins_dir = original_plugins_dir

def test_scaffold_success(clean_plugins_dir):
    """Test successful plugin scaffolding with valid inputs."""
    plugin_id = "test_happy_scanner"
    generate_scaffold(plugin_id=plugin_id, name="Test Happy Scanner", safety="safe")

    target_dir = clean_plugins_dir / plugin_id
    assert target_dir.exists()
    assert (target_dir / "metadata.json").exists()
    assert (target_dir / "parser.py").exists()

    # Validate that it passes validate_plugin script requirements
    assert validate_plugin(target_dir) is True

def test_scaffold_invalid_id_traversal(clean_plugins_dir):
    """Test that path traversal attempts in plugin ID are rejected."""
    with pytest.raises(SystemExit) as exc:
        generate_scaffold(plugin_id="../../outside_scanner", name="Traversal", safety="safe")
    assert exc.value.code == 1

def test_scaffold_invalid_id_chars(clean_plugins_dir):
    """Test that invalid characters in plugin ID are rejected."""
    with pytest.raises(SystemExit) as exc:
        generate_scaffold(plugin_id="Invalid@Scanner", name="Invalid", safety="safe")
    assert exc.value.code == 1

def test_scaffold_empty_id(clean_plugins_dir):
    """Test that empty plugin ID is rejected when supplied via CLI args."""
    with pytest.raises(SystemExit) as exc:
        generate_scaffold(plugin_id="", name="Empty", safety="safe")
    assert exc.value.code == 1

def test_scaffold_existing_directory(clean_plugins_dir):
    """Test that scaffolding fails if the target directory already exists."""
    plugin_id = "duplicate_scanner"
    target_dir = clean_plugins_dir / plugin_id
    target_dir.mkdir()

    with pytest.raises(SystemExit) as exc:
        generate_scaffold(plugin_id=plugin_id, name="Duplicate", safety="safe")
    assert exc.value.code == 1

def test_scaffold_invalid_safety_value(clean_plugins_dir):
    """Test that invalid safety levels are rejected."""
    with pytest.raises(SystemExit) as exc:
        generate_scaffold(plugin_id="valid_id", name="Valid", safety="extreme")
    assert exc.value.code == 1
