"""
triage_engine.py — LLM-powered context analysis for false positive reduction.

Implements the TriageEngine described in issue #1719: a secondary validation
layer that intercepts AST/regex-based static analysis findings before they
reach the user, extracts the surrounding code context (snippet, variable
definitions, data flow hints), and asks an LLM to judge whether the finding
is a true or false positive, with a short rationale and remediation note.

Design mirrors ai_summary.py:
  - Opt-in and OFF by default (config.settings.triage_engine_enabled).
  - Uses any OpenAI-compatible endpoint (OpenAI, Ollama, local LLM, etc).
  - Fails open: any error (missing package, network failure, malformed
    response) leaves the original finding untouched rather than blocking
    the scan pipeline or discarding data.
  - Never sends secrets/credentials extracted from evidence to the LLM
    verbatim beyond what's already present in the finding's own metadata;
    callers remain responsible for redaction upstream (see redaction.py).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[misc,assignment]


# How many lines of surrounding source to pull above/below the flagged line
# when a readable source file is available locally.
_CONTEXT_WINDOW = 6

# Categories that AST/regex-based static analysis plugins report under.
# Only findings in these categories are eligible for triage by default —
# this keeps the (costlier) LLM call scoped to the class of finding the
# feature was built for, rather than every scanner result.
_DEFAULT_ELIGIBLE_CATEGORIES = {"code security", "static analysis", "sast"}

_VALID_VERDICTS = {"true_positive", "false_positive", "needs_review"}


def is_eligible_for_triage(
    finding: Dict[str, Any],
    *,
    eligible_categories: Optional[List[str]] = None,
    min_confidence_to_skip: float = 0.9,
) -> bool:
    """
    Decide whether a finding should be sent through LLM triage.

    Findings are skipped (left as-is) when they:
      - already carry a triage verdict (idempotent — don't re-triage),
      - fall outside the configured eligible categories (non-SAST findings
        such as network/recon observations gain little from this analysis
        and would just add latency/cost), or
      - already have a high computed confidence score, since those findings
        are already well corroborated and re-analysis adds little value.
    """
    if finding.get("triage_verdict"):
        return False

    category = str(finding.get("category") or "").strip().lower()
    categories = {c.strip().lower() for c in (eligible_categories or _DEFAULT_ELIGIBLE_CATEGORIES)}
    if category not in categories:
        return False

    confidence = finding.get("confidence")
    if isinstance(confidence, (int, float)) and confidence >= min_confidence_to_skip:
        return False

    return True


def extract_code_context(finding: Dict[str, Any], *, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract the surrounding code context for a static-analysis finding.

    Looks for a file path and line number in the finding's metadata (the
    shape produced by plugins such as code_analyzer/semgrep_scanner) and,
    when the source file is readable on disk, pulls a small window of
    lines around the flagged line. Falls back to whatever snippet/proof
    text the plugin already captured when the file can't be read (e.g. the
    scan ran in a different environment than the triage step).
    """
    metadata = finding.get("metadata") if isinstance(finding.get("metadata"), dict) else {}
    file_path = str(metadata.get("file") or metadata.get("filename") or "").strip()
    try:
        line_no = int(metadata.get("line") or metadata.get("line_number") or 0)
    except (TypeError, ValueError):
        line_no = 0

    context: Dict[str, Any] = {
        "file": file_path,
        "line": line_no,
        "snippet": "",
        "variables": _extract_variable_hints(finding),
    }

    if not file_path or not line_no:
        context["snippet"] = str(finding.get("proof") or finding.get("description") or "").strip()
        return context

    candidate = Path(repo_root) / file_path if repo_root else Path(file_path)
    try:
        if candidate.is_file():
            lines = candidate.read_text(errors="replace").splitlines()
            start = max(0, line_no - 1 - _CONTEXT_WINDOW)
            end = min(len(lines), line_no + _CONTEXT_WINDOW)
            context["snippet"] = "\n".join(lines[start:end])
        else:
            context["snippet"] = str(finding.get("proof") or finding.get("description") or "").strip()
    except OSError as exc:
        logger.debug("triage_engine: could not read %s for context — %s", file_path, exc)
        context["snippet"] = str(finding.get("proof") or finding.get("description") or "").strip()

    return context


_VAR_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=")


def _extract_variable_hints(finding: Dict[str, Any]) -> List[str]:
    """Best-effort variable name extraction from proof/description text."""
    text = " ".join(
        str(finding.get(key) or "")
        for key in ("proof", "description", "title")
    )
    names = _VAR_RE.findall(text)
    # De-duplicate while preserving order, cap to keep prompts small.
    seen: List[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen[:10]


def _build_triage_prompt(finding: Dict[str, Any], context: Dict[str, Any]) -> str:
    title = str(finding.get("title") or "Untitled finding")
    category = str(finding.get("category") or "unknown")
    severity = str(finding.get("severity") or "unknown")
    description = str(finding.get("description") or "").strip()
    snippet = context.get("snippet") or "(no source snippet available)"
    variables = ", ".join(context.get("variables") or []) or "(none identified)"
    file_ref = context.get("file") or "(unknown file)"
    line_ref = context.get("line") or "?"

    return (
        "You are a security engineer triaging a static-analysis finding to "
        "reduce false positives. Static analysis (AST/regex pattern matching) "
        "lacks semantic understanding of data flow and business logic, so it "
        "over-flags. Use the code context below to judge whether this is a "
        "real, exploitable issue.\n\n"
        f"Finding: {title}\n"
        f"Category: {category}\n"
        f"Severity: {severity}\n"
        f"Description: {description or '(none provided)'}\n"
        f"File: {file_ref} (line {line_ref})\n"
        f"Variables referenced near the flagged line: {variables}\n"
        f"Code context:\n---\n{snippet}\n---\n\n"
        "Consider things like: is user input actually reachable here, is the "
        "value already sanitized/parameterized/escaped upstream, is this test "
        "or fixture code rather than production code, and whether the "
        "surrounding logic changes the risk.\n\n"
        "Respond with ONLY a JSON object (no markdown fences, no preamble) "
        "with exactly these keys:\n"
        '  "verdict": one of "true_positive", "false_positive", "needs_review",\n'
        '  "confidence": a number between 0 and 1,\n'
        '  "reasoning": a one or two sentence explanation grounded in the '
        "code context above,\n"
        '  "remediation": a short actionable next step (empty string if the '
        'verdict is "false_positive")'
    )


def _parse_triage_response(raw: str) -> Optional[Dict[str, Any]]:
    text = raw.strip()
    # Be tolerant of models that wrap JSON in markdown fences despite instructions.
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("triage_engine: LLM response was not valid JSON")
        return None

    verdict = str(data.get("verdict") or "").strip().lower()
    if verdict not in _VALID_VERDICTS:
        logger.warning("triage_engine: LLM returned unrecognized verdict %r", verdict)
        return None

    try:
        confidence = float(data.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return {
        "triage_verdict": verdict,
        "triage_confidence": round(confidence, 2),
        "triage_reasoning": str(data.get("reasoning") or "").strip(),
        "triage_remediation": str(data.get("remediation") or "").strip(),
    }


def triage_finding(
    finding: Dict[str, Any],
    *,
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
    repo_root: Optional[str] = None,
    timeout: float = 15.0,
) -> Optional[Dict[str, Any]]:
    """
    Run a single finding through LLM-assisted context analysis.

    Returns a dict with triage_verdict / triage_confidence / triage_reasoning
    / triage_remediation on success, or None on any failure — callers should
    treat None as "leave the finding as-is" and never let it interrupt the
    scan pipeline.
    """
    if OpenAI is None:
        logger.warning(
            "triage_engine: 'openai' package not installed. "
            "Run `pip install openai>=1.0.0` to enable AI triage."
        )
        return None

    context = extract_code_context(finding, repo_root=repo_root)
    prompt = _build_triage_prompt(finding, context)

    client_kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": timeout}
    if base_url:
        client_kwargs["base_url"] = base_url

    try:
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("triage_engine: LLM call failed — %s", exc)
        return None

    return _parse_triage_response(raw)


def triage_findings(
    findings: List[Dict[str, Any]],
    *,
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
    repo_root: Optional[str] = None,
    eligible_categories: Optional[List[str]] = None,
    min_confidence_to_skip: float = 0.9,
    timeout: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Apply LLM triage to a batch of findings in place (returns the same list
    with eligible entries annotated). Ineligible findings, and any finding
    where the LLM call fails, pass through unmodified so this can safely sit
    in front of existing report/notification code paths.
    """
    if not findings:
        return findings

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if not is_eligible_for_triage(
            finding,
            eligible_categories=eligible_categories,
            min_confidence_to_skip=min_confidence_to_skip,
        ):
            continue

        result = triage_finding(
            finding,
            model=model,
            api_key=api_key,
            base_url=base_url,
            repo_root=repo_root,
            timeout=timeout,
        )
        if not result:
            continue

        finding.update(result)
        if result["triage_verdict"] == "false_positive":
            # Surface the LLM's own reasoning as the confidence_reason so it's
            # visible in the UI/report right next to the existing confidence
            # scoring, without overwriting the analyst's own status field.
            finding["confidence_reason"] = (
                f"{finding.get('confidence_reason', '').rstrip('.')}; "
                f"AI triage: likely false positive — {result['triage_reasoning']}"
            ).strip("; ").strip()

    return findings
