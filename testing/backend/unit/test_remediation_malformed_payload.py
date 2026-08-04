"""
Regression tests for malformed structured remediation inputs — Issue #2157.

Verifies that the safety layer (validate_remediation and supporting functions)
returns a controlled, predictable result for every malformed payload variant
rather than raising an unhandled exception.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from packaging.specifiers import SpecifierSet

from backend.secuscan.remediation import (
    build_dependency_graph,
    clean_version_string,
    normalize_package_name,
    parse_package_json,
    parse_package_lock,
    parse_remediation_suggestion,
    parse_requirement_line,
    semver_to_pep440,
    validate_remediation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFE_RESULT_KEYS = {"safe_to_apply", "compatible_range", "alternatives"}


def _assert_controlled_result(result: dict) -> None:
    """Assert the safety layer always returns the canonical controlled shape."""
    assert isinstance(result, dict), "Result must be a dict"
    assert _SAFE_RESULT_KEYS == set(result.keys()), f"Unexpected keys: {result.keys()}"
    assert isinstance(result["safe_to_apply"], bool), "'safe_to_apply' must be bool"
    assert result["compatible_range"] is None or isinstance(
        result["compatible_range"], str
    ), "'compatible_range' must be str or None"
    assert isinstance(result["alternatives"], list), "'alternatives' must be a list"


# ===========================================================================
# 1. Malformed remediation strings — parse_remediation_suggestion
# ===========================================================================


class TestParseRemediationSuggestionMalformed:
    """parse_remediation_suggestion must never raise; always returns None or a tuple."""

    @pytest.mark.parametrize(
        "bad_input",
        [
            "",
            "   ",
            "NoneType",
            "\x00\x01\x02\x03",
            "\n\n\n\n",
            "!" * 10_000,
            "Update to version",
            "upgrade  to 1.0.0",
            "Update pkg",
            "update 1.2.3 to pkg",
            "<script>alert(1)</script>",
            "UPDATE PACKAGE TO VERSION 9.9.9",
            "update pkg-x to version",
            "update to version 1.0.0",
            "upgrade pkg@1.0.0 to version 2.0.0",
        ],
    )
    def test_does_not_raise(self, bad_input: str) -> None:
        result = parse_remediation_suggestion(bad_input)
        assert result is None or (
            isinstance(result, tuple) and len(result) == 2
        ), f"Unexpected return type for input {bad_input!r}: {result!r}"

    def test_empty_string_returns_none(self) -> None:
        assert parse_remediation_suggestion("") is None

    def test_only_whitespace_returns_none(self) -> None:
        assert parse_remediation_suggestion("   \t\n") is None

    def test_null_bytes_returns_none(self) -> None:
        assert parse_remediation_suggestion("\x00pkg\x00 to version 1.0") is None

    def test_huge_input_does_not_hang(self) -> None:
        huge = "x" * 100_000
        result = parse_remediation_suggestion(huge)
        assert result is None

    def test_uppercase_keywords_matched(self) -> None:
        result = parse_remediation_suggestion("UPDATE lib-x TO VERSION 3.0.0")
        assert result == ("lib-x", "3.0.0")


# ===========================================================================
# 2. validate_remediation — malformed graph structures
# ===========================================================================


class TestValidateRemediationMalformedGraph:
    """validate_remediation must return a controlled result for any graph shape."""

    def test_empty_graph_is_safe(self) -> None:
        result = validate_remediation("Update pkg to version 1.0.0", {})
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True

    def test_graph_missing_specifier_key(self) -> None:
        """Graph entry without 'specifier' key must not raise KeyError."""
        graph = {"pkg": [{"parent": "root"}]}
        result = validate_remediation("Update pkg to version 1.0.0", graph)
        _assert_controlled_result(result)

    def test_graph_entry_is_empty_list(self) -> None:
        """Package in graph with no constraints is still considered safe."""
        graph = {"pkg": []}
        result = validate_remediation("Update pkg to version 99.0.0", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True

    def test_completely_malformed_remediation_string(self) -> None:
        """Unparseable remediation string returns controlled safe fallback."""
        graph = {"pkg": [{"parent": "root", "specifier": SpecifierSet(">=1.0.0")}]}
        result = validate_remediation("!!!INVALID INPUT!!!", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True

    def test_version_with_unparseable_suffix(self) -> None:
        """Version strings with garbage suffixes fall back gracefully."""
        graph = {"lib": [{"parent": "root", "specifier": SpecifierSet(">=1.0.0,<2.0.0")}]}
        result = validate_remediation("Update lib to version 1.5.0-SNAPSHOT", graph)
        _assert_controlled_result(result)

    def test_zero_length_package_name_after_normalise(self) -> None:
        """A remediation where the normalized name maps to only separators must not crash."""
        result = validate_remediation("Update --- to version 1.0.0", {})
        _assert_controlled_result(result)

    def test_non_string_remediation_input(self) -> None:
        """Passing non-string remediation values must not raise unhandled."""
        for bad in (None, 42, [], {}):
            try:
                result = validate_remediation(bad, {})  # type: ignore[arg-type]
                _assert_controlled_result(result)
            except (TypeError, AttributeError):
                pytest.fail(
                    f"validate_remediation raised on bad input type {type(bad)} — "
                    "the safety layer must be defensive."
                )

    def test_deeply_nested_conflicting_constraints(self) -> None:
        """Multiple layers of conflicting constraints produce a sane result."""
        graph = {
            "lib-x": [
                {"parent": "root", "specifier": SpecifierSet(">=1.0.0,<2.0.0")},
                {"parent": "lib-a", "specifier": SpecifierSet(">=1.5.0,<1.9.0")},
                {"parent": "lib-b", "specifier": SpecifierSet("<1.8.0")},
            ]
        }
        result = validate_remediation("Update lib-x to version 2.0.0", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is False
        assert result["compatible_range"] is not None
        assert len(result["alternatives"]) > 0

    def test_alternatives_list_contains_strings_only(self) -> None:
        """All entries in 'alternatives' must be plain strings."""
        graph = {"lib": [{"parent": "root", "specifier": SpecifierSet("<1.0.0")}]}
        result = validate_remediation("Update lib to version 2.0.0", graph)
        _assert_controlled_result(result)
        assert all(isinstance(a, str) for a in result["alternatives"])

    def test_empty_specifier_allows_any_version(self) -> None:
        """An empty SpecifierSet allows all versions, so upgrade should be safe."""
        graph = {
            "pkg": [
                {"parent": "root", "specifier": SpecifierSet("")},
            ]
        }
        result = validate_remediation("Update pkg to version 99.0.0", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True


# ===========================================================================
# 3. Malformed file payloads — parse_package_lock / parse_package_json
# ===========================================================================


class TestMalformedFileParsing:
    """File parsers must return {} instead of raising on bad content."""

    def test_package_lock_not_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package-lock.json"
            bad_file.write_text("NOT JSON {{{{ !!!", encoding="utf-8")
            assert parse_package_lock(str(bad_file)) == {}

    def test_package_lock_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package-lock.json"
            bad_file.write_text("", encoding="utf-8")
            assert parse_package_lock(str(bad_file)) == {}

    def test_package_lock_json_array_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package-lock.json"
            bad_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            result = parse_package_lock(str(bad_file))
            assert isinstance(result, dict)

    def test_package_lock_packages_value_not_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package-lock.json"
            bad_file.write_text(json.dumps({"packages": "not-a-dict"}), encoding="utf-8")
            result = parse_package_lock(str(bad_file))
            assert isinstance(result, dict)

    def test_package_lock_nonexistent_path(self) -> None:
        result = parse_package_lock("/nonexistent/path/package-lock.json")
        assert result == {}

    def test_package_json_not_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package.json"
            bad_file.write_text("<html>not json</html>", encoding="utf-8")
            assert parse_package_json(str(bad_file)) == {}

    def test_package_json_null_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package.json"
            bad_file.write_text(json.dumps(None), encoding="utf-8")
            result = parse_package_json(str(bad_file))
            assert isinstance(result, dict)

    def test_package_json_dependencies_not_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "package.json"
            bad_file.write_text(json.dumps({"dependencies": ["list-not-dict"]}), encoding="utf-8")
            result = parse_package_json(str(bad_file))
            assert isinstance(result, dict)

    def test_package_json_nonexistent_path(self) -> None:
        result = parse_package_json("/nonexistent/path/package.json")
        assert result == {}


# ===========================================================================
# 4. Malformed requirement lines — parse_requirement_line
# ===========================================================================


class TestParseRequirementLineMalformed:
    @pytest.mark.parametrize(
        "line",
        [
            "",
            "   ",
            "# comment line",
            "-r other-requirements.txt",
            "--index-url https://example.com",
            "\x00bad\x00line",
            "===invalid===specifier===",
            "pkg_with_bad_spec @@@ 1.0",
        ],
    )
    def test_does_not_raise(self, line: str) -> None:
        result = parse_requirement_line(line)
        assert result is None or (
            isinstance(result, tuple)
            and len(result) == 2
            and isinstance(result[0], str)
            and isinstance(result[1], SpecifierSet)
        ), f"Unexpected result for {line!r}: {result!r}"


# ===========================================================================
# 5. Malformed semver strings — semver_to_pep440
# ===========================================================================


class TestSemverToPep440Malformed:
    @pytest.mark.parametrize(
        "bad_semver",
        [
            "",
            "   ",
            "NOT_SEMVER",
            "^^^^",
            "~~~~",
            "1.2.3.4.5.6.7",
            ">=",
            "<",
            "abc.def.ghi",
            "^",
            "~",
            "1.2.3 || 4.5.6",
            "\x00\x01",
        ],
    )
    def test_returns_specifier_set(self, bad_semver: str) -> None:
        result = semver_to_pep440(bad_semver)
        assert isinstance(result, SpecifierSet), (
            f"semver_to_pep440({bad_semver!r}) must return SpecifierSet, " f"got {type(result)}"
        )


# ===========================================================================
# 6. build_dependency_graph with malformed manifests
# ===========================================================================


class TestBuildDependencyGraphMalformed:
    def test_empty_target_string(self) -> None:
        result = build_dependency_graph("")
        assert result == {}

    def test_target_is_a_file_not_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            some_file = Path(tmpdir) / "notadir.txt"
            some_file.write_text("hello", encoding="utf-8")
            result = build_dependency_graph(str(some_file))
            assert isinstance(result, dict)

    def test_requirements_txt_with_null_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            req = Path(tmpdir) / "requirements.txt"
            req.write_bytes(b"\x00\x00\x00\x00bad content\x00")
            result = build_dependency_graph(tmpdir)
            assert isinstance(result, dict)

    def test_package_lock_with_corrupt_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = Path(tmpdir) / "package-lock.json"
            lock.write_text("{corrupt json", encoding="utf-8")
            result = build_dependency_graph(tmpdir)
            assert result == {}

    def test_graph_build_mocked_transitive_error(self) -> None:
        """If get_python_transitive_dependencies raises, graph build must continue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req = Path(tmpdir) / "requirements.txt"
            req.write_text("requests>=2.0.0\n", encoding="utf-8")

            with patch(
                "backend.secuscan.remediation.get_python_transitive_dependencies",
                side_effect=RuntimeError("transitive lookup failed"),
            ):
                result = build_dependency_graph(tmpdir)

            assert isinstance(result, dict)


# ===========================================================================
# 7. normalize_package_name and clean_version_string edge cases
# ===========================================================================


class TestNormalisationEdgeCases:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("", ""),
            ("---", "-"),
            ("_._._ ", "-"),
            ("A__B--C..D", "a-b-c-d"),
            ("PyPy3", "pypy3"),
        ],
    )
    def test_normalize_package_name(self, name: str, expected: str) -> None:
        assert normalize_package_name(name) == expected

    @pytest.mark.parametrize(
        "ver,expected",
        [
            ("", ""),
            ("v", ""),
            ("vv1.0.0", "v1.0.0"),  # only the leading 'v' is stripped, leaving 'v1.0.0'
            ("1.2.3-ubuntu+build", "1.2.3"),
            ("0.0.0", "0.0.0"),
            ("999.999.999", "999.999.999"),
        ],
    )
    def test_clean_version_string(self, ver: str, expected: str) -> None:
        assert clean_version_string(ver) == expected


# ===========================================================================
# 8. End-to-end: malformed payload through the full safety pipeline
# ===========================================================================


class TestEndToEndMalformedPayload:
    """Integration-style checks exercising validate_remediation end-to-end
    with realistic but structurally broken inputs."""

    def test_remediation_with_only_special_chars(self) -> None:
        graph = {"pkg": [{"parent": "root", "specifier": SpecifierSet(">=1.0.0")}]}
        result = validate_remediation("@#$%^&*()", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True

    def test_remediation_with_unicode_noise(self) -> None:
        graph = {"pkg": [{"parent": "root", "specifier": SpecifierSet(">=1.0.0")}]}
        result = validate_remediation("Update p\u00e0c\u03ba\u00e5ge to version 1.0.0", graph)
        _assert_controlled_result(result)

    def test_remediation_with_valid_string_but_unknown_package(self) -> None:
        graph = {"known-pkg": [{"parent": "root", "specifier": SpecifierSet(">=1.0.0")}]}
        result = validate_remediation("Update unknown-pkg to version 2.0.0", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True

    def test_remediation_conflict_produces_actionable_alternatives(self) -> None:
        graph = {
            "vuln-lib": [
                {"parent": "root", "specifier": SpecifierSet(">=1.0.0,<2.0.0")},
                {"parent": "middleware", "specifier": SpecifierSet(">=1.2.0,<1.5.0")},
            ]
        }
        result = validate_remediation("Update vuln-lib to version 3.0.0", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is False
        assert result["compatible_range"] is not None and result["compatible_range"] != ""
        combined = " ".join(result["alternatives"])
        assert "middleware" in combined or "root" in combined or "vuln-lib" in combined

    def test_safe_upgrade_within_constraint_window(self) -> None:
        graph = {
            "dep": [
                {"parent": "root", "specifier": SpecifierSet(">=1.0.0,<3.0.0")},
            ]
        }
        result = validate_remediation("Update dep to version 2.5.0", graph)
        _assert_controlled_result(result)
        assert result["safe_to_apply"] is True
        assert result["compatible_range"] is None
        assert result["alternatives"] == []

    def test_result_is_always_deterministic(self) -> None:
        """Calling validate_remediation twice with the same input returns equal dicts."""
        graph = {"lib": [{"parent": "root", "specifier": SpecifierSet(">=1.0.0,<2.0.0")}]}
        r1 = validate_remediation("Update lib to version 3.0.0", graph)
        r2 = validate_remediation("Update lib to version 3.0.0", graph)
        assert r1 == r2
