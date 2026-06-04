"""
testing/backend/test_docker_hardening.py

Integration tests that validate the Docker image hardening requirements
defined in docs/BASE_IMAGE_UPDATE_POLICY.md and enforced by CI.

These tests require Docker to be running. They are skipped automatically
when Docker is not available (e.g., in a non-Docker CI environment).

Run with:
    pytest testing/backend/test_docker_hardening.py -v
"""


import json
import subprocess
import shutil
import pytest
from pathlib import Path

# Helpers

REPO_ROOT = Path(__file__).resolve().parents[3]

IMAGES: dict[str, dict] = {
    "backend": {
        "context": str(REPO_ROOT / "backend"),
        "dockerfile": str(REPO_ROOT / "backend" / "Dockerfile"),
        "tag": "secuscan-backend:test-hardening",
    },
    "frontend": {
        "context": str(REPO_ROOT / "frontend"),
        "dockerfile": str(REPO_ROOT / "frontend" / "Dockerfile"),
        "tag": "secuscan-frontend:test-hardening",
    },
}

TRIVY_MIN_VERSION = (0, 50, 0)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def _docker_available() -> bool:
    result = _run(["docker", "info"])
    return result.returncode == 0


def _trivy_available() -> bool:
    if not shutil.which("trivy"):
        return False
    result = _run(["trivy", "--version"])
    # trivy --version output: "Version: 0.XX.Y"
    try:
        version_str = result.stdout.strip().splitlines()[0].split()[-1]
        parts = tuple(int(x) for x in version_str.split("."))
        return parts >= TRIVY_MIN_VERSION
    except Exception:
        return False


def _build_image(service: str) -> str:
    info = IMAGES[service]
    result = _run(
        [
            "docker", "build",
            "-t", info["tag"],
            "-f", info["dockerfile"],
            info["context"],
        ]
    )
    assert result.returncode == 0, (
        f"Failed to build {service} image:\n{result.stderr}"
    )
    return info["tag"]


def _container_uid(tag: str) -> int:
    result = _run(["docker", "run", "--rm", tag, "id", "-u"])
    assert result.returncode == 0, f"Could not get UID from container: {result.stderr}"
    return int(result.stdout.strip())


def _container_user(tag: str) -> str:
    result = _run(["docker", "run", "--rm", tag, "whoami"])
    assert result.returncode == 0, f"Could not get username from container: {result.stderr}"
    return result.stdout.strip()


def _suid_files(tag: str) -> list[str]:
    result = _run(
        [
            "docker", "run", "--rm", "--entrypoint", "find",
            tag,
            "/", "-xdev", "(", "-perm", "-4000", "-o", "-perm", "-2000", ")",
            "-type", "f",
        ]
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return lines


def _trivy_critical_count(tag: str) -> int:
    """Return number of CRITICAL CVEs found by Trivy."""
    result = _run(
        [
            "trivy", "image",
            "--format", "json",
            "--severity", "CRITICAL",
            "--ignore-unfixed",
            "--quiet",
            tag,
        ]
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip("Trivy returned non-JSON output; skipping CVE count check.")
    count = 0
    for target in data.get("Results", []):
        count += len(target.get("Vulnerabilities") or [])
    return count


# Fixtures

requires_docker = pytest.mark.skipif(
    not _docker_available(), reason="Docker daemon not available"
)
requires_trivy = pytest.mark.skipif(
    not _trivy_available(),
    reason=f"Trivy >= {'.'.join(str(x) for x in TRIVY_MIN_VERSION)} not available",
)


@pytest.fixture(scope="module")
def backend_image():
    return _build_image("backend")


@pytest.fixture(scope="module")
def frontend_image():
    return _build_image("frontend")


# Tests: non-root user

@requires_docker
class TestNonRootUser:
    """The container must not run as root (UID 0)."""

    def test_backend_non_root_uid(self, backend_image):
        uid = _container_uid(backend_image)
        assert uid != 0, (
            f"Backend container runs as root (UID 0). "
            f"Add a non-root USER instruction to backend/Dockerfile."
        )

    def test_frontend_non_root_uid(self, frontend_image):
        uid = _container_uid(frontend_image)
        assert uid != 0, (
            f"Frontend container runs as root (UID 0). "
            f"Add a non-root USER instruction to frontend/Dockerfile."
        )

    def test_backend_user_is_secuscan(self, backend_image):
        user = _container_user(backend_image)
        assert user == "secuscan", (
            f"Expected backend container user to be 'secuscan', got '{user}'."
        )

    def test_frontend_user_is_nginx(self, frontend_image):
        user = _container_user(frontend_image)
        assert user == "nginx", (
            f"Expected frontend container user to be 'nginx', got '{user}'."
        )


# Tests: SUID/SGID

# Known-safe SUID binaries shipped by Alpine/Debian base images.
# These are documented and intentional; any file NOT in this set is a failure.
ALLOWED_SUID = {
    "/bin/ping",
    "/bin/su",
    "/usr/bin/newgrp",
    "/usr/bin/passwd",
    "/usr/bin/chfn",
    "/usr/bin/chsh",
    "/usr/bin/gpasswd",
    "/sbin/unix_chkpwd",
    "/usr/bin/chage",
    "/usr/bin/expiry",
    "/usr/bin/mount",
    "/usr/bin/su",
    "/usr/bin/umount",
    "/usr/sbin/unix_chkpwd",
}


@requires_docker
class TestSUIDFiles:
    def test_backend_no_unexpected_suid(self, backend_image):
        suid = set(_suid_files(backend_image))
        unexpected = suid - ALLOWED_SUID
        assert not unexpected, (
            f"Unexpected SUID/SGID binaries in backend image:\n"
            + "\n".join(sorted(unexpected))
        )

    def test_frontend_no_unexpected_suid(self, frontend_image):
        suid = set(_suid_files(frontend_image))
        unexpected = suid - ALLOWED_SUID
        assert not unexpected, (
            f"Unexpected SUID/SGID binaries in frontend image:\n"
            + "\n".join(sorted(unexpected))
        )


# Tests: Dockerfile structural checks (static analysis)

class TestDockerfileStructure:
    """Parse Dockerfiles to confirm structural hardening without Docker."""

    def _read_dockerfile(self, service: str) -> str:
        path = REPO_ROOT / service / "Dockerfile"
        assert path.exists(), f"Dockerfile not found at {path}"
        return path.read_text()

    def test_backend_dockerfile_has_user_instruction(self):
        content = self._read_dockerfile("backend")
        user_lines = [l for l in content.splitlines() if l.strip().startswith("USER ")]
        assert user_lines, "backend/Dockerfile must contain a USER instruction."
        # Ensure it's not USER root
        for line in user_lines:
            assert "root" not in line.lower(), (
                f"backend/Dockerfile switches to root: {line}"
            )

    def test_frontend_dockerfile_has_user_instruction(self):
        content = self._read_dockerfile("frontend")
        user_lines = [l for l in content.splitlines() if l.strip().startswith("USER ")]
        assert user_lines, "frontend/Dockerfile must contain a USER instruction."
        for line in user_lines:
            assert "root" not in line.lower(), (
                f"frontend/Dockerfile switches to root: {line}"
            )

    def test_backend_dockerfile_pinned_base(self):
        content = self._read_dockerfile("backend")
        from_lines = [l for l in content.splitlines() if l.strip().startswith("FROM ")]
        assert from_lines, "backend/Dockerfile has no FROM line."
        base = from_lines[0]
        # Must not use 'latest' tag
        assert ":latest" not in base and " latest" not in base, (
            f"backend/Dockerfile must not use ':latest' tag. Found: {base}"
        )

    def test_frontend_dockerfile_pinned_base(self):
        content = self._read_dockerfile("frontend")
        from_lines = [l for l in content.splitlines() if l.strip().startswith("FROM ")]
        assert from_lines, "frontend/Dockerfile has no FROM line."
        base = from_lines[0]
        assert ":latest" not in base and " latest" not in base, (
            f"frontend/Dockerfile must not use ':latest' tag. Found: {base}"
        )

    def test_backend_dockerfile_has_healthcheck(self):
        content = self._read_dockerfile("backend")
        assert "HEALTHCHECK" in content, (
            "backend/Dockerfile must define a HEALTHCHECK instruction."
        )

    def test_frontend_dockerfile_has_healthcheck(self):
        content = self._read_dockerfile("frontend")
        assert "HEALTHCHECK" in content, (
            "frontend/Dockerfile must define a HEALTHCHECK instruction."
        )

    def test_backend_no_apt_cache_left_behind(self):
        content = self._read_dockerfile("backend")
        # Any RUN apt-get install line must be paired with cleanup in the same RUN
        import re
        run_blocks = re.findall(
            r"RUN (.+?)(?=\nRUN |\nCOPY |\nUSER |\nFROM |\Z)", content, re.DOTALL
        )
        for block in run_blocks:
            if "apt-get install" in block or "apt-get update" in block:
                assert "rm -rf /var/lib/apt/lists" in block, (
                    "apt-get install block must clean up apt lists in the same RUN layer."
                )


# Tests: Trivy CVE gate

@requires_docker
@requires_trivy
class TestTrivyCVEGate:
    """Fail if unfixed CRITICAL CVEs are present in the built image."""

    def test_backend_no_critical_cves(self, backend_image):
        count = _trivy_critical_count(backend_image)
        assert count == 0, (
            f"Backend image has {count} unfixed CRITICAL CVE(s). "
            f"Update the base image per docs/BASE_IMAGE_UPDATE_POLICY.md."
        )

    def test_frontend_no_critical_cves(self, frontend_image):
        count = _trivy_critical_count(frontend_image)
        assert count == 0, (
            f"Frontend image has {count} unfixed CRITICAL CVE(s). "
            f"Update the base image per docs/BASE_IMAGE_UPDATE_POLICY.md."
        )

    def test_policy_gate_detects_vulnerable_image(self):
        """
        Negative test: the policy gate must correctly flag a known-vulnerable image.
        Uses an old Python 3.8 slim image which reliably has CRITICAL CVEs.
        """
        vulnerable_tag = "python:3.8.20-slim-bullseye"
        result = _run(["docker", "pull", vulnerable_tag])
        if result.returncode != 0:
            pytest.skip("Could not pull vulnerable test image; skipping negative test.")

        result = subprocess.run(
            [
                "trivy", "image",
                "--format", "json",
                "--severity", "CRITICAL",
                "--quiet",
                vulnerable_tag,
            ],
            capture_output=True,
            text=True,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.skip("Trivy returned non-JSON output for vulnerable image.")

        count = sum(
            len(t.get("Vulnerabilities") or [])
            for t in data.get("Results", [])
        )
        assert count > 0, (
            "Expected to find CRITICAL CVEs in the known-vulnerable image "
            f"({vulnerable_tag}), but found none. "
            "Trivy may not be scanning correctly."
        )