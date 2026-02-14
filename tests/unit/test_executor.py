import asyncio
import json

from backend.secuscan.config import settings
from backend.secuscan.executor import TaskExecutor
from backend.secuscan.plugins import get_plugin_manager, init_plugins


def _ensure_plugins_loaded():
    try:
        return get_plugin_manager()
    except RuntimeError:
        asyncio.run(init_plugins(settings.plugins_dir))
        return get_plugin_manager()


def test_parse_results_prefers_report_path_when_available(setup_test_environment, tmp_path):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("secret_scanner")
    assert plugin is not None

    report_file = tmp_path / "gitleaks-report.json"
    report_file.write_text(
        json.dumps(
            [
                {
                    "RuleID": "generic-api-key",
                    "File": "config.py",
                    "StartLine": 10,
                    "Offender": "SG.xxxx",
                }
            ]
        ),
        encoding="utf-8",
    )

    plugin.output["report_path"] = str(report_file)
    executor = TaskExecutor()

    result = executor._parse_results(plugin, "No leaks found")
    assert result["count"] == 1
    assert "Secret Leak" in result["findings"][0]["title"]


def test_parse_results_falls_back_to_stdout_when_report_missing(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("secret_scanner")
    assert plugin is not None

    plugin.output["report_path"] = "/tmp/does-not-exist.json"
    executor = TaskExecutor()
    stdout_json = json.dumps(
        [
            {
                "RuleID": "generic-api-key",
                "File": "stdout.py",
                "StartLine": 7,
                "Offender": "AKIA...",
            }
        ]
    )

    result = executor._parse_results(plugin, stdout_json)
    assert result["count"] == 1
    assert "stdout.py" in result["findings"][0]["title"]
