"""
Risk scoring model with explainable finding prioritization.

Computes a composite risk score (0–10) from five factors:
  - severity      (30%)
  - exploitability (25%)
  - asset exposure (20%)
  - recency        (15%)
  - confidence     (10%)

Each factor also produces a human-readable explanation entry.
"""

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
    "high": 1.25,        # Important business function
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
    """Map severity label to a numeric 0–10 value."""
    return SEVERITY_MAP.get(severity.lower(), 0.5)


def _recency_score(discovered_at: Optional[datetime]) -> float:
    """Score recency (10 = today, down to 0 for very old)."""
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
    """Map confidence 0–1 to 0–10. Default 0.5 → 5.0."""
    if confidence is None:
        return 5.0
    return max(0.0, min(10.0, confidence * 10.0))


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def _system_exposure_factor(exposure_context: Optional[str]) -> float:
    """Get the exposure context multiplier for severity adjustment."""
    if exposure_context is None:
        return 1.0
    return EXPOSURE_CONTEXT_MAP.get(exposure_context.lower(), 1.0)


def _business_criticality_factor(criticality: Optional[str]) -> float:
    """Get the business criticality multiplier for severity adjustment."""
    if criticality is None:
        return 1.0
    return CRITICALITY_MAP.get(criticality.lower(), 1.0)


def _contextual_severity_score(
    base_severity: float,
    exposure_context: Optional[str] = None,
    business_criticality: Optional[str] = None,
    custom_override: Optional[float] = None,
) -> float:
    """
    Calculate context-aware severity score.

    Accounts for system exposure (public/private/internal) and business
    criticality (data sensitivity, user count) to provide more accurate
    prioritization beyond raw CVSS score.

    Parameters
    ----------
    base_severity : float
        Base severity score 0-10 (from CVSS)
    exposure_context : str or None
        System exposure: 'public', 'internet_facing', 'internal', 'private'
    business_criticality : str or None
        Business impact: 'critical', 'high', 'medium', 'low'
    custom_override : float or None
        Manual override (0-10). If set, bypasses calculated score.

    Returns
    -------
    float
        Context-adjusted severity score (0-10)
    """
    if custom_override is not None:
        return _clamp(custom_override)

    exposure_mult = _system_exposure_factor(exposure_context)
    criticality_mult = _business_criticality_factor(business_criticality)

    contextual_score = base_severity * exposure_mult * criticality_mult
    return _clamp(contextual_score)


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
    """
    Compute a weighted composite risk score in [0, 10].

    Parameters
    ----------
    severity : str
        One of "critical", "high", "medium", "low", "info".
    exploitability : float or None
        0–10. Defaults to 5.0 when None.
    asset_exposure : str or None
        One of "critical", "high", "medium", "low". Defaults to "medium".
    discovered_at : datetime or None
        When the finding was discovered. Defaults to 90-day-old equivalent.
    confidence : float or None
        0–1. Defaults to 0.5 when None.
    exposure_context : str or None
        System exposure: 'public', 'internet_facing', 'internal', 'private'.
        Adjusts severity by system context.
    business_criticality : str or None
        Business impact: 'critical', 'high', 'medium', 'low'.
        Adjusts severity by business function importance.
    severity_override : float or None
        Manual override for severity (0-10). Bypasses context calculation.
    """
    base_severity = _severity_score(severity)
    sv = _contextual_severity_score(
        base_severity,
        exposure_context=exposure_context,
        business_criticality=business_criticality,
        custom_override=severity_override,
    )
    ev = _clamp(exploitability if exploitability is not None else 5.0)
    av = ASSET_EXPOSURE_MAP.get(asset_exposure.lower() if asset_exposure else None, 5.0)
    rv = _recency_score(discovered_at)
    cv = _confidence_score(confidence)

    score = (
        sv * WEIGHTS["severity"]
        + ev * WEIGHTS["exploitability"]
        + av * WEIGHTS["asset_exposure"]
        + rv * WEIGHTS["recency"]
        + cv * WEIGHTS["confidence"]
    )
    return round(_clamp(score), 1)


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
    """
    Return a list of explainable factor dicts, each with:
      - factor:   short key name
      - label:    human-readable label
      - value:    raw value
      - score:    numeric sub-score (0–10)
      - weight:   contribution weight
      - contribution: weighted contribution to total
      - detail:   short explanation sentence
    """
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
    ev = _clamp(exploitability if exploitability is not None else 5.0)
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
