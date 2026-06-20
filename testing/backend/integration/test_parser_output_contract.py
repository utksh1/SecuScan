import os
import sys
import json
import importlib.util
from pathlib import Path
import pytest
import asyncio

from backend.secuscan.capabilities import effective_capabilities
from backend.secuscan.config import settings
from backend.secuscan.plugins import init_plugins
from backend.secuscan.executor import executor


# ---------------------------------------------------------------------------
# Dynamic Discovery of All Bundled Custom Parsers
# ---------------------------------------------------------------------------

KNOWN_PARSER_CAPABILITY_GROUPS = frozenset(
    {"network", "intrusive", "credentials", "exploit"}
)
SELECTED_PARSER_CAPABILITY_GROUP = (
    os.getenv("PARSER_CAPABILITY_GROUP", "").strip().lower()
)
if (
    SELECTED_PARSER_CAPABILITY_GROUP
    and SELECTED_PARSER_CAPABILITY_GROUP not in KNOWN_PARSER_CAPABILITY_GROUPS
):
    raise RuntimeError(
        f"Unsupported parser capability group '{SELECTED_PARSER_CAPABILITY_GROUP}'."
        f"Valid groups: {sorted(KNOWN_PARSER_CAPABILITY_GROUPS)}"
    )


def get_all_custom_parsers() -> list[tuple[str, Path, Path]]:
    """
    Scans the plugins directory to discover all bundled scanners
    that define both `metadata.json` and a custom `parser.py`.
    """
    plugins_dir = Path(settings.plugins_dir)
    if not plugins_dir.exists():
        return []

    parsers = []
    for p_dir in plugins_dir.iterdir():
        if p_dir.is_dir():
            parser_file = p_dir / "parser.py"
            metadata_file = p_dir / "metadata.json"
            if parser_file.exists() and metadata_file.exists():
                parsers.append((p_dir.name, parser_file, metadata_file))

    # Sort for deterministic test execution ordering
    return sorted(parsers, key=lambda x: x[0])


def get_parser_capability_group(metadata_path: Path) -> str:
    """Return the highest-consequence capability group for CI grouping."""
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    caps = data.get("capabilities")
    if caps is None:
        safety_level = data.get("safety", {}).get("level", "safe")
        caps = list(
            effective_capabilities(None, safety_level, data.get("id", "unknown"))
        )

    if "exploit" in caps:
        return "exploit"
    # if "docker" in caps:
    #     return "docker"
    if "credentials" in caps:
        return "credentials"
    if "intrusive" in caps:
        return "intrusive"
    return "network"


def get_selected_custom_parsers() -> list[tuple[str, Path, Path]]:
    """Return plugin parsers filtered by the requested capability group."""
    if not SELECTED_PARSER_CAPABILITY_GROUP:
        return get_all_custom_parsers()

    selected = [
        item
        for item in get_all_custom_parsers()
        if get_parser_capability_group(item[2]) == SELECTED_PARSER_CAPABILITY_GROUP
    ]

    if not selected:
        raise RuntimeError(
            f"No parser contracts found for capability group '{SELECTED_PARSER_CAPABILITY_GROUP}'. "
            "Verify that the group name is correct and that plugin metadata declares the expected capabilities."
        )

    return selected


def test_parser_capability_groups_are_populated() -> None:
    """Ensure known CI capability groups map to at least one parser plugin."""
    groups = {
        get_parser_capability_group(metadata_path)
        for _, _, metadata_path in get_all_custom_parsers()
    }
    missing = KNOWN_PARSER_CAPABILITY_GROUPS - groups
    assert not missing, (
        "The parser capability matrix contains groups with no matching plugins: "
        f"{sorted(missing)}. "
        "Update KNOWN_PARSER_CAPABILITY_GROUPS or plugin metadata capabilities accordingly."
    )


# ---------------------------------------------------------------------------
# Module Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def plugin_manager_instance():
    """Initializes and loads the global plugin manager for tests."""
    return asyncio.run(init_plugins(settings.plugins_dir))


# ---------------------------------------------------------------------------
# Parser Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "plugin_id, parser_path, metadata_path", get_selected_custom_parsers()
)
def test_parser_contract_compliance(
    plugin_id, parser_path, metadata_path, plugin_manager_instance
):
    """
    Verifies that every custom parser in the codebase complies with
    the required parse entrypoint signature and normalization contracts.
    """
    # 1. Assert the custom parser.py file is dynamically importable
    spec = importlib.util.spec_from_file_location(f"parser_{plugin_id}", parser_path)
    assert (
        spec is not None
    ), f"Failed to create module spec for custom parser: {plugin_id}"

    loader = spec.loader
    assert (
        loader is not None
    ), f"Failed to load module loader for custom parser: {plugin_id}"

    module = importlib.util.module_from_spec(spec)
    try:
        loader.exec_module(module)
    except Exception as exc:
        pytest.fail(
            f"Subprocess import crashed while executing module {plugin_id}: {exc}"
        )

    # 2. Assert 'parse' entrypoint exists and is callable
    assert hasattr(
        module, "parse"
    ), f"Parser for '{plugin_id}' is missing the required 'parse' function"
    assert callable(
        module.parse
    ), f"The 'parse' attribute in '{plugin_id}' custom parser is not a callable function"

    # 3. Retrieve plugin metadata
    plugin = plugin_manager_instance.get_plugin(plugin_id)
    assert (
        plugin is not None
    ), f"Plugin metadata not found in plugin manager for ID: {plugin_id}"

    # 4. Verify Normalization Contract - Empty shapes
    res_empty = executor._normalize_parsed_result(plugin, "", {})
    assert "findings" in res_empty, "Normalized result is missing 'findings' array"
    assert isinstance(
        res_empty["findings"], list
    ), "findings must be represented as a list"
    assert res_empty["count"] == 0, "Empty parser inputs must result in 0 count"

    # 5. Verify Normalization Contract - Malformed shapes (resilience test)
    malformed_finding = {"unrelated_field": "some_value"}
    res_malformed = executor._normalize_parsed_result(
        plugin, "", {"findings": [malformed_finding]}
    )
    assert len(res_malformed["findings"]) == 1

    finding = res_malformed["findings"][0]
    assert (
        finding["title"] == "Security Finding"
    ), "Malformed finding must fall back to default title"
    assert (
        finding["severity"] == "info"
    ), "Malformed finding severity must default to 'info'"
    assert (
        finding["category"] == str(plugin.category).title()
    ), "Malformed finding category must match capitalized plugin category"
    assert (
        finding["description"] == "Security Finding"
    ), "Malformed finding description must fall back to default"
    assert (
        finding["remediation"] == ""
    ), "Malformed finding remediation must fall back to empty string"
    assert (
        finding["metadata"] == {}
    ), "Malformed finding metadata must default to empty dictionary"

    # 6. Verify Normalization Contract - Valid Severity Mappings
    severities_test = [
        ("CRITICAL", "critical"),
        ("HIGH", "high"),
        ("MEDIUM", "medium"),
        ("moderate", "medium"),
        ("WARNING", "medium"),
        ("LOW", "low"),
        ("INFO", "info"),
        ("informational", "info"),
        ("error", "high"),
    ]
    for raw_sev, expected_sev in severities_test:
        test_finding = {"title": "Test Title", "severity": raw_sev}
        res = executor._normalize_parsed_result(
            plugin, "", {"findings": [test_finding]}
        )
        assert (
            res["findings"][0]["severity"] == expected_sev
        ), f"Failed mapping '{raw_sev}' to '{expected_sev}'"

    # 7. Verify Normalization Contract - Unsafe / Unknown Severities (Negative test case)
    unknown_sevs = ["critical-critical", "severe", "malicious", None, 999, ""]
    for raw_sev in unknown_sevs:
        test_finding = {"title": "Test Title", "severity": raw_sev}
        res = executor._normalize_parsed_result(
            plugin, "", {"findings": [test_finding]}
        )
        assert (
            res["findings"][0]["severity"] == "info"
        ), f"Expected unknown severity '{raw_sev}' to default safely to 'info'"

    # 8. Verify Normalization Contract - Non-dictionary findings (Negative test case)
    invalid_findings = ["string_instead_of_dict", 1234, ["list_instead_of_dict"]]
    res_invalid = executor._normalize_parsed_result(
        plugin, "", {"findings": invalid_findings}
    )
    assert (
        len(res_invalid["findings"]) == 0
    ), "Non-dictionary findings in findings list must be strictly filtered out"
