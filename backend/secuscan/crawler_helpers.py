"""
Pure HTML-surface parsing helpers extracted from crawler.py.

These helpers contain no network or external dependencies and can be tested
directly without pulling in the httpx import chain.
crawler.py re-imports them so existing call sites keep working.
"""
from __future__ import annotations

from html.parser import HTMLParser
import re
from typing import Any, Dict, List


class _SurfaceParser(HTMLParser):
    """Extract links, scripts, forms, and meta generators from an HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []
        self.forms: List[Dict[str, Any]] = []
        self.scripts: List[str] = []
        self.meta_generators: List[str] = []
        self._current_form: Dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"])
        elif tag == "script" and attrs_dict.get("src"):
            self.scripts.append(attrs_dict["src"])
        elif tag == "meta":
            meta_name = attrs_dict.get("name", "").lower()
            if meta_name == "generator" and attrs_dict.get("content"):
                self.meta_generators.append(attrs_dict["content"])
        elif tag == "form":
            self._current_form = {
                "action": attrs_dict.get("action", ""),
                "method": attrs_dict.get("method", "get").lower(),
                "inputs": [],
                "id": attrs_dict.get("id", ""),
                "name": attrs_dict.get("name", ""),
            }
            self.forms.append(self._current_form)
        elif tag == "input" and self._current_form is not None:
            self._current_form["inputs"].append(
                {
                    "name": attrs_dict.get("name", ""),
                    "type": attrs_dict.get("type", "text"),
                    "value": attrs_dict.get("value", ""),
                }
            )
        elif tag in {"textarea", "select"} and self._current_form is not None:
            self._current_form["inputs"].append(
                {
                    "name": attrs_dict.get("name", ""),
                    "type": tag,
                    "value": "",
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current_form = None


def _build_headers(extra_headers: Dict[str, Any] | None = None) -> Dict[str, str]:
    """Build HTTP headers for crawler requests."""
    headers: Dict[str, str] = {
        "User-Agent": "SecuScan-Crawler/1.0",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    }
    if extra_headers:
        for key, value in extra_headers.items():
            if key and value is not None:
                headers[str(key)] = str(value)
    return headers
