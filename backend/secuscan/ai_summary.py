"""
ai_summary.py — LLM-powered executive summary generation for SecuScan reports.

Opt-in feature: returns an empty string when disabled or when the openai
package is not installed. Zero impact on existing report behaviour.

Supports any OpenAI-compatible endpoint:
  - OpenAI:  leave AI_SUMMARY_BASE_URL blank
  - Ollama:  AI_SUMMARY_BASE_URL=http://localhost:11434/v1
  - Any other local / cloud LLM with a /v1/chat/completions endpoint
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)

# Top-level import so the symbol can be patched in tests.
# If openai is not installed this will be None and generate_summary() handles it.
try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[misc,assignment]

def _build_prompt(findings: list[dict]) -> str:
    """Build a privacy-safe prompt from aggregate finding metadata only.

    Per issue #640, the prompt contains ONLY non-identifying metadata —
    total count, severity distribution, and vulnerability categories.
    Finding titles, hostnames, IPs, URLs, and credentials are NEVER sent to
    the LLM, so no per-finding free text can leak to a third-party endpoint.
    """
    total = len(findings)

    severity_counts: Counter = Counter()
    categories: Counter = Counter()

    for f in findings:
        sev = str(f.get("severity", "unknown")).lower()
        severity_counts[sev] += 1
        cat = str(f.get("category") or f.get("type") or "general")
        categories[cat] += 1

    sev_summary = ", ".join(
        f"{count} {sev}" for sev, count in severity_counts.most_common()
    )
    top_cats = ", ".join(cat for cat, _ in categories.most_common(5))

    return (
        "You are a cybersecurity analyst writing an executive summary for a "
        "security scan report.\n\n"
        "Scan statistics:\n"
        f"- Total findings: {total}\n"
        f"- Severity breakdown: {sev_summary if sev_summary else 'none recorded'}\n"
        f"- Top vulnerability categories: {top_cats if top_cats else 'general'}\n\n"
        "Write a concise 3-5 sentence executive summary suitable for "
        "non-technical stakeholders. Focus on: overall risk posture, the most "
        "important issues to address first, and one recommended next step. "
        "Do not mention hostnames, IP addresses, or credentials. "
        "Plain text only — no bullet points, no markdown."
    )


def generate_summary(
    findings: list[dict],
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
    timeout: float = 15.0,
) -> str:
    """Generate an LLM executive summary from scan findings.

    Args:
        findings: List of normalised finding dicts from a completed scan.
        model:    Model name e.g. ``"gpt-4o-mini"`` or ``"llama3"``.
        api_key:  API key for the OpenAI-compatible endpoint.
        base_url: Optional base URL override for non-OpenAI providers.
        timeout:  HTTP timeout in seconds (default 15). Prevents LLM calls
                  from stalling report generation.

    Returns:
        A plain-text executive summary string, or ``""`` on any failure so
        that callers always get a safe value to embed in reports.
    """
    if not findings:
        return ""

    if OpenAI is None:
        logger.warning(
            "ai_summary: 'openai' package not installed. "
            "Run `pip install openai>=1.0.0` to enable AI summaries."
        )
        return ""

    prompt = _build_prompt(findings)
    client_kwargs: dict = {"api_key": api_key, "timeout": timeout}
    if base_url:
        client_kwargs["base_url"] = base_url

    try:
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,
        )
        summary = response.choices[0].message.content or ""
        return summary.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_summary: LLM call failed — %s", exc)
        return ""