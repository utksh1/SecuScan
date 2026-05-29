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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_risk_score(
    severity: str,
    exploitability: Optional[float] = None,
    asset_exposure: Optional[str] = None,
    discovered_at: Optional[datetime] = None,
    confidence: Optional[float] = None,
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
    """
    sv = _severity_score(severity)
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
        risk_score = compute_risk_score(severity, exploitability, asset_exposure, discovered_at, confidence)

    sv = _severity_score(severity)
    ev = _clamp(exploitability if exploitability is not None else 5.0)
    av = ASSET_EXPOSURE_MAP.get(asset_exposure.lower() if asset_exposure else None, 5.0)
    rv = _recency_score(discovered_at)
    cv = _confidence_score(confidence)

    factors = [
        {
            "factor": "severity",
            "label": "Severity",
            "value": severity,
            "score": round(sv, 1),
            "weight": WEIGHTS["severity"],
            "contribution": round(sv * WEIGHTS["severity"], 2),
            "detail": f"Severity is {severity} ({sv:.1f}/10)",
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
