from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Numeric maps
# ---------------------------------------------------------------------------

SEVERITY_MAP: Dict[str, float] = {
    "critical": 10.0,
    "high": 7.5,
    "medium": 5.0,
    "low": 2.5,
    "info": 0.5,
}

ASSET_EXPOSURE_MAP: Dict[str, float] = {
    "critical": 10.0,
    "high": 7.5,
    "medium": 5.0,
    "low": 2.5,
}

# System exposure context factors (multiplicative)
EXPOSURE_CONTEXT_MAP: Dict[str, float] = {
    "public": 1.5,          # Public-facing systems: higher multiplier
    "internet_facing": 1.3, # Internet-accessible but not primary public interface
    "internal": 0.8,        # Internal only: lower multiplier
    "private": 0.6,         # Development/private systems: minimal context
}

# Business criticality factors (multiplicative)
CRITICALITY_MAP: Dict[str, float] = {
    "critical": 1.5,     # Critical business function
    "high": 1.25,
    "medium": 1.0,       # Standard business function (no multiplier)
    "low": 0.8,          # Non-critical function
}

# Weights used in the composite score (must sum to 1.0)
WEIGHTS = {
    "severity": 0.30,
    "exploitability": 0.25,
    "asset_exposure": 0.20,
    "recency": 0.15,
    "confidence": 0.10,
}


def _severity_score(severity: str) -> float:
    return SEVERITY_MAP.get(severity.lower(), 0.5)


def _recency_score(discovered_at: Optional[datetime]) -> float:
    if discovered_at is None:
        return 5.0
    now = datetime.now(timezone.utc)
    if discovered_at.tzinfo is None:
        from datetime import timedelta
        discovered = discovered_at.replace(tzinfo=timezone.utc)
    else:
        discovered = discovered_at
    days = (now - discovered).days
    if days < 7:
        return 10.0
    if days < 30:
        return 7.5
    if days < 90:
        return 5.0
    if days < 365:
        return 2.5
    return 1.0


def _confidence_score(confidence: Optional[float]) -> float:
    if confidence is None:
        return 0.0
    return max(0.0, min(10.0, confidence * 10.0))



def _contextual_severity_score(
    base_severity: float,
    exposure_context: Optional[str] = None,
    business_criticality: Optional[str] = None,
    custom_override: Optional[float] = None,
) -> float:
    if custom_override is not None:
        return max(0.0, min(10.0, custom_override))

    exposure_mult = EXPOSURE_CONTEXT_MAP.get((exposure_context or "").lower(), 1.0)
    criticality_mult = CRITICALITY_MAP.get((business_criticality or "").lower(), 1.0)

    contextual_score = base_severity * exposure_mult * criticality_mult
    return max(0.0, min(10.0, contextual_score))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_risk_score(
    severity: str,
    exploitability: Optional[float] = None,
    asset_exposure: Optional[str] = None,
    discovered_at: Optional[datetime] = None,
    confidence: Optional[float] = None,
    exposure_context: Optional[str] = None,
    business_criticality: Optional[str] = None,
    severity_override: Optional[float] = None,
) -> float:
    base_severity = _severity_score(severity)
    sv = _contextual_severity_score(
        base_severity,
        exposure_context=exposure_context,
        business_criticality=business_criticality,
        custom_override=severity_override,
    )
    ev = max(0.0, min(10.0, exploitability if exploitability is not None else 0.0))
    av = ASSET_EXPOSURE_MAP.get(asset_exposure.lower() if asset_exposure else None, 0.0)
    rv = _recency_score(discovered_at)
    cv = _confidence_score(confidence)

    score = (
        sv * WEIGHTS["severity"]
        + ev * WEIGHTS["exploitability"]
        + av * WEIGHTS["asset_exposure"]
        + rv * WEIGHTS["recency"]
        + cv * WEIGHTS["confidence"]
    )
    return round(max(0.0, min(10.0, score)), 1)


def compute_risk_factors(
    severity: str,
    exploitability: Optional[float] = None,
    asset_exposure: Optional[str] = None,
    discovered_at: Optional[datetime] = None,
    confidence: Optional[float] = None,
    exposure_context: Optional[str] = None,
    business_criticality: Optional[str] = None,
    severity_override: Optional[float] = None,
    risk_score: Optional[float] = None,
) -> List[Dict[str, Any]]:
    if risk_score is None:
        risk_score = compute_risk_score(
            severity, exploitability, asset_exposure, discovered_at, confidence,
            exposure_context=exposure_context,
            business_criticality=business_criticality,
            severity_override=severity_override,
        )

    base_severity = _severity_score(severity)
    sv = _contextual_severity_score(
        base_severity,
        exposure_context=exposure_context,
        business_criticality=business_criticality,
        custom_override=severity_override,
    )
    ev = max(0.0, min(10.0, exploitability if exploitability is not None else 5.0))
    av = ASSET_EXPOSURE_MAP.get(asset_exposure.lower() if asset_exposure else None, 5.0)
    rv = _recency_score(discovered_at)
    cv = _confidence_score(confidence)

    # Build context information string
    context_parts = []
    if exposure_context:
        context_parts.append(f"exposure: {exposure_context}")
    if business_criticality:
        context_parts.append(f"criticality: {business_criticality}")
    context_str = " [" + ", ".join(context_parts) + "]" if context_parts else ""

    factors = [
        {
            "factor": "severity",
            "label": "Severity",
            "value": severity,
            "score": round(sv, 1),
            "weight": WEIGHTS["severity"],
            "contribution": round(sv * WEIGHTS["severity"], 2),
            "detail": f"Base severity {severity} ({base_severity:.1f}/10) adjusted to {sv:.1f}/10{context_str}",
            "exposure_context": exposure_context,
            "business_criticality": business_criticality,
            "context_multiplier": round((sv / base_severity) if base_severity > 0 else 1.0, 2),
        },
        {
            "factor": "exploitability",
            "label": "Exploitability",
            "value": exploitability if exploitability is not None else 5.0,
            "score": round(ev, 1),
            "weight": WEIGHTS["exploitability"],
            "contribution": round(ev * WEIGHTS["exploitability"], 2),
            "detail": f"Exploitability score is {ev:.1f}/10",
        },
        {
            "factor": "asset_exposure",
            "label": "Asset Exposure",
            "value": asset_exposure or "medium",
            "score": round(av, 1),
            "weight": WEIGHTS["asset_exposure"],
            "contribution": round(av * WEIGHTS["asset_exposure"], 2),
            "detail": f"Asset exposure is {asset_exposure or 'medium'} ({av:.1f}/10)",
        },
        {
            "factor": "recency",
            "label": "Recency",
            "value": f"{discovered_at.isoformat() if discovered_at else 'unknown'}",
            "score": round(rv, 1),
            "weight": WEIGHTS["recency"],
            "contribution": round(rv * WEIGHTS["recency"], 2),
            "detail": _recency_detail(discovered_at, rv),
        },
        {
            "factor": "confidence",
            "label": "Confidence",
            "value": confidence if confidence is not None else 0.5,
            "score": round(cv, 1),
            "weight": WEIGHTS["confidence"],
            "contribution": round(cv * WEIGHTS["confidence"], 2),
            "detail": f"Confidence is {(confidence * 100 if confidence else 50):.0f}%",
        },
    ]
    return factors


def _recency_detail(discovered_at: Optional[datetime], rv: float) -> str:
    if discovered_at is None:
        return "No discovery date — assumed moderate recency"
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if discovered_at.tzinfo is None:
        from datetime import timedelta
        d = discovered_at.replace(tzinfo=timezone.utc)
    else:
        d = discovered_at
    days = (now - d).days
    if days < 0:
        return "Discovered in the future — treated as very recent"
    if days == 0:
        return "Discovered today — maximum recency score"
    if days == 1:
        return f"Discovered {days} day ago — recency score {rv:.1f}/10"
    return f"Discovered {days} days ago — recency score {rv:.1f}/10"
