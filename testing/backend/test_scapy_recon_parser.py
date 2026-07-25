import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from plugins.scapy_recon.parser import parse


# ---------------------------------------------------------------------------
# Normal ARP output
# ---------------------------------------------------------------------------

_ARP_OUTPUT = (
    "UP: 192.168.1.1 - aa:bb:cc:dd:ee:ff\n"
    "UP: 192.168.1.10 - 11:22:33:44:55:66\n"
)


def test_arp_output_extracts_correct_ip_and_mac():
    """Parser must correctly extract IP and MAC from ARP-style lines."""
    result = parse(_ARP_OUTPUT)
    hosts = {h["ip"]: h["mac"] for h in result["hosts"]}

    assert hosts.get("192.168.1.1") == "aa:bb:cc:dd:ee:ff"
    assert hosts.get("192.168.1.10") == "11:22:33:44:55:66"


def test_arp_output_count_matches_hosts():
    """'count' must equal the number of discovered hosts."""
    result = parse(_ARP_OUTPUT)
    assert result["count"] == len(result["hosts"]) == 2


def test_arp_output_findings_contain_ip_and_mac_in_description():
    """Each finding description must reference the host IP and MAC."""
    result = parse(_ARP_OUTPUT)
    for finding in result["findings"]:
        ip = finding["metadata"]["ip"]
        mac = finding["metadata"]["mac"]
        assert ip in finding["description"]
        assert mac in finding["description"]


# ---------------------------------------------------------------------------
# Missing MAC — ICMP-style output
# ---------------------------------------------------------------------------


def test_missing_mac_defaults_to_unknown():
    """A 'UP:' line without a MAC segment must set mac to 'Unknown'."""
    result = parse("UP: 192.168.1.1\n")
    assert result["count"] == 1
    assert result["hosts"][0]["mac"] == "Unknown"


# ---------------------------------------------------------------------------
# Empty / whitespace input
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_results():
    """parse() must return empty results on empty string input."""
    result = parse("")
    assert result == {"findings": [], "count": 0, "hosts": []}


def test_whitespace_only_input_returns_empty_results():
    """parse() must return empty results on whitespace-only input."""
    result = parse("   \n\n\t  \n")
    assert result == {"findings": [], "count": 0, "hosts": []}


# ---------------------------------------------------------------------------
# Noise lines — only UP: lines should be parsed
# ---------------------------------------------------------------------------


def test_noise_lines_are_ignored():
    """Parser must skip non-UP lines and extract only valid host lines."""
    output = (
        "Starting Scapy scan...\n"
        "UP: 192.168.1.5 - 00:aa:bb:cc:dd:ee\n"
        "Some random debug line\n"
        "UP: 192.168.1.9 - ff:00:11:22:33:44\n"
        "Scan finished.\n"
    )
    result = parse(output)
    assert result["count"] == 2
    ips = {h["ip"] for h in result["hosts"]}
    assert ips == {"192.168.1.5", "192.168.1.9"}


# ---------------------------------------------------------------------------
# Malformed input — must not crash
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_output", [
    "UP:\n",
    "UP:  \n",
    "UP: no-dash-separator\n",
    "UP: 999.999.999.999 - INVALID:MAC:HERE\n",
])
def test_malformed_up_line_does_not_crash(bad_output):
    """Parser must not raise an exception for any malformed 'UP:' line."""
    result = parse(bad_output)
    assert isinstance(result, dict)
