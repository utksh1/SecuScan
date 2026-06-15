import asyncio
import importlib.util
from pathlib import Path

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "urlfinder"
PLUGIN_DIR = Path(settings.plugins_dir) / PLUGIN_ID


def _load_urlfinder_parser():
    parser_path = PLUGIN_DIR / "parser.py"

    spec = importlib.util.spec_from_file_location(
        "urlfinder_parser",
        parser_path,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def _get_parser_name(plugin):
    output = plugin.output

    if isinstance(output, dict):
        return output.get("parser")

    return getattr(output, "parser", None)


def test_urlfinder_metadata_loads_through_plugin_manager(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "urlfinder"
    assert plugin.category == "recon"
    assert _get_parser_name(plugin) == "custom"


def test_urlfinder_command_renders_domain_target(setup_test_environment):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        PLUGIN_ID,
        {
            "target": "example.com",
        },
    )

    assert command == [
        "urlfinder",
        "-d",
        "example.com",
        "-silent",
    ]


def test_urlfinder_parser_normalizes_discovered_urls():
    parser = _load_urlfinder_parser()

    result = parser.parse(
        "\n".join(
            [
                "https://example.com/",
                "https://example.com/login",
                "https://example.com/open-api",
            ]
        )
    )

    assert result["count"] == 3
    assert len(result["findings"]) == 3
    assert result["items"] == [
        "https://example.com/",
        "https://example.com/login",
        "https://example.com/open-api",
    ]

    finding = result["findings"][2]

    assert finding["title"] == "urlfinder Observation"
    assert finding["category"] == "Recon"
    assert finding["severity"] == "low"
    assert finding["description"] == "https://example.com/open-api"
    assert finding["metadata"] == {
        "raw_line": "https://example.com/open-api",
    }


def test_urlfinder_parser_keeps_normal_urls_info_severity():
    parser = _load_urlfinder_parser()

    result = parser.parse("https://example.com/about")

    assert result["count"] == 1
    assert result["findings"][0]["severity"] == "info"
    assert result["findings"][0]["metadata"] == {
        "raw_line": "https://example.com/about",
    }


def test_urlfinder_parser_ignores_blank_lines_and_caps_output():
    parser = _load_urlfinder_parser()

    output = "\n".join(
        ["", "https://example.com/first", "   "]
        + [f"https://example.com/page-{index}" for index in range(250)]
    )

    result = parser.parse(output)

    assert result["count"] == 200
    assert len(result["findings"]) == 200
    assert result["items"][0] == "https://example.com/first"
    assert result["items"][-1] == "https://example.com/page-198"