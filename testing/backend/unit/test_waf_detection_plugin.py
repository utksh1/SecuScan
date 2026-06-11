import asyncio
import importlib.util
from pathlib import Path

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager

PLUGIN_ID_CANDIDATES = ("waf-detection", "waf_detector")


def _find_plugin_dir() -> Path:
    for plugin_id in PLUGIN_ID_CANDIDATES:
        plugin_dir = Path(settings.plugins_dir) / plugin_id
        if (plugin_dir / "parser.py").exists():
            return plugin_dir

    raise AssertionError("WAF detection plugin parser not found")


def _load_waf_parser():
    parser_path = _find_plugin_dir() / "parser.py"

    spec = importlib.util.spec_from_file_location(
        "waf_detection_parser",
        parser_path,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def _get_waf_plugin(manager: PluginManager):
    for plugin_id in PLUGIN_ID_CANDIDATES:
        plugin = manager.get_plugin(plugin_id)
        if plugin is not None:
            return plugin_id, plugin

    return None, None


def _get_parser_name(plugin):
    output = plugin.output

    if isinstance(output, dict):
        return output.get("parser")

    return getattr(output, "parser", None)


def test_waf_detection_metadata_loads_through_plugin_manager(
    setup_test_environment,
):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugin_id, plugin = _get_waf_plugin(manager)

    assert plugin is not None
    assert plugin_id is not None
    assert "waf" in plugin.name.lower()
    assert _get_parser_name(plugin) == "custom"


def test_waf_detection_command_renders_target_url(
    setup_test_environment,
):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugin_id, plugin = _get_waf_plugin(manager)

    assert plugin is not None

    command = manager.build_command(
        plugin_id,
        {
            "target": "https://example.com",
        },
    )

    assert command is not None
    assert "wafw00f" in command
    assert "https://example.com" in command


def test_waf_detection_parser_normalizes_detected_waf_output():
    parser = _load_waf_parser()

    result = parser.parse(
        "\n".join(
            [
                "Checking https://example.com",
                "The site is behind Cloudflare",
                "WAF detected: Cloudflare",
            ]
        )
    )

    assert result["count"] >= 1
    assert len(result["findings"]) > 0

    descriptions = " ".join(
        finding["description"]
        for finding in result["findings"]
    )

    assert "Cloudflare" in descriptions

    finding = next(
        item
        for item in result["findings"]
        if "Cloudflare" in item["description"]
    )

    assert finding["title"]
    assert finding["category"]
    assert finding["severity"] in {
        "info",
        "low",
        "medium",
        "high",
        "critical",
    }
    assert finding["metadata"]
    assert "Cloudflare" in str(finding["metadata"])


def test_waf_detection_parser_keeps_non_detection_lines_info_severity():
    parser = _load_waf_parser()

    result = parser.parse("Checking https://example.com")

    assert result["count"] >= 1
    assert result["findings"][0]["severity"] == "info"
    assert result["findings"][0]["metadata"]


def test_waf_detection_parser_ignores_blank_lines_with_stable_fixture():
    parser = _load_waf_parser()

    output = "\n".join(
        [
            "",
            "WAF detected: Cloudflare",
            "   ",
            "line 1",
            "line 2",
        ]
    )

    result = parser.parse(output)

    assert result["count"] >= 3
    assert len(result["findings"]) >= 3

    descriptions = " ".join(
        finding["description"]
        for finding in result["findings"]
    )

    assert "Cloudflare" in descriptions
    assert "line 1" in descriptions
    assert "line 2" in descriptions