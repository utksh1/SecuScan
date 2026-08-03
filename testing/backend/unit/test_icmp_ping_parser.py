from plugins.icmp_ping.parser import parse

def test_parse_normal_reachable():
    output = (
        "PING google.com (142.250.190.46) 56(84) bytes of data.\n"
        "64 bytes from lhr25s34-in-f14.1e100.net (142.250.190.46): icmp_seq=1 ttl=116 time=7.80 ms\n"
        "64 bytes from lhr25s34-in-f14.1e100.net (142.250.190.46): icmp_seq=2 ttl=116 time=7.92 ms\n"
        "\n"
        "--- google.com ping statistics ---\n"
        "2 packets transmitted, 2 packets received, 0.0% packet loss, time 1001ms\n"
        "rtt min/avg/max/mdev = 7.799/7.859/7.919/0.060 ms\n"
    )

    result = parse(output)

    assert result["count"] == 1
    assert len(result["findings"]) == 1
    finding = result["findings"][0]
    assert finding["title"] == "Host Reachable: google.com"
    assert finding["category"] == "Network Reachability"
    assert finding["severity"] == "info"
    assert "google.com responded to ICMP echo requests" in finding["description"]
    assert "Packet loss observed: 0.0%" in finding["description"]

    metrics = result["metrics"]
    assert metrics["target"] == "google.com"
    assert metrics["transmitted"] == 2
    assert metrics["received"] == 2
    assert metrics["packet_loss_percent"] == 0.0
    assert metrics["reachable"] is True
    assert metrics["timeouts"] == 0
    assert metrics["filtered"] is False

    assert "google.com responded to ICMP echo with 2/2 replies." in result["summary"]

def test_parse_reachable_with_loss_and_timeouts():
    output = (
        "PING google.com (142.250.190.46) 56(84) bytes of data.\n"
        "64 bytes from lhr25s34-in-f14.1e100.net (142.250.190.46): icmp_seq=1 ttl=116 time=7.80 ms\n"
        "Request timeout for icmp_seq 2\n"
        "Request timeout for icmp_seq 3\n"
        "64 bytes from lhr25s34-in-f14.1e100.net (142.250.190.46): icmp_seq=4 ttl=116 time=7.92 ms\n"
        "\n"
        "--- google.com ping statistics ---\n"
        "4 packets transmitted, 2 packets received, 50% packet loss, time 3003ms\n"
    )

    result = parse(output)

    assert result["count"] == 1
    finding = result["findings"][0]
    assert finding["title"] == "Host Reachable: google.com"
    assert "Packet loss observed: 50.0%" in finding["description"]

    metrics = result["metrics"]
    assert metrics["target"] == "google.com"
    assert metrics["transmitted"] == 4
    assert metrics["received"] == 2
    assert metrics["packet_loss_percent"] == 50.0
    assert metrics["reachable"] is True
    assert metrics["timeouts"] == 2
    assert metrics["filtered"] is False

def test_parse_unreachable():
    output = (
        "PING 192.0.2.1 (192.0.2.1) 56(84) bytes of data.\n"
        "\n"
        "--- 192.0.2.1 ping statistics ---\n"
        "3 packets transmitted, 0 packets received, 100% packet loss, time 2015ms\n"
    )

    result = parse(output)

    assert result["count"] == 1
    finding = result["findings"][0]
    assert finding["title"] == "No ICMP Response: 192.0.2.1"
    assert "returned 0/3 ICMP replies with 100.0% packet loss." in finding["description"]
    assert "The host did not reply to the probe." in finding["description"]

    metrics = result["metrics"]
    assert metrics["target"] == "192.0.2.1"
    assert metrics["transmitted"] == 3
    assert metrics["received"] == 0
    assert metrics["packet_loss_percent"] == 100.0
    assert metrics["reachable"] is False
    assert metrics["timeouts"] == 0
    assert metrics["filtered"] is False

    assert "192.0.2.1 did not respond to ICMP echo. Packet loss: 100.0%." in result["summary"]

def test_parse_filtered():
    output = (
        "PING 192.0.2.1 (192.0.2.1) 56(84) bytes of data.\n"
        "From 192.0.2.2 icmp_seq=1 Destination Port Unreachable (communication prohibited by filter)\n"
        "\n"
        "--- 192.0.2.1 ping statistics ---\n"
        "1 packets transmitted, 0 packets received, 100.0% packet loss, time 0ms\n"
    )

    result = parse(output)

    assert result["count"] == 1
    finding = result["findings"][0]
    assert finding["title"] == "No ICMP Response: 192.0.2.1"
    assert "ICMP traffic appears filtered along the network path." in finding["description"]

    metrics = result["metrics"]
    assert metrics["target"] == "192.0.2.1"
    assert metrics["transmitted"] == 1
    assert metrics["received"] == 0
    assert metrics["packet_loss_percent"] == 100.0
    assert metrics["reachable"] is False
    assert metrics["timeouts"] == 0
    assert metrics["filtered"] is True

def test_parse_empty():
    result = parse("")

    assert result["count"] == 0
    assert result["findings"] == []
    assert "Ping output did not include packet statistics." in result["summary"]
    assert result["metrics"] == {
        "target": "unknown target",
        "timeouts": 0,
        "filtered": False,
    }
    assert result["items"] == []

def test_parse_malformed():
    result = parse("ping: unknown host someinvalidtarget")

    assert result["count"] == 0
    assert result["findings"] == []
    assert "Ping output did not include packet statistics." in result["summary"]
    assert result["metrics"] == {
        "target": "unknown target",
        "timeouts": 0,
        "filtered": False,
    }
    assert len(result["items"]) == 1
    assert result["items"][0] == "ping: unknown host someinvalidtarget"
