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


def test_icmp_ping_parser_summarizes_full_packet_loss(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    output = """PING 192.168.1.1 (192.168.1.1): 56 data bytes
Request timeout for icmp_seq 0
76 bytes from 115.247.228.233: Communication prohibited by filter

--- 192.168.1.1 ping statistics ---
7 packets transmitted, 0 packets received, 100.0% packet loss
"""

    result = executor._parse_results(plugin, output)

    assert result["count"] == 1
    assert result["findings"][0]["title"] == "No ICMP Response: 192.168.1.1"
    assert result["findings"][0]["severity"] == "info"
    assert result["metrics"]["packet_loss_percent"] == 100.0
    assert result["metrics"]["filtered"] is True


def test_classify_command_result_allows_nonfatal_ping_exit_with_statistics(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    status, error = executor._classify_command_result(
        plugin=plugin,
        output="--- 192.168.1.1 ping statistics ---\n7 packets transmitted, 0 packets received, 100.0% packet loss\n",
        exit_code=2,
    )

    assert status == "completed"
    assert error is None


def test_classify_command_result_keeps_real_ping_execution_errors_failed(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    status, error = executor._classify_command_result(
        plugin=plugin,
        output="ping: cannot resolve definitely-not-a-host: Unknown host\n",
        exit_code=2,
    )

    assert status == "failed"
    assert error is not None
