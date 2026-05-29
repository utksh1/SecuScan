from plugins.dns_enum.parser import parse


def test_dns_enum_groups_repeated_record_hosts():
    output = "\n".join(
        [
            "[*] SOA adi.ns.cloudflare.com 173.245.58.56",
            "[*] SOA adi.ns.cloudflare.com 108.162.192.56",
            "[*] NS adi.ns.cloudflare.com 173.245.58.56",
            "[*] NS adi.ns.cloudflare.com 172.64.32.56",
            "[*] NS yichun.ns.cloudflare.com 173.245.59.248",
            "[*] MX route1.mx.cloudflare.net 162.159.205.11",
            "[*] MX route1.mx.cloudflare.net 162.159.205.12",
            "[*] A utksh.in 216.198.79.1",
        ]
    )

    result = parse(output)

    assert result["count"] == 8
    assert len(result["findings"]) == 5
    assert any("record values grouped into 5 readable DNS entries" in item for item in result["summary"])

    soa = next(finding for finding in result["findings"] if finding["title"] == "DNS SOA Record: adi.ns.cloudflare.com")
    assert "173.245.58.56" in soa["description"]
    assert "108.162.192.56" in soa["description"]
    assert soa["metadata"]["record_count"] == 2


def test_dns_enum_preserves_raw_records_for_exports():
    result = parse("[*] A example.com 93.184.216.34\n[*] MX mail.example.com 10")

    assert result["records"] == [
        {"type": "A", "value": "example.com 93.184.216.34"},
        {"type": "MX", "value": "mail.example.com 10"},
    ]
    assert any(record["type"] == "MX" for record in result["records"])
