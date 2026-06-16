import asyncio
import importlib.util
from pathlib import Path

from backend.secuscan.config import settings
from backend.secuscan.plugins import PluginManager

PLUGIN_ID = "url-fuzzer-2"
PLUGIN_DIR = Path(settings.plugins_dir) / PLUGIN_ID


def _load_url_fuzzer_parser():
    parser_path = PLUGIN_DIR / "parser.py"

    spec = importlib.util.spec_from_file_location(
        "url_fuzzer_2_parser",
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


def test_url_fuzzer_2_metadata_loads_through_plugin_manager(
    setup_test_environment,
):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    plugin = manager.get_plugin(PLUGIN_ID)

    assert plugin is not None
    assert plugin.id == PLUGIN_ID
    assert plugin.name == "URL Fuzzer"
    assert plugin.category == "recon"
    assert _get_parser_name(plugin) == "custom"


def test_url_fuzzer_2_command_renders_target_and_wordlist(
    setup_test_environment,
):
    manager = PluginManager(settings.plugins_dir)
    asyncio.run(manager.load_plugins())

    command = manager.build_command(
        PLUGIN_ID,
        {
            "target": "https://example.com",
            "wordlist": "wordlists/paths.txt",
        },
    )

    assert command == [
        "ffuf",
        "-u",
        "https://example.com/FUZZ",
        "-w",
        "wordlists/paths.txt",
        "-mc",
        "200,204,301,302,307,401,403",
        "-s",
    ]


def test_url_fuzzer_2_parser_normalizes_discovered_paths():
    parser = _load_url_fuzzer_parser()

    result = parser.parse(
        "\n".join(
            [
                "admin found [Status: 200]",
                "login [Status: 301]",
                "assets/app.js [Status: 200]",
            ]
        )
    )

    assert result["count"] == 3
    assert len(result["findings"]) == 3
    assert result["items"] == [
        "admin found [Status: 200]",
        "login [Status: 301]",
        "assets/app.js [Status: 200]",
    ]

    finding = result["findings"][0]

    assert finding["title"] == "URL Fuzzer Observation"
    assert finding["category"] == "Recon"
    assert finding["severity"] == "low"
    assert finding["description"] == "admin found [Status: 200]"
    assert finding["metadata"] == {
        "raw_line": "admin found [Status: 200]",
    }


def test_url_fuzzer_2_parser_keeps_regular_paths_info_severity():
    parser = _load_url_fuzzer_parser()

    result = parser.parse("assets/app.js [Status: 200]")

    assert result["count"] == 1
    assert result["findings"][0]["severity"] == "info"
    assert result["findings"][0]["metadata"] == {
        "raw_line": "assets/app.js [Status: 200]",
    }


def test_url_fuzzer_2_parser_ignores_blank_lines_and_caps_output():
    parser = _load_url_fuzzer_parser()

    output = "\n".join(
        ["", "admin found [Status: 200]", "   "]
        + [f"path-{index} [Status: 200]" for index in range(250)]
    )

    result = parser.parse(output)

    assert result["count"] == 200
    assert len(result["findings"]) == 200
    assert result["items"][0] == "admin found [Status: 200]"
    assert result["items"][-1] == "path-198 [Status: 200]"