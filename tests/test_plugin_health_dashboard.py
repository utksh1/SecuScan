import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.plugin_health_dashboard import build_report


def test_build_report_summary_counts():
    plugins = [
        {
            "name": "nmap",
            "path": "plugins/network/nmap.py",
            "has_parser": True,
            "has_tests": True,
            "category": "network",
        },
        {
            "name": "whois",
            "path": "plugins/recon/whois.py",
            "has_parser": False,
            "has_tests": False,
            "category": "recon",
        },
    ]

    report = build_report(plugins)

    assert report["summary"]["total_plugins"] == 2
    assert report["summary"]["plugins_with_parsers"] == 1
    assert report["summary"]["plugins_without_parsers"] == 1
    assert report["summary"]["plugins_with_tests"] == 1
    assert report["summary"]["plugins_without_tests"] == 1
    assert report["categories"]["network"] == 1
    assert report["categories"]["recon"] == 1
