import re
from typing import Dict, Any, List

RECORD_REMEDIATION = (
    "Verify that these DNS records are expected, remove stale entries, and "
    "confirm mail/name-server records do not disclose unintended infrastructure."
)


def parse(output: str) -> Dict[str, Any]:
    records: List[Dict[str, str]] = []
    grouped_records: Dict[tuple[str, str], Dict[str, Any]] = {}
    
    # Simple regex to find common record types: [*] TYPE value
    record_pattern = re.compile(r"\[\*\]\s+([A-Z]+)\s+(.*)")
    
    for match in record_pattern.finditer(output):
        rec_type, value = match.groups()
        value = value.strip()
        records.append({"type": rec_type, "value": value})

        parts = value.split()
        host = parts[0] if parts else "Unknown"
        details = parts[1:] if parts else []
        
        key = (rec_type, host)
        group = grouped_records.setdefault(key, {"type": rec_type, "host": host, "values": [], "raw_values": [], "count": 0})
        group["count"] += 1
        group["raw_values"].append(value)
        group["values"].extend(details)

    groups = []
    findings = []
    for group in grouped_records.values():
        values = sorted(set(group["values"]))
        raw_values = sorted(set(group["raw_values"]))
        normalized_group = {"type": group["type"], "host": group["host"], "values": values, "raw_values": raw_values, "count": group["count"]}
        groups.append(normalized_group)

        detail_label = "Resolved values" if group["type"] in {"A", "AAAA", "NS", "SOA", "MX"} else "Values"
        desc = f"{group['type']} record for {group['host']}\n{detail_label} ({len(values)}):\n" + "\n".join(f"- {d}" for d in values) if values else f"{group['type']} record observed for {group['host']}. Seen {group['count']} time{'s' if group['count'] != 1 else ''}."

        findings.append({
            "title": f"DNS {group['type']} Record: {group['host']}",
            "category": "DNS Configuration",
            "severity": "info",
            "description": desc,
            "remediation": RECORD_REMEDIATION,
            "metadata": {"type": group["type"], "host": group["host"], "values": values, "raw_values": raw_values, "record_count": group["count"]}
        })
        
    if "Zone Transfer Successful" in output:
        findings.append({
            "title": "Critical: DNS Zone Transfer Successful",
            "category": "DNS Misconfiguration",
            "severity": "critical",
            "description": "The DNS server allowed a full zone transfer (AXFR). This exposes all internal DNS records.",
            "remediation": "Restrict AXFR transfers to authorized slave servers only."
        })

    if not records:
        summary = ["DNS reconnaissance did not return structured DNS records."]
    else:
        counts_by_type = {}
        for r in records:
            counts_by_type[r["type"]] = counts_by_type.get(r["type"], 0) + 1
        type_summary = ", ".join(f"{t}: {c}" for t, c in sorted(counts_by_type.items()))
        summary = [f"DNS reconnaissance found {len(records)} record values grouped into {len(groups)} readable DNS entries.", f"Record types observed: {type_summary}."]
        
        ns = sorted(set(g["host"] for g in groups if g["type"] == "NS"))[:6]
        mx = sorted(set(g["host"] for g in groups if g["type"] == "MX"))[:6]
        if ns:
            summary.append(f"Authoritative name servers: {', '.join(ns)}.")
        if mx:
            summary.append(f"Mail exchangers: {', '.join(mx)}.")
            
    return {"findings": findings, "count": len(records), "total_count": len(findings), "records": records, "record_groups": groups, "summary": summary}
