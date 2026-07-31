"""Regression tests for start.sh port collision handling."""

import socket
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_startup_rejects_occupied_required_ports() -> None:
    if shutil.which("bash") is None:
        raise unittest.SkipTest("bash is required to test start.sh")

    for port in (8000, 5173):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
            listener.listen(1)

            result = subprocess.run(
                [shutil.which("bash"), "start.sh"],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=False,
            )

        output = result.stdout + result.stderr
        assert result.returncode == 1
        assert f"ERROR: port {port} is already in use." in output
        assert f"Stop the process using port {port}, then run ./start.sh again." in output


if __name__ == "__main__":
    try:
        test_startup_rejects_occupied_required_ports()
    except unittest.SkipTest as exc:
        print(f"SKIPPED: {exc}")
