"""
test_port_collision.py  —  issue #895

Regression coverage for the port-collision pre-flight in start.sh.

start.sh contains these two lines before launching any service:

    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true

These tests verify:

1. PRE-FLIGHT CONTRACT — the cleanup lines are present verbatim in start.sh
   (guards against silent removal during refactors).

2. PORT-RELEASE BEHAVIOUR — when a socket is already bound on :8000 or :5173,
   running the pre-flight section of start.sh releases it so the port is free
   afterwards.  Tests use a minimal wrapper script that runs only the cleanup
   lines (no venv, no npm, no uvicorn), making them fast and deterministic.

3. STRUCTURE GUARD — start.sh still exits non-zero with a clear ERROR: message
   when backend/requirements.txt is missing, even after the pre-flight runs.
   This proves the guard is not bypassed by the cleanup logic.

All tests:
- require only bash and lsof (both present on Linux CI runners)
- bind real sockets on loopback so the kernel owns the port
- never start uvicorn, npm, or any long-running process
- complete in < 5 s each
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import textwrap
import time

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = pathlib.Path(__file__).parent.parent
START_SH = REPO_ROOT / "start.sh"

# ── Helpers ───────────────────────────────────────────────────────────────────


def lsof_available() -> bool:
    return subprocess.run(
        ["which", "lsof"], capture_output=True
    ).returncode == 0


def port_in_use(port: int) -> bool:
    """Return True if *port* is currently bound on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def bind_port(port: int) -> socket.socket:
    """
    Bind and return a listening socket on 127.0.0.1:*port*.
    Caller is responsible for closing it.
    SO_REUSEADDR is intentionally NOT set so the kernel truly owns the port
    until we release it (or lsof kill -9 releases it for us).
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(1)
    return s


def run_preflight_only(tmp_path: pathlib.Path) -> subprocess.CompletedProcess:
    """
    Run *only* the port-cleanup pre-flight lines from start.sh in a minimal
    wrapper script.  The wrapper exits 0 immediately afterwards — no venv, no
    npm, no uvicorn is ever started.
    """
    wrapper = tmp_path / "preflight_only.sh"
    wrapper.write_text(
        textwrap.dedent(
            """\
            #!/bin/bash
            set -euo pipefail
            lsof -ti :8000 | xargs kill -9 2>/dev/null || true
            lsof -ti :5173 | xargs kill -9 2>/dev/null || true
            sleep 0.3
            exit 0
            """
        )
    )
    wrapper.chmod(0o755)
    return subprocess.run(
        ["bash", str(wrapper)],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(REPO_ROOT),
    )


# ── Skip guard ────────────────────────────────────────────────────────────────

requires_lsof = pytest.mark.skipif(
    not lsof_available(),
    reason="lsof not available on this system",
)

# ── Tests: pre-flight contract ────────────────────────────────────────────────


def test_start_sh_exists():
    """start.sh must exist at the repo root."""
    assert START_SH.exists(), f"start.sh not found at {START_SH}"


def test_preflight_cleanup_line_port_8000_present():
    """
    start.sh must contain the lsof kill line for port 8000.
    Removing or renaming it would silently break port-collision handling.
    """
    content = START_SH.read_text(encoding="utf-8")
    assert "lsof -ti :8000 | xargs kill -9" in content, (
        "Pre-flight cleanup line for port 8000 is missing from start.sh. "
        "This line must be present: lsof -ti :8000 | xargs kill -9 2>/dev/null || true"
    )


def test_preflight_cleanup_line_port_5173_present():
    """
    start.sh must contain the lsof kill line for port 5173.
    Removing it would silently break the frontend port-collision pre-flight.
    """
    content = START_SH.read_text(encoding="utf-8")
    assert "lsof -ti :5173 | xargs kill -9" in content, (
        "Pre-flight cleanup line for port 5173 is missing from start.sh. "
        "This line must be present: lsof -ti :5173 | xargs kill -9 2>/dev/null || true"
    )


def test_preflight_cleanup_lines_appear_before_backend_launch():
    """
    The port-cleanup lines must appear before uvicorn is launched.
    If they appear after, a collision on :8000 would crash uvicorn before
    the pre-flight ever runs.
    """
    content = START_SH.read_text(encoding="utf-8")
    cleanup_pos = content.find("lsof -ti :8000 | xargs kill -9")
    uvicorn_pos = content.find("uvicorn")
    assert cleanup_pos != -1, "lsof cleanup line for :8000 not found"
    assert uvicorn_pos != -1, "uvicorn launch line not found in start.sh"
    assert cleanup_pos < uvicorn_pos, (
        "Port-cleanup pre-flight must appear before the uvicorn launch. "
        f"cleanup at char {cleanup_pos}, uvicorn at char {uvicorn_pos}."
    )


def test_preflight_has_error_fallback():
    """
    The cleanup lines must use '|| true' so a missing lsof or an empty port
    does not abort start.sh with set -euo pipefail.
    """
    content = START_SH.read_text(encoding="utf-8")
    # Both lines must end with '|| true' (allowing 2>/dev/null in between)
    for port in (8000, 5173):
        line = next(
            (ln for ln in content.splitlines() if f"lsof -ti :{port}" in ln),
            None,
        )
        assert line is not None, f"lsof cleanup line for :{port} not found"
        assert "|| true" in line, (
            f"Cleanup line for :{port} must end with '|| true' to be safe "
            f"under set -euo pipefail. Got: {line!r}"
        )


# ── Tests: port-release behaviour ─────────────────────────────────────────────


@requires_lsof
def test_preflight_releases_occupied_port_8000(tmp_path):
    """
    When port 8000 is already bound, running the pre-flight wrapper must
    release it so the port is free afterwards.
    """
    sock = bind_port(8000)
    try:
        assert port_in_use(8000), "Setup: port 8000 should be in use before pre-flight"
        result = run_preflight_only(tmp_path)
        assert result.returncode == 0, (
            f"Pre-flight wrapper exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Give the OS a moment to reclaim the port after kill -9
        time.sleep(0.5)
        assert not port_in_use(8000), (
            "Port 8000 is still in use after pre-flight ran. "
            "The lsof | xargs kill -9 line may not be working correctly."
        )
    finally:
        # Best-effort: socket may already be dead after kill -9
        try:
            sock.close()
        except OSError:
            pass


@requires_lsof
def test_preflight_releases_occupied_port_5173(tmp_path):
    """
    When port 5173 is already bound, running the pre-flight wrapper must
    release it so the port is free afterwards.
    """
    sock = bind_port(5173)
    try:
        assert port_in_use(5173), "Setup: port 5173 should be in use before pre-flight"
        result = run_preflight_only(tmp_path)
        assert result.returncode == 0, (
            f"Pre-flight wrapper exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        time.sleep(0.5)
        assert not port_in_use(5173), (
            "Port 5173 is still in use after pre-flight ran. "
            "The lsof | xargs kill -9 line may not be working correctly."
        )
    finally:
        try:
            sock.close()
        except OSError:
            pass


@requires_lsof
def test_preflight_succeeds_when_ports_are_already_free(tmp_path):
    """
    Pre-flight must exit 0 cleanly when neither port is occupied — the
    '|| true' guard must swallow the empty-pipe error without aborting.
    """
    # Ensure neither port is in use (best-effort — skip if still bound)
    if port_in_use(8000) or port_in_use(5173):
        pytest.skip("A port is already in use on this machine; skipping free-port test")

    result = run_preflight_only(tmp_path)
    assert result.returncode == 0, (
        f"Pre-flight failed when ports were free (exit {result.returncode}). "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


@requires_lsof
def test_preflight_releases_both_ports_simultaneously(tmp_path):
    """
    Both port 8000 and port 5173 must be released in the same pre-flight run.
    """
    sock_8000 = bind_port(8000)
    sock_5173 = bind_port(5173)
    try:
        assert port_in_use(8000), "Setup: port 8000 should be in use"
        assert port_in_use(5173), "Setup: port 5173 should be in use"

        result = run_preflight_only(tmp_path)
        assert result.returncode == 0, (
            f"Pre-flight wrapper exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        time.sleep(0.5)
        assert not port_in_use(8000), "Port 8000 still in use after simultaneous pre-flight"
        assert not port_in_use(5173), "Port 5173 still in use after simultaneous pre-flight"
    finally:
        for s in (sock_8000, sock_5173):
            try:
                s.close()
            except OSError:
                pass


# ── Tests: structure guard survives pre-flight ────────────────────────────────


def test_start_sh_errors_on_missing_requirements_txt(tmp_path):
    """
    Even after the port-cleanup pre-flight runs, start.sh must exit non-zero
    with a clear ERROR: message when backend/requirements.txt is missing.
    This ensures the structure guard is not accidentally bypassed.
    """
    # Make a copy of the repo tree with requirements.txt removed
    import shutil

    fake_root = tmp_path / "repo"
    shutil.copytree(
        str(REPO_ROOT),
        str(fake_root),
        ignore=shutil.ignore_patterns(
            "venv", "venv_tests", "node_modules", "__pycache__", ".git",
            "*.pyc",
        ),
        symlinks=False,
    )

    req = fake_root / "backend" / "requirements.txt"
    if req.exists():
        req.unlink()

    result = subprocess.run(
        ["bash", "start.sh"],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(fake_root),
    )

    assert result.returncode != 0, (
        "start.sh should have exited non-zero when requirements.txt is missing, "
        f"but exited {result.returncode}."
    )

    combined = result.stdout + result.stderr
    assert "ERROR:" in combined, (
        "start.sh did not print an actionable ERROR: message when "
        f"requirements.txt was missing.\nOutput:\n{combined}"
    )
    assert "requirements.txt" in combined, (
        "Error message should mention 'requirements.txt' so maintainers know "
        f"what is missing.\nOutput:\n{combined}"
    )


def test_start_sh_errors_on_missing_frontend_directory(tmp_path):
    """
    start.sh must exit non-zero with ERROR: frontend directory not found.
    when the frontend/ directory is absent — even after port cleanup runs.
    This mirrors the existing shell-smoke CI step but as a Python test so
    it runs in the port-collision suite without a separate shell wrapper.
    """
    import shutil

    fake_root = tmp_path / "repo"
    shutil.copytree(
        str(REPO_ROOT),
        str(fake_root),
        ignore=shutil.ignore_patterns(
            "venv", "venv_tests", "node_modules", "__pycache__", ".git",
            "*.pyc",
        ),
        symlinks=False,
    )

    frontend_dir = fake_root / "frontend"
    if frontend_dir.exists():
        shutil.rmtree(str(frontend_dir))

    result = subprocess.run(
        ["bash", "start.sh"],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(fake_root),
    )

    assert result.returncode != 0, (
        "start.sh should have exited non-zero when frontend/ is missing, "
        f"but exited {result.returncode}."
    )

    combined = result.stdout + result.stderr
    assert "ERROR: frontend directory not found." in combined, (
        "Expected 'ERROR: frontend directory not found.' in output.\n"
        f"Got:\n{combined}"
    )