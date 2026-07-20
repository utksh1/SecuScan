import re
from typing import Any, Dict


PING_HEADER_RE = re.compile(r"^PING\s+(?P<target>\S+)")
PING_STATS_RE = re.compile(
    r"(?P<transmitted>\d+)\s+packets transmitted,\s+"
    r"(?P<received>\d+)\s+packets received,\s+"
    r"(?P<loss>[\d.]+)%\s+packet loss",
    re.IGNORECASE,
)


def parse(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    target = "unknown target"

    header_match = PING_HEADER_RE.search(output)
    if header_match:
        target = header_match.group("target")

    stats_match = PING_STATS_RE.search(output)
    timeout_count = sum(1 for line in lines if "request timeout" in line.lower())
    filtered = any("communication prohibited by filter" in line.lower() for line in lines)

    findings = []
    summary = []
    metrics: Dict[str, Any] = {
        "target": target,
        "timeouts": timeout_count,
        "filtered": filtered,
    }

    if stats_match:
        transmitted = int(stats_match.group("transmitted"))
        received = int(stats_match.group("received"))
        packet_loss = float(stats_match.group("loss"))
        reachable = received > 0

        metrics.update(
            {
                "transmitted": transmitted,
                "received": received,
                "packet_loss_percent": packet_loss,
                "reachable": reachable,
            }
        )

        if reachable:
            summary.append(f"{target} responded to ICMP echo with {received}/{transmitted} replies.")
            findings.append(
                {
                    "title": f"Host Reachable: {target}",
                    "category": "Network Reachability",
                    "severity": "info",
                    "description": (
                        f"{target} responded to ICMP echo requests. "
                        f"Packet loss observed: {packet_loss:.1f}%."
                    ),
                    "remediation": "No action required unless intermittent loss is unexpected.",
                    "metadata": metrics,
                }
            )
        else:
            reason = "ICMP traffic appears filtered along the network path." if filtered else "The host did not reply to the probe."
            summary.append(f"{target} did not respond to ICMP echo. Packet loss: {packet_loss:.1f}%.")
            findings.append(
                {
                    "title": f"No ICMP Response: {target}",
                    "category": "Network Reachability",
                    "severity": "info",
                    "description": (
                        f"{target} returned 0/{transmitted} ICMP replies with {packet_loss:.1f}% packet loss. "
                        f"{reason}"
                    ),
                    "remediation": "Verify routing, firewall rules, and whether the target intentionally drops ICMP traffic.",
                    "metadata": metrics,
                }
            )
    else:
        summary.append("Ping output did not include packet statistics.")

    return {
        "findings": findings,
        "count": len(findings),
        "summary": summary,
        "metrics": metrics,
        "items": lines[:50],
    }
