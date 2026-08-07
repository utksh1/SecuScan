import shutil
import subprocess
import pytest


def test_check_artifacts_regression_suite():
    bash_bin = shutil.which("bash")
    if not bash_bin:
        pytest.skip("bash shell not available")

    result = subprocess.run(
        [bash_bin, "scripts/check-artifacts.sh", "--test"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Artifact guard regression tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "All regression tests passed successfully!" in result.stdout
