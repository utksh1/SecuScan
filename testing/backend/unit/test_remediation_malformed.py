"""
Unit tests for validate_remediation with malformed structured inputs.

Covers crash-avoidance and safe graceful degradation on genuinely malformed
inputs that are not tested in test_remediation_safety.py.
"""

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from backend.secuscan.remediation import (
    clean_version_string,
    parse_remediation_suggestion,
    validate_remediation,
)


class TestValidateRemediationMalformedInputs:
    def test_none_remediation_str_raises_type_error(self):
        """None remediation_str raises TypeError (function expects a string)."""
        try:
            validate_remediation(None, {})
            assert False, "Expected TypeError"
        except TypeError as e:
            assert "string" in str(e).lower() or "NoneType" in str(e)

    def test_empty_string_remediation_str_returns_safe_default(self):
        """Empty string remediation_str returns safe default (no parse result)."""
        res = validate_remediation("", {})
        assert res["safe_to_apply"] is True
        assert res["compatible_range"] is None
        assert res["alternatives"] == []

    def test_none_graph_raises_type_error(self):
        """None graph raises TypeError (function expects a dict)."""
        try:
            validate_remediation("Update pkg to version 1.2.3", None)
            assert False, "Expected TypeError"
        except TypeError as e:
            assert "NoneType" in str(e)

    def test_empty_graph_returns_safe_default(self):
        """Empty graph should not raise and returns safe default."""
        res = validate_remediation("Update pkg to version 1.2.3", {})
        assert res["safe_to_apply"] is True

    def test_unparseable_version_returns_safe_default(self):
        """Unparseable version string in the remediation string returns safe default."""
        res = validate_remediation("Update pkg to version not-a-version", {})
        assert res["safe_to_apply"] is True

    def test_package_not_in_graph_returns_safe_default(self):
        """Package not in the dependency graph is treated as safe."""
        graph = {
            "other-pkg": [
                {"parent": "root", "specifier": SpecifierSet(">=1.0.0")}
            ]
        }
        res = validate_remediation("Update missing-pkg to version 2.0.0", graph)
        assert res["safe_to_apply"] is True

    def test_specifier_set_with_unparseable_constraint_raises(self):
        """SpecifierSet raises InvalidSpecifier for malformed constraint strings."""
        try:
            SpecifierSet("invalid-spec")
            assert False, "Expected InvalidSpecifier"
        except InvalidSpecifier:
            pass  # expected

    def test_validate_with_valid_specifier_in_graph(self):
        """Valid specifier in graph with compatible version is safe."""
        graph = {
            "pkg": [
                {"parent": "root", "specifier": SpecifierSet(">=1.0.0,<2.0.0")}
            ]
        }
        res = validate_remediation("Update pkg to version 1.5.0", graph)
        assert res["safe_to_apply"] is True

    def test_validate_with_valid_specifier_incompatible_version(self):
        """Valid specifier in graph with incompatible version marks unsafe."""
        graph = {
            "pkg": [
                {"parent": "root", "specifier": SpecifierSet("<2.0.0")}
            ]
        }
        res = validate_remediation("Update pkg to version 2.5.0", graph)
        assert res["safe_to_apply"] is False
        assert "2.0.0" in res["compatible_range"]


class TestCleanVersionStringMalformed:
    def test_clean_version_string_with_prerelease_suffix(self):
        """Version strings with prerelease suffixes are truncated to base version."""
        assert clean_version_string("1.2.3-alpha") == "1.2.3"
        assert clean_version_string("2.0.0-beta1") == "2.0.0"
        assert clean_version_string("3.1.4-rc.2") == "3.1.4"

    def test_clean_version_string_with_build_metadata(self):
        """Version strings with build metadata (+build) strip the build part."""
        assert clean_version_string("1.0.0+build.123") == "1.0.0"

    def test_clean_version_string_with_git_hash(self):
        """Version strings with git hashes strip the hash."""
        assert clean_version_string("1.2.3-d6b8f9a") == "1.2.3"


class TestParseRemediationSuggestionEdgeCases:
    def test_package_name_with_underscore(self):
        """Package names with underscores are normalised correctly."""
        res = parse_remediation_suggestion("Update my_pkg_name to version 1.0.0")
        assert res is not None
        pkg, ver = res
        assert ver == "1.0.0"

    def test_version_with_v_prefix(self):
        """Version strings with 'v' prefix are parsed."""
        res = parse_remediation_suggestion("Update react to version v18.0.0")
        assert res is not None
        pkg, ver = res
        assert ver == "v18.0.0"

    def test_no_version_phrase(self):
        """Remediation strings without a version phrase return None."""
        assert parse_remediation_suggestion("Downgrade the library") is None
        assert parse_remediation_suggestion("Remove package completely") is None
