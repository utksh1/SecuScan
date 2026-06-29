import os
import sys
import pathlib

# Add root directory to sys.path so we can import from scripts
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)

from scripts.check_hygiene import (
    is_virtualenv_segment,
    is_pycache_or_pyc,
    is_in_virtualenv,
)

def test_is_virtualenv_segment():
    # Standard virtualenv names
    assert is_virtualenv_segment(".venv") is True
    assert is_virtualenv_segment("venv") is True
    assert is_virtualenv_segment(".venv-codex") is True
    assert is_virtualenv_segment("venv_tests") is True
    assert is_virtualenv_segment("my-venv") is True
    assert is_virtualenv_segment("my_venv") is True
    assert is_virtualenv_segment("env") is True

    # Non-virtualenv names
    assert is_virtualenv_segment("backend") is False
    assert is_virtualenv_segment("secuscan") is False
    assert is_virtualenv_segment("testing") is False
    assert is_virtualenv_segment("myvenv") is False  # doesn't match start/end patterns

def test_is_pycache_or_pyc():
    assert is_pycache_or_pyc("backend/secuscan/__pycache__/routes.cpython-311.pyc") is True
    assert is_pycache_or_pyc("backend/secuscan/routes.pyc") is True
    assert is_pycache_or_pyc("backend/secuscan/__pycache__/routes.py") is True

    assert is_pycache_or_pyc("backend/secuscan/routes.py") is False
    assert is_pycache_or_pyc("backend/secuscan/pycache/routes.py") is False

def test_is_in_virtualenv_by_segment_match(tmp_path):
    git_root = tmp_path

    # Test path that contains venv directory segment
    assert is_in_virtualenv(".venv-codex/lib/python3.11/site-packages/__pycache__/foo.pyc", git_root) is True
    assert is_in_virtualenv("testing/venv_tests/lib/python3.11/site-packages/__pycache__/foo.pyc", git_root) is True

    # Test path that doesn't contain venv directory segment
    assert is_in_virtualenv("backend/secuscan/__pycache__/routes.cpython-311.pyc", git_root) is False

def test_is_in_virtualenv_by_cfg_file(tmp_path):
    git_root = tmp_path

    # Create a dummy virtualenv folder with pyvenv.cfg
    custom_venv_dir = git_root / "my_custom_env"
    custom_venv_dir.mkdir()
    (custom_venv_dir / "pyvenv.cfg").write_text("version = 3.11.0", encoding="utf-8")

    # The file path relative to git_root
    rel_path = "my_custom_env/lib/__pycache__/foo.pyc"

    # Create the nested directory structure physically so it can be resolved on disk
    (custom_venv_dir / "lib" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (custom_venv_dir / "lib" / "__pycache__" / "foo.pyc").touch()

    # Verify that it detects the virtualenv due to the physical pyvenv.cfg file
    assert is_in_virtualenv(rel_path, git_root) is True
