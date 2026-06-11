import asyncio
import importlib.util
from pathlib import Path

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager


PLUGIN_ID = "waf-detection"
PLUGIN_DIR = Path(settings.plugins_dir) / PLUGIN_ID


def _load_waf_parser():
    parser_path = PLUGIN_DIR / "parser.py"
    spec = importlib.util.spec_from_file_location("waf_detection_parser", parser_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_waf_detection_metadata_loads_through_plugin_manager(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin("waf-detection")

    assert plugin is not None
    assert plugin.id == "waf-detection"
    assert plugin.name == "WAF Detector"
    assert plugin.output["parser"] == "custom"


def test_waf_detection_command_renders_target_url(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        PLUGIN_ID,
        {
            "target": "https://example.com",
        },
    )

    assert command == ["wafw00f", "https://example.com"]


def test_waf_detection_parser_normalizes_detected_waf_output():
    parser = _load_waf_parser()

    result = parser.parse(
        "\n".join(
            [
                "Checking https://example.com",
                "The site https://example.com is behind Cloudflare WAF.",
                "WAF detected: Cloudflare",
            ]
        )
    )

    assert result["count"] == 3
    assert len(result["findings"]) == 3
    assert result["items"] == [
        "Checking https://example.com",
        "The site https://example.com is behind Cloudflare WAF.",
        "WAF detected: Cloudflare",
    ]

    detected = result["findings"][-1]
    assert detected["title"] == "WAF Detector Observation"
    assert detected["category"] == "Recon"
    assert detected["severity"] == "low"
    assert detected["description"] == "WAF detected: Cloudflare"
    assert detected["metadata"] == {"raw_line": "WAF detected: Cloudflare"}


def test_waf_detection_parser_keeps_non_detection_lines_info_severity():
    parser = _load_waf_parser()

    result = parser.parse("Checking https://example.com")

    assert result["count"] == 1
    assert result["findings"][0]["severity"] == "info"
    assert result["findings"][0]["metadata"]["raw_line"] == "Checking https://example.com"


def test_waf_detection_parser_ignores_blank_lines_and_caps_fixture_size():
    parser = _load_waf_parser()

    output = "\n".join(["", "WAF detected: Cloudflare", "   "] + [f"line {i}" for i in range(250)])
    result = parser.parse(output)

    assert result["count"] == 200
    assert len(result["findings"]) == 200
    assert result["items"][0] == "WAF detected: Cloudflare"
    assert result["items"][-1] == "line 198"