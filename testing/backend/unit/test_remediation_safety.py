import json
import tempfile
from pathlib import Path
import pytest
from packaging.specifiers import SpecifierSet
from backend.secuscan.remediation import (
    normalize_package_name,
    clean_version_string,
    parse_remediation_suggestion,
    semver_to_pep440,
    parse_package_lock,
    parse_package_json,
    parse_requirement_line,
    build_dependency_graph,
    validate_remediation
)
from backend.secuscan.models import Finding


def test_normalize_package_name():
    assert normalize_package_name("pydantic_settings") == "pydantic-settings"
    assert normalize_package_name("Flask-RESTful") == "flask-restful"
    assert normalize_package_name("  PyJWT  ") == "pyjwt"
    assert normalize_package_name("libssl.1.1") == "libssl-1-1"


def test_clean_version_string():
    assert clean_version_string("v1.2.3") == "1.2.3"
    assert clean_version_string("1.1.1f-1ubuntu2.23") == "1.1.1"
    assert clean_version_string("3.0.0-rc1") == "3.0.0"
    assert clean_version_string("invalid") == "invalid"


def test_parse_remediation_suggestion():
    res1 = parse_remediation_suggestion("Update framer-motion to version 11.0.0")
    assert res1 == ("framer-motion", "11.0.0")

    res2 = parse_remediation_suggestion("upgrade library-x to 2.4.1")
    assert res2 == ("library-x", "2.4.1")

    res3 = parse_remediation_suggestion("Apply secure controls")
    assert res3 is None


def test_semver_to_pep440():
    # Carets
    assert semver_to_pep440("^1.2.3") == SpecifierSet(">=1.2.3,<2.0.0")
    assert semver_to_pep440("^0.2.3") == SpecifierSet(">=0.2.3,<0.3.0")
    assert semver_to_pep440("^0.0.3") == SpecifierSet(">=0.0.3,<0.0.4")

    # Tildes
    assert semver_to_pep440("~1.2.3") == SpecifierSet(">=1.2.3,<1.3.0")
    assert semver_to_pep440("~1.2") == SpecifierSet(">=1.2.0,<1.3.0")

    # Wildcards
    assert semver_to_pep440("1.x") == SpecifierSet(">=1.0.0,<2.0.0")
    assert semver_to_pep440("1.*") == SpecifierSet(">=1.0.0,<2.0.0")
    assert semver_to_pep440("1.2.x") == SpecifierSet(">=1.2.0,<1.3.0")

    # Partial without wildcards
    assert semver_to_pep440("1.2") == SpecifierSet(">=1.2.0,<1.3.0")
    assert semver_to_pep440("1") == SpecifierSet(">=1.0.0,<2.0.0")

    # Operators & ranges
    assert semver_to_pep440(">=1.0.0 <2.0.0") == SpecifierSet(">=1.0.0,<2.0.0")
    assert semver_to_pep440("<=2.0.0") == SpecifierSet("<=2.0.0")

    # Exact and fallbacks
    assert semver_to_pep440("1.2.3") == SpecifierSet("==1.2.3")
    assert semver_to_pep440("*") == SpecifierSet("")


def test_parse_requirement_line():
    assert parse_requirement_line("fastapi>=0.115.0") == ("fastapi", SpecifierSet(">=0.115.0"))
    assert parse_requirement_line("cryptography>=42.0.0 ; extra == 'ssl'") == ("cryptography", SpecifierSet(">=42.0.0"))
    assert parse_requirement_line("  # commented line") is None
    assert parse_requirement_line("") is None


def test_parse_package_lock():
    lock_data = {
        "packages": {
            "": {
                "dependencies": {
                    "framer-motion": "^10.0.0"
                }
            },
            "node_modules/framer-motion": {
                "version": "10.16.4",
                "dependencies": {
                    "react": "^18.0.0"
                }
            }
        }
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "package-lock.json"
        with open(lock_file, "w") as f:
            json.dump(lock_data, f)

        relations = parse_package_lock(str(lock_file))
        assert "root" in relations
        assert relations["root"] == [("framer-motion", "^10.0.0")]
        assert "framer-motion" in relations
        assert relations["framer-motion"] == [("react", "^18.0.0")]


def test_parse_package_json():
    pkg_data = {
        "dependencies": {
            "express": "^4.17.1"
        },
        "devDependencies": {
            "jest": "^26.0.0"
        }
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        with open(pkg_file, "w") as f:
            json.dump(pkg_data, f)

        relations = parse_package_json(str(pkg_file))
        assert "root" in relations
        assert ("express", "^4.17.1") in relations["root"]
        assert ("jest", "^26.0.0") in relations["root"]


def test_validate_remediation_no_conflict():
    # If package not in graph, defaults to safe
    graph = {}
    res = validate_remediation("Update framer-motion to version 11.0.0", graph)
    assert res["safe_to_apply"] is True
    assert res["compatible_range"] is None
    assert len(res["alternatives"]) == 0


def test_validate_remediation_with_conflict():
    # Setup graph where root requires library-y, which transitively requires library-x <2.0
    graph = {
        "library-x": [
            {"parent": "library-y", "specifier": SpecifierSet("<2.0")}
        ]
    }

    # Suggest upgrade of library-x to 1.5.0 (compatible with <2.0)
    res_safe = validate_remediation("Update library-x to version 1.5.0", graph)
    assert res_safe["safe_to_apply"] is True

    # Suggest upgrade of library-x to 2.1.0 (conflicts with <2.0)
    res_unsafe = validate_remediation("Update library-x to version 2.1.0", graph)
    assert res_unsafe["safe_to_apply"] is False
    assert res_unsafe["compatible_range"] == "<2.0"
    assert len(res_unsafe["alternatives"]) > 0
    assert any("library-y" in alt for alt in res_unsafe["alternatives"])


def test_finding_model_safety_fields():
    finding = Finding(
        title="Outdated dependency",
        category="Dependency Vulnerability",
        severity="high",
        target="package.json",
        description="Vulnerability in library-x",
        safe_to_apply=False,
        compatible_range="<2.0",
        alternatives=["Upgrade library-y"]
    )
    assert finding.safe_to_apply is False
    assert finding.compatible_range == "<2.0"
    assert finding.alternatives == ["Upgrade library-y"]


def test_build_dependency_graph_fallback_disabled():
    """Verify that build_dependency_graph does not fall back to local manifests when target is invalid/nonexistent."""
    # 1. Non-existent directory
    graph_nonexistent = build_dependency_graph("nonexistent_directory_123")
    assert graph_nonexistent == {}

    # 2. URL/IP target
    graph_url = build_dependency_graph("http://example.com/api")
    assert graph_url == {}


def test_build_dependency_graph_python_transitive_mocked():
    """Test building dependency graph for Python requirements with mocked transitive dependencies."""
    from unittest.mock import patch

    req_content = "library-y>=1.0.0\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = Path(tmpdir) / "requirements.txt"
        with open(req_file, "w", encoding="utf-8") as f:
            f.write(req_content)

        # Mock get_python_transitive_dependencies to return a transitive dependency
        mock_transitive = [("library-x", SpecifierSet("<2.0"))]
        with patch("backend.secuscan.remediation.get_python_transitive_dependencies", return_value=mock_transitive):
            graph = build_dependency_graph(tmpdir)

        assert "library-y" in graph
        assert graph["library-y"] == [{"parent": "root", "specifier": SpecifierSet(">=1.0.0")}]

        assert "library-x" in graph
        assert graph["library-x"] == [{"parent": "library-y", "specifier": SpecifierSet("<2.0")}]
