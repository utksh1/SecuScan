"""Pure diff logic for scan findings — no DB access."""

from typing import Any


def fingerprint(finding: dict[str, Any]) -> str:
    """Stable identity key for a finding."""
    title = finding.get("title") or ""
    category = finding.get("category") or ""
    target = finding.get("target") or ""
    return f"{title}\x00{category}\x00{target}"


def compute_diff(
    findings_a: list[dict[str, Any]],
    findings_b: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return new/fixed/unchanged/severity_changed buckets for two finding lists."""
    map_a: dict[str, dict[str, Any]] = {fingerprint(f): f for f in findings_a}
    map_b: dict[str, dict[str, Any]] = {fingerprint(f): f for f in findings_b}
    ka: set[str] = set(map_a)
    kb: set[str] = set(map_b)

    new_findings = [map_b[k] for k in kb - ka]
    fixed_findings = [map_a[k] for k in ka - kb]
    unchanged_findings = [
        map_a[k] for k in ka & kb
        if map_a[k].get("severity") == map_b[k].get("severity")
    ]
    severity_changed = [
        {"before": map_a[k], "after": map_b[k]}
        for k in ka & kb
        if map_a[k].get("severity") != map_b[k].get("severity")
    ]

    return {
        "new_findings": new_findings,
        "fixed_findings": fixed_findings,
        "unchanged_findings": unchanged_findings,
        "severity_changed": severity_changed,
    }
