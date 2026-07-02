"""Local vulnerability knowledge-base helpers."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from .config import settings

logger = logging.getLogger(__name__)


_SEEDED_CPE_INDEX: Dict[str, List[Dict[str, Any]]] = {
    "cpe:/a:nginx:nginx:1.18.0": [
        {
            "cve": "CVE-2021-23017",
            "severity": "high",
            "cvss": 7.7,
            "title": "Resolver off-by-one overwrite in nginx",
            "description": "Certain nginx resolver configurations before newer releases are vulnerable to a 1-byte memory overwrite.",
            "references": [{"source": "NVD", "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-23017"}],
        }
    ],
    "cpe:/a:openbsd:openssh:8.2": [
        {
            "cve": "CVE-2020-15778",
            "severity": "medium",
            "cvss": 6.8,
            "title": "Command injection in scp client arguments",
            "description": "Affected OpenSSH releases allow command injection in some scp usage patterns.",
            "references": [{"source": "NVD", "url": "https://nvd.nist.gov/vuln/detail/CVE-2020-15778"}],
        }
    ],
    "cpe:/a:apache:http_server:2.4.49": [
        {
            "cve": "CVE-2021-41773",
            "severity": "critical",
            "cvss": 9.8,
            "title": "Path traversal and file disclosure in Apache HTTP Server",
            "description": "Apache HTTP Server 2.4.49 is vulnerable to path traversal and possible remote code execution.",
            "references": [{"source": "NVD", "url": "https://nvd.nist.gov/vuln/detail/CVE-2021-41773"}],
        }
    ],
}

_PRODUCT_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bnginx\b", re.I), "cpe:/a:nginx:nginx:{version}"),
    (re.compile(r"\bopenssh\b", re.I), "cpe:/a:openbsd:openssh:{version}"),
    (re.compile(r"\bapache(?: httpd| http server)?\b", re.I), "cpe:/a:apache:http_server:{version}"),
    (re.compile(r"\bwordpress\b", re.I), "cpe:/a:wordpress:wordpress:{version}"),
    (re.compile(r"\bdrupal\b", re.I), "cpe:/a:drupal:drupal:{version}"),
]


_cached_entries: Dict[str, List[Dict[str, Any]]] | None = None
_cached_mtime: float | None = None


class KnowledgeBase:
    """Loads local CPE/CVE intelligence without live network calls."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir or settings.knowledgebase_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> Dict[str, Any]:
        entries = self._load_entries()
        total_refs = sum(len(v) for v in entries.values())
        feed_files = sorted(path.name for path in self.data_dir.glob("*.json"))
        newest_mtime = max((path.stat().st_mtime for path in self.data_dir.glob("*.json")), default=None)
        return {
            "status": "ready",
            "source": "local-json-feeds",
            "directory": str(self.data_dir),
            "feed_files": feed_files,
            "total_cpes": len(entries),
            "total_cves": total_refs,
            "synced_at": newest_mtime,
        }

    def find_vulnerabilities(self, service: str, product: str, version: str) -> Dict[str, Any]:
        entries = self._load_entries()
        match = self._find_best_cpe_match(entries, service=service, product=product, version=version)
        if not match:
            return {"cpe": None, "cves": [], "match_strength": "none"}

        candidates = entries.get(match["cpe"], [])
        return {
            "cpe": match["cpe"],
            "cves": list(candidates),
            "match_strength": match["match_strength"],
        }

    def infer_cpe(self, service: str, product: str, version: str) -> str | None:
        entries = self._load_entries()
        match = self._find_best_cpe_match(entries, service=service, product=product, version=version)
        return match["cpe"] if match else None

    def _normalize_version(self, version: str) -> str:
        if not version:
            return ""
        match = re.search(r"\d+(?:\.\d+){0,3}", version)
        return match.group(0) if match else version.strip().lower()

    def _find_best_cpe_match(
        self,
        entries: Dict[str, List[Dict[str, Any]]],
        *,
        service: str,
        product: str,
        version: str,
    ) -> Dict[str, str] | None:
        haystack = " ".join(part for part in [service, product] if part).strip()
        if not haystack:
            return None

        normalized_version = self._normalize_version(version)
        family_matches: List[tuple[str, str]] = []
        for pattern, template in _PRODUCT_PATTERNS:
            if not pattern.search(haystack):
                continue
            exact_cpe = template.format(version=normalized_version or "unknown")
            if normalized_version and exact_cpe in entries:
                return {"cpe": exact_cpe, "match_strength": "exact"}

            family_prefix = template.format(version="").rstrip(":")
            matching_cpes = [cpe for cpe in entries.keys() if cpe.startswith(family_prefix)]
            if not matching_cpes:
                continue

            if normalized_version:
                strong = self._select_version_match(matching_cpes, normalized_version, same_minor=True)
                if strong:
                    return {"cpe": strong, "match_strength": "strong_fuzzy"}
                fuzzy = self._select_version_match(matching_cpes, normalized_version, same_minor=False)
                if fuzzy:
                    return {"cpe": fuzzy, "match_strength": "fuzzy"}

            family_matches.append((matching_cpes[0], "family"))

        if family_matches:
            cpe, match_strength = family_matches[0]
            return {"cpe": cpe, "match_strength": match_strength}
        return None

    def _select_version_match(self, cpes: List[str], normalized_version: str, *, same_minor: bool) -> str | None:
        requested_parts = normalized_version.split(".")
        for cpe in cpes:
            candidate_version = cpe.split(":")[-1]
            candidate_parts = candidate_version.split(".")
            if candidate_version == normalized_version:
                return cpe
            if same_minor:
                if len(requested_parts) >= 2 and len(candidate_parts) >= 2 and candidate_parts[:2] == requested_parts[:2]:
                    return cpe
            elif candidate_parts and requested_parts and candidate_parts[0] == requested_parts[0]:
                return cpe
        return None

    def _load_entries(self) -> Dict[str, List[Dict[str, Any]]]:
        global _cached_entries, _cached_mtime

        feed_files = sorted(self.data_dir.glob("*.json"))
        newest_mtime = max((path.stat().st_mtime for path in feed_files), default=0.0)

        if _cached_entries is not None and _cached_mtime == newest_mtime:
            return _cached_entries

        entries: Dict[str, List[Dict[str, Any]]] = {
            key: list(value) for key, value in _SEEDED_CPE_INDEX.items()
        }

        for path in feed_files:
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to load knowledge-base feed %s: %s", path, exc)
                continue

            if not isinstance(loaded, dict):
                continue

            for cpe, vuln_entries in loaded.items():
                if not isinstance(cpe, str) or not isinstance(vuln_entries, list):
                    continue
                bucket = entries.setdefault(cpe, [])
                for item in vuln_entries:
                    if isinstance(item, dict):
                        bucket.append(item)

        _cached_entries = entries
        _cached_mtime = newest_mtime
        return entries
