import re
from typing import Dict, Any, List

RECORD_REMEDIATION = (
    "Verify that these DNS records are expected, remove stale entries, and "
    "confirm mail/name-server records do not disclose unintended infrastructure."
)


def _unique(items: List[str]) -> List[str]:
    seen = set()
    unique_items = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)
    return unique_items


def _split_record_value(value: str) -> tuple[str, List[str]]:
    parts = value.split()
    if not parts:
        return "Unknown", []
    return parts[0], parts[1:]


def _format_group_description(
    rec_type: str, host: str, details: List[str], total: int
) -> str:
    if details:
        detail_label = (
            "Resolved values"
            if rec_type in {"A", "AAAA", "NS", "SOA", "MX"}
            else "Values"
        )
        return (
            f"{rec_type} record for {host}\n"
            f"{detail_label} ({len(details)}):\n"
            + "\n".join(f"- {detail}" for detail in details)
        )
    return f"{rec_type} record observed for {host}. Seen {total} time{'s' if total != 1 else ''}."


def _summarize_dns_records(
    records: List[Dict[str, str]], groups: List[Dict[str, Any]]
) -> List[str]:
    if not records:
        return ["DNS reconnaissance did not return structured DNS records."]

    counts_by_type: Dict[str, int] = {}
    for record in records:
        counts_by_type[record["type"]] = counts_by_type.get(record["type"], 0) + 1

    type_summary = ", ".join(
        f"{record_type}: {count}"
        for record_type, count in sorted(counts_by_type.items())
    )
    summary = [
        f"DNS reconnaissance found {len(records)} record values grouped into {len(groups)} readable DNS entries.",
        f"Record types observed: {type_summary}.",
    ]

    name_servers = [group["host"] for group in groups if group["type"] == "NS"]
    mail_exchangers = [group["host"] for group in groups if group["type"] == "MX"]
    if name_servers:
        summary.append(
            f"Authoritative name servers: {', '.join(_unique(name_servers)[:6])}."
        )
    if mail_exchangers:
        summary.append(f"Mail exchangers: {', '.join(_unique(mail_exchangers)[:6])}.")

    return summary


def parse(output: str) -> Dict[str, Any]:
    """
    Parse DNSRecon output.
    """
    records: List[Dict[str, str]] = []
    grouped_records: Dict[tuple[str, str], Dict[str, Any]] = {}

    # Simple regex to find common record types: [*] TYPE value
    record_pattern = re.compile(r"\[\*\]\s+([A-Z]+)\s+(.*)")

    for match in record_pattern.finditer(output):
        rec_type, value = match.groups()
        value = value.strip()
        records.append({"type": rec_type, "value": value})

        host, details = _split_record_value(value)
        key = (rec_type, host)
        group = grouped_records.setdefault(
            key,
            {
                "type": rec_type,
                "host": host,
                "values": [],
                "raw_values": [],
                "count": 0,
            },
        )
        group["count"] += 1
        group["raw_values"].append(value)
        group["values"].extend(details)

    groups = []
    findings = []
    for group in grouped_records.values():
        values = _unique(group["values"])
        raw_values = _unique(group["raw_values"])
        normalized_group = {
            "type": group["type"],
            "host": group["host"],
            "values": values,
            "raw_values": raw_values,
            "count": group["count"],
        }
        groups.append(normalized_group)

        findings.append(
            {
                "title": f"DNS {group['type']} Record: {group['host']}",
                "category": "DNS Configuration",
                "severity": "info",
                "description": _format_group_description(
                    group["type"], group["host"], values, group["count"]
                ),
                "remediation": RECORD_REMEDIATION,
                "metadata": {
                    "type": group["type"],
                    "host": group["host"],
                    "values": values,
                    "raw_values": raw_values,
                    "record_count": group["count"],
                },
            }
        )

    if "Zone Transfer Successful" in output:
        findings.append(
            {
                "title": "Critical: DNS Zone Transfer Successful",
                "category": "DNS Misconfiguration",
                "severity": "critical",
                "description": "The DNS server allowed a full zone transfer (AXFR). This exposes all internal DNS records.",
                "remediation": "Restrict AXFR transfers to authorized slave servers only.",
            }
        )

    return {
        "findings": findings,
        "count": len(records),
        "total_count": len(findings),
        "records": records,
        "record_groups": groups,
        "summary": _summarize_dns_records(records, groups),
    }
