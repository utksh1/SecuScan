import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

import json
from unittest.mock import patch, MagicMock
from scripts import generate_sbom


class TestGetPythonPackages:
    def test_returns_empty_for_missing_requirements_file(self, tmp_path):
        result = generate_sbom.get_python_packages(str(tmp_path / "nonexistent.txt"))
        assert result == []

    def test_skips_comments_and_empty_lines(self, tmp_path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# comment\n\nflask==2.0.0\n")
        with patch.object(generate_sbom.subprocess, "run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{"name": "Flask", "version": "2.0.0"}]),
            )
            pkgs = generate_sbom.get_python_packages(str(req_file))
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "Flask"
        assert pkgs[0]["version"] == "2.0.0"


class TestGetNpmPackages:
    def test_returns_empty_for_missing_package_json(self, tmp_path):
        result = generate_sbom.get_npm_packages(str(tmp_path / "nonexistent.json"))
        assert result == []

    def test_parses_direct_dependencies(self, tmp_path):
        pkg_file = tmp_path / "package.json"
        pkg_file.write_text(
            json.dumps({
                "dependencies": {"axios": "^1.0.0"},
                "devDependencies": {"vitest": "~0.34.0"},
            })
        )
        with patch.object(generate_sbom.subprocess, "run") as mock_run:
            mock_run.side_effect = Exception("npm not available")
            pkgs = generate_sbom.get_npm_packages(str(pkg_file))
        assert len(pkgs) == 2
        names = {p["name"] for p in pkgs}
        assert "axios" in names
        assert "vitest" in names


class TestGenerateSbom:
    def test_cyclonedx_format_structure(self, tmp_path):
        sbom_file = tmp_path / "sbom.json"
        with patch.object(generate_sbom, "get_python_packages", return_value=[]):
            with patch.object(generate_sbom, "get_npm_packages", return_value=[]):
                generate_sbom.generate_sbom(str(sbom_file))

        assert sbom_file.exists()
        sbom = json.loads(sbom_file.read_text())
        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == "1.4"
        assert "serialNumber" in sbom
        assert sbom["version"] == 1
        assert "metadata" in sbom
        assert sbom["metadata"]["component"]["name"] == "SecuScan"
        assert "components" in sbom

    def test_includes_python_packages(self, tmp_path):
        sbom_file = tmp_path / "sbom.json"
        fake_python_pkgs = [
            {"name": "requests", "version": "2.31.0", "type": "python-package", "scope": "runtime"},
        ]
        with patch.object(generate_sbom, "get_python_packages", return_value=fake_python_pkgs):
            with patch.object(generate_sbom, "get_npm_packages", return_value=[]):
                generate_sbom.generate_sbom(str(sbom_file))

        sbom = json.loads(sbom_file.read_text())
        assert len(sbom["components"]) == 1
        comp = sbom["components"][0]
        assert comp["name"] == "requests"
        assert comp["version"] == "2.31.0"

    def test_includes_npm_packages(self, tmp_path):
        sbom_file = tmp_path / "sbom.json"
        fake_npm_pkgs = [
            {"name": "lodash", "version": "4.17.21", "type": "npm-package", "scope": "runtime"},
        ]
        with patch.object(generate_sbom, "get_python_packages", return_value=[]):
            with patch.object(generate_sbom, "get_npm_packages", return_value=fake_npm_pkgs):
                generate_sbom.generate_sbom(str(sbom_file))

        sbom = json.loads(sbom_file.read_text())
        assert len(sbom["components"]) == 1
        comp = sbom["components"][0]
        assert comp["name"] == "lodash"
        assert comp["version"] == "4.17.21"

    def test_bom_ref_is_unique_per_package(self, tmp_path):
        sbom_file = tmp_path / "sbom.json"
        fake_pkgs = [
            {"name": "a", "version": "1.0.0", "type": "python-package", "scope": "runtime"},
            {"name": "b", "version": "2.0.0", "type": "python-package", "scope": "runtime"},
        ]
        with patch.object(generate_sbom, "get_python_packages", return_value=fake_pkgs):
            with patch.object(generate_sbom, "get_npm_packages", return_value=[]):
                generate_sbom.generate_sbom(str(sbom_file))

        sbom = json.loads(sbom_file.read_text())
        bom_refs = {c["bom-ref"] for c in sbom["components"]}
        assert len(bom_refs) == 2
