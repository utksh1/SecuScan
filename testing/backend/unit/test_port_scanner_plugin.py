"""
Unit tests for plugins/port-scanner/parser.py.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import the parser module directly from the file without requiring __init__.py
_parser_path = Path(__file__).resolve().parents[3] / "plugins" / "port-scanner" / "parser.py"
_spec = importlib.util.spec_from_file_location("plugins.port_scanner.parser", str(_parser_path))
_parser_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parser_module)
parse = _parser_module.parse


class TestParseOpenPorts:
    def test_finds_single_open_port(self):
        output = "22/tcp open ssh"
        result = parse(output)
        assert result["count"] >= 1

    def test_finds_multiple_open_ports(self):
        output = (
            "22/tcp open ssh\n"
            "80/tcp open http\n"
            "443/tcp open https\n"
        )
        result = parse(output)
        open_ports = result["structured"]["rows"]
        assert len(open_ports) == 3
        ports = [p["port"] for p in open_ports]
        assert "22" in ports
        assert "80" in ports
        assert "443" in ports

    def test_skips_closed_ports(self):
        output = "22/tcp closed ssh\n80/tcp open http"
        result = parse(output)
        open_ports = result["structured"]["rows"]
        assert len(open_ports) == 1
        assert open_ports[0]["port"] == "80"

    def test_skips_filtered_ports(self):
        output = "22/tcp filtered firewall\n80/tcp open http"
        result = parse(output)
        open_ports = result["structured"]["rows"]
        assert len(open_ports) == 1

    def test_port_protocol_in_structured_data(self):
        output = "8080/tcp open http-proxy"
        result = parse(output)
        port = result["structured"]["rows"][0]
        assert port["port"] == "8080"
        assert port["protocol"] == "tcp"
        assert port["service"] == "http-proxy"

    def test_udp_ports_parsed(self):
        output = "53/udp open domain"
        result = parse(output)
        open_ports = result["structured"]["rows"]
        assert len(open_ports) == 1
        assert open_ports[0]["protocol"] == "udp"


class TestSeverityClassification:
    def test_regular_ports_have_low_severity(self):
        output = "22/tcp open ssh\n80/tcp open http"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "low" in severities

    def test_mysql_port_triggers_medium(self):
        output = "3306/tcp open mysql"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities

    def test_ftp_port_triggers_medium(self):
        output = "21/tcp open ftp"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities

    def test_telnet_port_triggers_medium(self):
        output = "23/tcp open telnet"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities

    def test_smb_port_triggers_medium(self):
        output = "445/tcp open microsoft-ds"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities

    def test_rdp_port_triggers_medium(self):
        output = "3389/tcp open ms-wbt-server"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities

    def test_postgres_port_triggers_medium(self):
        output = "5432/tcp open postgresql"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities

    def test_multiple_critical_ports_all_medium(self):
        output = "21/tcp open ftp\n3306/tcp open mysql\n445/tcp open smb"
        result = parse(output)
        severities = [f["severity"] for f in result["findings"]]
        assert "medium" in severities


class TestFindingStructure:
    def test_finding_has_correct_title(self):
        output = "80/tcp open http"
        result = parse(output)
        assert result["findings"][0]["title"] == "Open Network Services Detected"

    def test_finding_has_correct_category(self):
        output = "22/tcp open ssh"
        result = parse(output)
        assert result["findings"][0]["category"] == "Insecure Surface"

    def test_finding_has_remediation(self):
        output = "80/tcp open http"
        result = parse(output)
        assert "remediation" in result["findings"][0]
        assert len(result["findings"][0]["remediation"]) > 0

    def test_metadata_contains_open_ports(self):
        output = "22/tcp open ssh\n80/tcp open http"
        result = parse(output)
        meta = result["findings"][0]["metadata"]
        assert "open_ports" in meta
        assert len(meta["open_ports"]) == 2

    def test_description_contains_port_count(self):
        output = "22/tcp open ssh\n80/tcp open http\n443/tcp open https"
        result = parse(output)
        desc = result["findings"][0]["description"]
        assert "3" in desc


class TestStructuredData:
    def test_total_count_reflects_open_ports(self):
        output = "22/tcp open ssh\n80/tcp open http\n443/tcp open https"
        result = parse(output)
        assert result["structured"]["total_count"] == 3
        assert result["count"] == 1

    def test_rows_contain_port_service_protocol(self):
        output = "22/tcp open ssh"
        result = parse(output)
        row = result["structured"]["rows"][0]
        assert "port" in row
        assert "protocol" in row
        assert "service" in row

    def test_type_is_ports(self):
        output = "80/tcp open http"
        result = parse(output)
        assert result["structured"]["type"] == "ports"

    def test_host_status_up(self):
        output = "Host is up\n22/tcp open ssh"
        result = parse(output)
        assert result["structured"]["host_status"] == "up"

    def test_host_status_unknown(self):
        output = "22/tcp open ssh"
        result = parse(output)
        assert result["structured"]["host_status"] == "unknown"


class TestSummaryText:
    def test_summary_contains_open_port_count(self):
        output = "22/tcp open ssh"
        result = parse(output)
        summary = result["summary"]
        assert any("1" in s for s in summary)

    def test_summary_contains_service_name(self):
        output = "22/tcp open ssh"
        result = parse(output)
        summary_text = " ".join(result["summary"])
        assert "ssh" in summary_text.lower()

    def test_empty_summary_when_no_open_ports(self):
        output = "22/tcp closed ssh"
        result = parse(output)
        assert len(result["findings"]) == 0


class TestHostUpFinding:
    def test_host_up_no_open_ports_creates_info_finding(self):
        output = "Host is up (0.050s latency)"
        result = parse(output)
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "info"
        assert result["findings"][0]["title"] == "Host Status: Active"

    def test_host_up_with_closed_ports_no_finding(self):
        output = "22/tcp closed ssh\n80/tcp filtered http"
        result = parse(output)
        assert len(result["findings"]) == 0


class TestEdgeCases:
    def test_empty_input_returns_empty_findings(self):
        result = parse("")
        assert result["count"] == 0
        assert result["findings"] == []
        assert result["structured"]["rows"] == []

    def test_whitespace_only_input_returns_empty_findings(self):
        result = parse("   \n  \n  ")
        assert result["count"] == 0
        assert result["findings"] == []

    def test_non_matching_lines_skipped(self):
        output = "Starting Nmap scan\n22/tcp open ssh\nHost is up\nFinished scan"
        result = parse(output)
        open_ports = result["structured"]["rows"]
        assert len(open_ports) == 1
        assert open_ports[0]["port"] == "22"

    def test_case_insensitive_state_matching(self):
        output = "22/tcp OPEN ssh\n80/tcp Open http"
        result = parse(output)
        assert len(result["structured"]["rows"]) == 2
