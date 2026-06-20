import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.plugin_health_dashboard import (
    discover_plugins,
    build_report,
    format_markdown,
)


def test_discover_plugins_uses_metadata_and_parser_directories(tmp_path):
    plugin_dir = tmp_path / "plugins" / "network" / "demo_plugin"
    plugin_dir.mkdir(parents=True)

    metadata = {
        "name": "demo_plugin",
        "category": "network",
        "description": "Demo plugin",
    }

    (plugin_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (plugin_dir / "parser.py").write_text("def parse(): pass", encoding="utf-8")

    plugins = discover_plugins(tmp_path / "plugins")

    assert len(plugins) == 1
    assert plugins[0]["name"] == "demo_plugin"
    assert plugins[0]["category"] == "network"
    assert plugins[0]["has_parser"] is True
    assert plugins[0]["has_metadata"] is True


def test_build_report_counts_parser_coverage():
    plugins = [
        {"name": "plugin_one", "category": "network", "has_parser": True},
        {"name": "plugin_two", "category": "web", "has_parser": False},
    ]

    report = build_report(plugins)

    assert report["summary"]["total_plugins"] == 2
    assert report["summary"]["plugins_with_parser"] == 1
    assert report["summary"]["plugins_without_parser"] == 1
    assert report["categories"]["network"] == 1
    assert report["categories"]["web"] == 1


def test_format_markdown_contains_plugin_details():
    report = {
        "summary": {
            "total_plugins": 1,
            "plugins_with_parser": 1,
            "plugins_without_parser": 0,
        },
        "categories": {"network": 1},
        "plugins": [
            {
                "name": "demo_plugin",
                "category": "network",
                "has_parser": True,
                "path": "plugins/network/demo_plugin",
            }
        ],
    }

    markdown = format_markdown(report)

    assert "Plugin Health & Coverage Report" in markdown
    assert "demo_plugin" in markdown
    assert "network" in markdown
    assert "Yes" in markdown


def test_cli_output_path_creates_parent_directories_and_writes_file(tmp_path):
    output_path = tmp_path / "nested" / "reports" / "plugin_health_report.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/plugin_health_dashboard.py",
            "--format",
            "json",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == ""
    assert output_path.exists()

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert "summary" in report
    assert "plugins" in report
    assert "categories" in report
