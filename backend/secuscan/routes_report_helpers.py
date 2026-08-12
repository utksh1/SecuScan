"""
Pure helpers extracted from routes.py for safe import in unit tests.

These functions contain no FastAPI or database dependencies.
routes.py re-exports them so existing call sites keep working.
"""
import re
from typing import Any
from urllib.parse import urlparse


def _slugify_filename_part(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or fallback


def build_report_filename(task: Any, extension: str) -> str:
    tool = _slugify_filename_part(str(task.get("tool_name") or task.get("plugin_id") or "scan"), "scan")

    raw_target = str(task.get("target") or "")
    parsed = urlparse(raw_target if "://" in raw_target else f"//{raw_target}")
    target_source = parsed.netloc or parsed.path or raw_target
    target = _slugify_filename_part(target_source, "target")

    created_at = str(task.get("created_at") or "")
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", created_at)
    date_part = date_match.group(0) if date_match else "report"

    return f"secuscan_{tool}_{target}_{date_part}.{extension}"
