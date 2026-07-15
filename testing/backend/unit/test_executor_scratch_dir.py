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
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.secuscan.database import get_db, init_db
from backend.secuscan.config import settings
from backend.secuscan.executor import (
    SCRATCH_DIR_PLACEHOLDER,
    TaskExecutor,
    _substitute_scratch_dir,
)
from backend.secuscan.models import TaskStatus


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


# ---------------------------------------------------------------------------
# Docker command path (PR #2020 review): the host scratch dir must be
# bind-mounted into the sandbox container, else the tool cannot write there.
# ---------------------------------------------------------------------------


async def _run_standard_scanner_with_docker(command, docker_image="caffix/amass:latest"):
    """Drive ``_execute_standard_scanner`` with Docker enabled.

    Returns ``(final_command, scratch_dir, existed_during_run)`` where
    ``final_command`` is the argv actually handed to ``_execute_command``.
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target,
                           inputs_json, status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, owner_id, "amass", "amass", "example.com", "{}",
         TaskStatus.QUEUED.value, 1, 0),
    )

    executor = TaskExecutor()

    mock_plugin = MagicMock()
    mock_plugin.id = "amass"
    mock_plugin.name = "amass"
    mock_plugin.docker_image = docker_image

    recorded = {}

    # Capture the real scratch dir the executor creates by wrapping the helper,
    # so recovery is robust to path formats (e.g. Windows drive-letter colons).
    real_substitute = _substitute_scratch_dir

    def wrapped_substitute(cmd, plugin_id):
        resolved, sd = real_substitute(cmd, plugin_id)
        recorded["scratch_dir"] = sd
        return resolved, sd

    def fake_execute_command(cmd, task, timeout=None):
        recorded["command"] = list(cmd)
        sd = recorded.get("scratch_dir")
        recorded["existed_during_run"] = bool(sd) and os.path.isdir(sd)
        return ("mock output\n", 0)

    try:
        with patch("backend.secuscan.executor.get_plugin_manager") as mock_pm, \
             patch("backend.secuscan.executor._substitute_scratch_dir", wrapped_substitute), \
             patch.object(settings, "docker_enabled", True), \
             patch.object(executor, "_ensure_docker_network", new=AsyncMock()), \
             patch("backend.secuscan.validation.validate_command_network_egress",
                   return_value=(True, None)), \
             patch.object(executor, "_execute_command",
                          side_effect=fake_execute_command), \
             patch.object(executor, "_classify_command_result",
                          return_value=(TaskStatus.COMPLETED.value, None)), \
             patch.object(executor, "_upsert_findings_and_report", new=AsyncMock()):
            mock_pm.return_value.build_command.return_value = command

            await executor._execute_standard_scanner(
                db=db,
                task_id=task_id,
                owner_id=owner_id,
                plugin=mock_plugin,
                plugin_id="amass",
                target="example.com",
                inputs={},
                safe_mode=0,
            )
    finally:
        await db.disconnect()

    return recorded["command"], recorded.get("scratch_dir"), recorded["existed_during_run"]


@pytest.mark.asyncio
async def test_docker_mode_bind_mounts_scratch_dir():
    """In Docker mode the private scratch dir is mounted into the container."""
    command = ["amass", "enum", "-d", "example.com", "-dir", SCRATCH_DIR_PLACEHOLDER]
    final_command, scratch_dir, existed = await _run_standard_scanner_with_docker(command)

    # A docker run wrapper with an explicit bind mount was built.
    assert final_command[:2] == ["docker", "run"]
    assert "-v" in final_command
    assert f"{scratch_dir}:{scratch_dir}:rw" in final_command

    # The placeholder is fully resolved and the vulnerable path is gone.
    assert SCRATCH_DIR_PLACEHOLDER not in final_command
    assert scratch_dir not in ("/tmp/amass", "/tmp/amass/")
    assert "secuscan-amass-" in os.path.basename(scratch_dir)

    # The inner tool references the *same* path that was mounted.
    assert final_command[final_command.index("-dir") + 1] == scratch_dir

    # The mount points at a directory that really existed during the run.
    assert existed is True


@pytest.mark.asyncio
async def test_docker_mode_cleans_up_scratch_dir():
    """The scratch dir is removed after the Docker run finishes."""
    command = ["amass", "enum", "-d", "example.com", "-dir", SCRATCH_DIR_PLACEHOLDER]
    _final_command, scratch_dir, existed = await _run_standard_scanner_with_docker(command)

    assert existed is True
    # finally-block cleanup removed the host directory once execution ended.
    assert not os.path.exists(scratch_dir)


@pytest.mark.asyncio
async def test_docker_mode_without_placeholder_adds_no_mount():
    """A plugin that uses no scratch token gets no bind mount."""
    command = ["nmap", "-sV", "127.0.0.1"]
    final_command, _scratch, _existed = await _run_standard_scanner_with_docker(
        command, docker_image="instrumentisto/nmap:latest"
    )
    assert final_command[:2] == ["docker", "run"]
    assert "-v" not in final_command
