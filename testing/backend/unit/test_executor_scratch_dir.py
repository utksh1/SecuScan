"""
Unit tests for the reserved scratch-directory mechanism in executor.py.

Issue #1803: the amass plugin hardcoded a world-writable, predictable
``/tmp/amass`` path (symlink-hijack / cross-user-collision / never-cleaned).
Plugins now use the ``SCRATCH_DIR_PLACEHOLDER`` token, which the executor
replaces at run time with a fresh private ``tempfile.mkdtemp`` directory and
removes when the scan ends. These tests cover ``_substitute_scratch_dir``.
"""

import os
import shutil
import stat

import pytest

from backend.secuscan.executor import (
    SCRATCH_DIR_PLACEHOLDER,
    _substitute_scratch_dir,
)


def test_no_placeholder_returns_command_unchanged():
    """Commands without the placeholder are returned verbatim with no dir."""
    command = ["nmap", "-sV", "127.0.0.1"]
    resolved, scratch_dir = _substitute_scratch_dir(command, "nmap")
    assert resolved == command
    assert scratch_dir is None


def test_placeholder_replaced_with_real_existing_dir():
    """The placeholder token is replaced by an actually-created directory."""
    command = ["amass", "enum", "-d", "example.com", "-dir", SCRATCH_DIR_PLACEHOLDER]
    resolved, scratch_dir = _substitute_scratch_dir(command, "amass")
    try:
        assert scratch_dir is not None
        assert os.path.isdir(scratch_dir)
        assert SCRATCH_DIR_PLACEHOLDER not in resolved
        # The '-dir' value is now the real scratch path.
        assert resolved[resolved.index("-dir") + 1] == scratch_dir
    finally:
        if scratch_dir:
            shutil.rmtree(scratch_dir, ignore_errors=True)


def test_scratch_dir_name_is_unpredictable():
    """Two runs get distinct, unguessable directories (no shared /tmp/amass)."""
    cmd = ["amass", "-dir", SCRATCH_DIR_PLACEHOLDER]
    r1, d1 = _substitute_scratch_dir(cmd, "amass")
    r2, d2 = _substitute_scratch_dir(cmd, "amass")
    try:
        assert d1 != d2
        assert d1 not in ("/tmp/amass", "/tmp/amass/")
        assert "secuscan-amass-" in os.path.basename(d1)
    finally:
        shutil.rmtree(d1, ignore_errors=True)
        shutil.rmtree(d2, ignore_errors=True)


def test_multiple_placeholders_all_replaced_with_same_dir():
    """Every placeholder occurrence resolves to the one created directory."""
    command = [SCRATCH_DIR_PLACEHOLDER, "--out", SCRATCH_DIR_PLACEHOLDER]
    resolved, scratch_dir = _substitute_scratch_dir(command, "tool")
    try:
        assert resolved[0] == scratch_dir
        assert resolved[2] == scratch_dir
        assert SCRATCH_DIR_PLACEHOLDER not in resolved
    finally:
        if scratch_dir:
            shutil.rmtree(scratch_dir, ignore_errors=True)


@pytest.mark.skipif(os.name != "posix", reason="POSIX file-mode semantics")
def test_scratch_dir_is_private():
    """mkdtemp creates the directory 0700 so other local users cannot read it."""
    command = ["amass", "-dir", SCRATCH_DIR_PLACEHOLDER]
    _resolved, scratch_dir = _substitute_scratch_dir(command, "amass")
    try:
        mode = stat.S_IMODE(os.stat(scratch_dir).st_mode)
        assert mode == 0o700
    finally:
        if scratch_dir:
            shutil.rmtree(scratch_dir, ignore_errors=True)
