"""Finding normalization, correlation, grouping, and diff helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


_OBSERVATION_CATEGORIES = {
    "attack surface",
    "asset discovery",
    "api discovery",
    "api exposure",
    "service exposure",
    "information disclosure",
    "technology fingerprint",
    "transport security",
    "certificate hygiene",
}

_SOURCE_QUALITY = {
    "nuclei": 0.8,
    "nikto": 0.7,
    "ffuf": 0.7,
    "nmap": 0.78,
    "http_probe": 0.82,
    "http_inspector": 0.7,
    "crawl": 0.68,
    "graphql": 0.82,
    "openapi": 0.8,
    "knowledgebase": 0.72,
    "tls_probe": 0.8,
    "socket_probe": 0.76,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(raw: Any) -> str:
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc).isoformat()
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            return _now_iso()
    return _now_iso()


def _stable_id(prefix: str, *parts: Any) -> str:
    material = "||".join(str(part or "").strip().lower() for part in parts)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _normalize_severity(value: Any) -> str:
    severity = str(value or "info").lower()
    mapping = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "moderate": "medium",
        "low": "low",
        "info": "info",
        "informational": "info",
        "note": "info",
    }
    return mapping.get(severity, "info")


def _severity_rank(value: str) -> int:
    order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    return order.get(_normalize_severity(value), 1)


def _normalize_url_path(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return parsed.path.rstrip("/") or "/"
    if value.startswith("/"):
        return value.rstrip("/") or "/"
    return ""


def _extract_best_url(finding: Dict[str, Any]) -> str:
    metadata = finding.get("metadata") if isinstance(finding.get("metadata"), dict) else {}
    for key in ("url", "matched_at", "endpoint", "action"):
        value = metadata.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    for evidence in finding.get("evidence", []) if isinstance(finding.get("evidence"), list) else []:
        if not isinstance(evidence, dict):
            continue
        value = evidence.get("value")
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    target = str(finding.get("target") or "")
    return target if target.startswith(("http://", "https://")) else ""


def _guess_asset_ref(finding: Dict[str, Any], target: str) -> str:
    asset_refs = finding.get("asset_refs") if isinstance(finding.get("asset_refs"), list) else []
    if asset_refs:
        first = asset_refs[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    best_url = _extract_best_url(finding)
    if best_url:
        parsed = urlparse(best_url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    metadata = finding.get("metadata") if isinstance(finding.get("metadata"), dict) else {}
    host = metadata.get("host") or target
    port = metadata.get("port")
    protocol = metadata.get("protocol")
    if port:
        return f"{host}:{port}/{protocol or 'tcp'}"
    return str(host or target)


def _issue_signature(finding: Dict[str, Any]) -> str:
    cve = str(finding.get("cve") or "").strip().lower()
    if cve:
        return f"cve:{cve}"

    metadata = finding.get("metadata") if isinstance(finding.get("metadata"), dict) else {}
    path = _normalize_url_path(_extract_best_url(finding))
    detail = (
        metadata.get("template")
        or metadata.get("header")
        or metadata.get("cookie_name")
        or metadata.get("policy")
        or metadata.get("service")
        or metadata.get("endpoint")
        or metadata.get("port")
        or metadata.get("cms")
        or ""
    )
    base = "|".join(
        [
            str(finding.get("category") or "").strip().lower(),
            str(finding.get("title") or "").strip().lower(),
            str(finding.get("validation_method") or "").strip().lower(),
            str(detail).strip().lower(),
            path,
        ]
    )
    compact = re.sub(r"[^a-z0-9|:/._-]+", "-", base)
    return compact.strip("-") or "finding"


def _typed_evidence(
    item: Any,
    *,
    source: str,
    observed_at: str,
    confidence: float,
) -> Dict[str, Any]:
    if isinstance(item, dict):
        evidence_type = str(item.get("type") or "evidence")
        label = str(item.get("label") or evidence_type.replace("_", " ").title())
        value = item.get("value")
        artifact_ref = item.get("artifact_ref")
        item_source = str(item.get("source") or source)
        item_confidence = item.get("confidence")
        normalized_confidence = float(item_confidence) if isinstance(item_confidence, (int, float)) else confidence
        return {
            "type": evidence_type,
            "label": label,
            "value": value,
            "artifact_ref": artifact_ref,
            "source": item_source,
            "observed_at": str(item.get("observed_at") or observed_at),
            "confidence": max(0.0, min(1.0, normalized_confidence)),
        }
    return {
        "type": "evidence",
        "label": "Evidence",
        "value": item,
        "artifact_ref": None,
        "source": source,
        "observed_at": observed_at,
        "confidence": max(0.0, min(1.0, confidence)),
    }


def _dedupe_evidence(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        key = json.dumps(
            {
                "type": item.get("type"),
                "label": item.get("label"),
                "value": item.get("value"),
                "artifact_ref": item.get("artifact_ref"),
                "source": item.get("source"),
            },
            sort_keys=True,
            default=str,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _merge_text(primary: str, fallback: str) -> str:
    return primary if str(primary or "").strip() else fallback


def _build_confidence_reason(
    *,
    finding_kind: str,
    evidence_count: int,
    corroborating_sources: List[str],
    occurrence_count: int,
    match_strength: str,
) -> str:
    parts = [
        f"{finding_kind.replace('_', ' ')} classification",
        f"{evidence_count} evidence item{'s' if evidence_count != 1 else ''}",
    ]
    if corroborating_sources:
        parts.append(f"corroborated by {len(corroborating_sources)} source{'s' if len(corroborating_sources) != 1 else ''}")
    if occurrence_count > 1:
        parts.append(f"seen across {occurrence_count} scan observations")
    if match_strength and match_strength != "none":
        parts.append(f"{match_strength} fingerprint match")
    return "; ".join(parts).capitalize() + "."


def _finding_kind_for(finding: Dict[str, Any]) -> str:
    category = str(finding.get("category") or "").strip().lower()
    severity = _normalize_severity(finding.get("severity"))
    if finding.get("validated") and category not in _OBSERVATION_CATEGORIES and severity in {"critical", "high", "medium", "low"}:
        return "validated_issue"
    if category in _OBSERVATION_CATEGORIES and not finding.get("cve"):
        return "observation"
    if severity in {"critical", "high", "medium"} or finding.get("cve") or finding.get("validation_method") == "cpe_cve_correlation":
        return "suspected_issue"
    return "observation"


def _fingerprint_score(finding: Dict[str, Any]) -> tuple[float, str]:
    metadata = finding.get("metadata") if isinstance(finding.get("metadata"), dict) else {}
    match_strength = str(
        metadata.get("match_strength")
        or metadata.get("cpe_match_strength")
        or ("validated" if finding.get("validated") else "none")
    ).lower()
    mapping = {"validated": 1.0, "exact": 0.95, "strong_fuzzy": 0.8, "fuzzy": 0.7, "family": 0.45, "none": 0.25}
    return mapping.get(match_strength, 0.35), match_strength


def _source_quality(sources: Iterable[str]) -> float:
    values = [_SOURCE_QUALITY.get(str(source).lower(), 0.58) for source in sources if str(source).strip()]
    return max(values) if values else 0.58


def _compute_confidence(
    finding: Dict[str, Any],
    *,
    corroborating_sources: List[str],
    occurrence_count: int,
    evidence: List[Dict[str, Any]],
) -> float:
    fingerprint_score, _ = _fingerprint_score(finding)
    base = 0.18
    source_component = _source_quality(corroborating_sources) * 0.28
    evidence_component = min(0.2, 0.05 * len(evidence))
    repeatability_component = min(0.15, 0.05 * max(0, occurrence_count - 1))
    corroboration_component = min(0.12, 0.06 * max(0, len(corroborating_sources) - 1))
    fingerprint_component = fingerprint_score * 0.18
    validation_component = 0.12 if finding.get("validated") else 0.04 if finding.get("cve") else 0.0
    severity_component = {"critical": 0.08, "high": 0.06, "medium": 0.04, "low": 0.02, "info": 0.0}.get(
        _normalize_severity(finding.get("severity")),
        0.0,
    )
    score = (
        base
        + source_component
        + evidence_component
        + repeatability_component
        + corroboration_component
        + fingerprint_component
        + validation_component
        + severity_component
    )
    return round(max(0.0, min(0.99, score)), 2)


def _sort_sources(sources: Iterable[str]) -> List[str]:
    return sorted({str(source).strip() for source in sources if str(source).strip()})


async def normalize_and_correlate_findings(
    db: Any,
    *,
    owner_id: str,
    plugin_id: str,
    target: str,
    findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize evidence and correlate repeated findings across scans."""
    observed_at = _now_iso()
    staged: Dict[str, Dict[str, Any]] = {}

    for raw_finding in findings:
        finding = dict(raw_finding or {})
        severity = _normalize_severity(finding.get("severity"))
        asset_ref = _guess_asset_ref(finding, target)
        asset_id = _stable_id("asset", target, asset_ref)
        finding_group_id = _stable_id("group", plugin_id, asset_id, _issue_signature(finding))
        base_source = str(
            (finding.get("metadata") or {}).get("source")
            if isinstance(finding.get("metadata"), dict)
            else ""
        ) or plugin_id

        normalized_evidence = _dedupe_evidence(
            [
                _typed_evidence(item, source=base_source, observed_at=observed_at, confidence=0.72)
                for item in (finding.get("evidence") if isinstance(finding.get("evidence"), list) else [])
            ]
        )
        sources = _sort_sources(
            [base_source]
            + [item.get("source", "") for item in normalized_evidence if isinstance(item, dict)]
        )

        staged_item = staged.get(finding_group_id)
        if staged_item is None:
            staged[finding_group_id] = {
                **finding,
                "severity": severity,
                "target": str(finding.get("target") or target),
                "asset_refs": sorted({asset_ref, *[str(ref) for ref in finding.get("asset_refs", []) if str(ref).strip()]}),
                "asset_id": asset_id,
                "finding_group_id": finding_group_id,
                "evidence": normalized_evidence,
                "corroborating_sources": sources,
                "metadata": dict(finding.get("metadata") or {}),
                "occurrence_count": 1,
                "discovered_at": str(finding.get("discovered_at") or observed_at),
            }
            continue

        staged_item["occurrence_count"] = int(staged_item.get("occurrence_count", 1)) + 1
        if _severity_rank(severity) > _severity_rank(staged_item.get("severity", "info")):
            staged_item["severity"] = severity
        staged_item["validated"] = bool(staged_item.get("validated")) or bool(finding.get("validated"))
        staged_item["cvss"] = staged_item.get("cvss") or finding.get("cvss")
        staged_item["cve"] = staged_item.get("cve") or finding.get("cve")
        staged_item["cpe"] = staged_item.get("cpe") or finding.get("cpe")
        staged_item["service_fingerprint"] = staged_item.get("service_fingerprint") or finding.get("service_fingerprint")
        staged_item["description"] = _merge_text(staged_item.get("description", ""), finding.get("description", ""))
        staged_item["remediation"] = _merge_text(staged_item.get("remediation", ""), finding.get("remediation", ""))
        staged_item["proof"] = _merge_text(staged_item.get("proof", ""), finding.get("proof", ""))
        staged_item["validation_method"] = _merge_text(staged_item.get("validation_method", ""), finding.get("validation_method", ""))
        staged_item["confidence_reason"] = _merge_text(staged_item.get("confidence_reason", ""), finding.get("confidence_reason", ""))
        staged_item["asset_refs"] = sorted({*staged_item.get("asset_refs", []), *[str(ref) for ref in finding.get("asset_refs", []) if str(ref).strip()]})
        staged_item["references"] = [
            *staged_item.get("references", []),
            *[item for item in finding.get("references", []) if isinstance(item, dict)],
        ]
        staged_item["evidence"] = _dedupe_evidence([*staged_item.get("evidence", []), *normalized_evidence])
        staged_item["corroborating_sources"] = _sort_sources([*staged_item.get("corroborating_sources", []), *sources])
        staged_item["metadata"].update({key: value for key, value in (finding.get("metadata") or {}).items() if value not in ("", None, [], {})})

    normalized: List[Dict[str, Any]] = []
    for finding_group_id, finding in staged.items():
        previous = await db.fetchone(
            """
            SELECT first_seen_at, occurrence_count, corroborating_sources_json, analyst_status, retest_status
            FROM findings
            WHERE owner_id = ? AND finding_group_id = ?
            ORDER BY discovered_at DESC
            LIMIT 1
            """,
            (owner_id, finding_group_id),
        )
        prior_sources = []
        if previous and previous.get("corroborating_sources_json"):
            try:
                prior_sources = json.loads(previous["corroborating_sources_json"])
            except json.JSONDecodeError:
                prior_sources = []

        finding["corroborating_sources"] = _sort_sources([*finding.get("corroborating_sources", []), *prior_sources])
        previous_count = int(previous["occurrence_count"]) if previous and previous.get("occurrence_count") else 0
        local_count = int(finding.get("occurrence_count", 1))
        occurrence_count = previous_count + local_count
        finding["occurrence_count"] = occurrence_count
        finding["first_seen_at"] = str(previous["first_seen_at"]) if previous and previous.get("first_seen_at") else finding["discovered_at"]
        finding["last_seen_at"] = finding["discovered_at"]
        finding["analyst_status"] = str(previous["analyst_status"]) if previous and previous.get("analyst_status") else "new"
        finding["retest_status"] = str(previous["retest_status"]) if previous and previous.get("retest_status") else "not_requested"
        finding["finding_kind"] = _finding_kind_for(finding)
        finding["evidence_count"] = len(finding.get("evidence", []))
        fingerprint_score, match_strength = _fingerprint_score(finding)
        finding["confidence"] = _compute_confidence(
            finding,
            corroborating_sources=finding.get("corroborating_sources", []),
            occurrence_count=occurrence_count,
            evidence=finding.get("evidence", []),
        )
        if not finding.get("confidence_reason"):
            finding["confidence_reason"] = _build_confidence_reason(
                finding_kind=finding["finding_kind"],
                evidence_count=finding["evidence_count"],
                corroborating_sources=finding.get("corroborating_sources", []),
                occurrence_count=occurrence_count,
                match_strength=match_strength if fingerprint_score >= 0.45 else "none",
            )
        normalized.append(finding)

    normalized.sort(
        key=lambda item: (
            -_severity_rank(item.get("severity", "info")),
            -(float(item.get("confidence") or 0.0)),
            str(item.get("title") or "").lower(),
        )
    )
    return normalized


def build_finding_groups(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, Dict[str, Any]] = {}
    for finding in findings:
        group_id = str(finding.get("finding_group_id") or finding.get("id") or _stable_id("group", finding.get("title"), finding.get("target")))
        current = groups.get(group_id)
        if current is None:
            groups[group_id] = {
                "id": group_id,
                "title": finding.get("title"),
                "severity": _normalize_severity(finding.get("severity")),
                "category": finding.get("category"),
                "target": finding.get("target"),
                "asset_id": finding.get("asset_id"),
                "finding_kind": finding.get("finding_kind", "observation"),
                "validated": bool(finding.get("validated")),
                "cve": finding.get("cve"),
                "cpe": finding.get("cpe"),
                "confidence": finding.get("confidence"),
                "confidence_reason": finding.get("confidence_reason"),
                "first_seen_at": finding.get("first_seen_at") or finding.get("discovered_at"),
                "last_seen_at": finding.get("last_seen_at") or finding.get("discovered_at"),
                "occurrence_count": int(finding.get("occurrence_count") or 1),
                "evidence_count": int(finding.get("evidence_count") or len(finding.get("evidence", []))),
                "corroborating_sources": list(finding.get("corroborating_sources", [])),
                "analyst_status": finding.get("analyst_status", "new"),
                "retest_status": finding.get("retest_status", "not_requested"),
                "latest_finding_id": finding.get("id"),
                "findings": [finding],
            }
            continue

        current["validated"] = bool(current.get("validated")) or bool(finding.get("validated"))
        if _severity_rank(finding.get("severity", "info")) > _severity_rank(current.get("severity", "info")):
            current["severity"] = _normalize_severity(finding.get("severity"))
        current["last_seen_at"] = max(str(current.get("last_seen_at") or ""), str(finding.get("last_seen_at") or finding.get("discovered_at") or ""))
        current["first_seen_at"] = min(str(current.get("first_seen_at") or ""), str(finding.get("first_seen_at") or finding.get("discovered_at") or ""))
        current["occurrence_count"] = max(int(current.get("occurrence_count") or 1), int(finding.get("occurrence_count") or 1))
        current["evidence_count"] = max(int(current.get("evidence_count") or 0), int(finding.get("evidence_count") or len(finding.get("evidence", []))))
        current["corroborating_sources"] = _sort_sources([*current.get("corroborating_sources", []), *finding.get("corroborating_sources", [])])
        current["confidence"] = max(float(current.get("confidence") or 0.0), float(finding.get("confidence") or 0.0))
        current["findings"].append(finding)

    grouped = list(groups.values())
    grouped.sort(
        key=lambda item: (
            -_severity_rank(item.get("severity", "info")),
            -(float(item.get("confidence") or 0.0)),
            str(item.get("title") or "").lower(),
        )
    )
    return grouped


def build_asset_summary(
    findings: List[Dict[str, Any]],
    asset_services: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    assets: Dict[str, Dict[str, Any]] = {}
    for service in asset_services:
        asset_id = str(service.get("asset_id") or _stable_id("asset", service.get("target"), service.get("host"), service.get("port"), service.get("protocol")))
        entry = assets.setdefault(
            asset_id,
            {
                "asset_id": asset_id,
                "label": service.get("host") or service.get("target"),
                "target": service.get("target"),
                "services": [],
                "finding_count": 0,
                "validated_count": 0,
                "highest_severity": "info",
            },
        )
        entry["services"].append(service)

    for finding in findings:
        asset_id = str(finding.get("asset_id") or _stable_id("asset", finding.get("target"), *(finding.get("asset_refs") or [])))
        entry = assets.setdefault(
            asset_id,
            {
                "asset_id": asset_id,
                "label": finding.get("target"),
                "target": finding.get("target"),
                "services": [],
                "finding_count": 0,
                "validated_count": 0,
                "highest_severity": "info",
            },
        )
        entry["finding_count"] += 1
        if finding.get("validated"):
            entry["validated_count"] += 1
        if _severity_rank(finding.get("severity", "info")) > _severity_rank(entry.get("highest_severity", "info")):
            entry["highest_severity"] = _normalize_severity(finding.get("severity"))

    summary = list(assets.values())
    summary.sort(key=lambda item: (-_severity_rank(item.get("highest_severity", "info")), -int(item.get("finding_count", 0)), str(item.get("label") or "")))
    return summary


def build_scan_diff(current_findings: List[Dict[str, Any]], previous_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    current = {str(item.get("finding_group_id") or item.get("id")): item for item in current_findings}
    previous = {str(item.get("finding_group_id") or item.get("id")): item for item in previous_findings}

    new_groups = [current[key] for key in current.keys() - previous.keys()]
    resolved_groups = [previous[key] for key in previous.keys() - current.keys()]
    changed_groups = []
    for key in current.keys() & previous.keys():
        before = previous[key]
        after = current[key]
        if (
            before.get("severity") != after.get("severity")
            or bool(before.get("validated")) != bool(after.get("validated"))
            or round(float(before.get("confidence") or 0.0), 2) != round(float(after.get("confidence") or 0.0), 2)
        ):
            changed_groups.append(
                {
                    "before": before,
                    "after": after,
                    "group_id": key,
                }
            )

    return {
        "new": build_finding_groups(new_groups),
        "resolved": build_finding_groups(resolved_groups),
        "changed": changed_groups,
        "summary": {
            "new_count": len(new_groups),
            "resolved_count": len(resolved_groups),
            "changed_count": len(changed_groups),
        },
    }
