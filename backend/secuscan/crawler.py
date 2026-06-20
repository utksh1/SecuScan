"""Lightweight authenticated crawl helpers for modular scanners."""

from __future__ import annotations

from html.parser import HTMLParser
import re
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urljoin, urlparse

import httpx


# Sync helpers re-exported from import-safe module
from .crawler_helpers import (
    _SurfaceParser,
    _build_headers,
    _extract_title,
    _normalize_form,
    _classify_path_hint,
    _extract_tech_hints,
    _extract_cms_hints,
)


async def crawl_target(
    url: str,
    *,
    timeout: int = 10,
    cookies: Dict[str, str] | None = None,
    extra_headers: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Fetch a target and normalize discovered links/forms/scripts/API hints."""
    headers = _build_headers(extra_headers)
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers=headers,
        cookies=cookies or {},
        verify=False,
    ) as client:
        response = await client.get(url)

    body = response.text
    parser = _SurfaceParser()
    parser.feed(body)

    base_url = str(response.url)
    final_parsed = urlparse(base_url)
    normalized_links = sorted({urljoin(base_url, link) for link in parser.links if link})
    normalized_scripts = sorted({urljoin(base_url, script) for script in parser.scripts if script})

    params = []
    for parsed_link in normalized_links:
        for key, value in parse_qsl(urlparse(parsed_link).query, keep_blank_values=True):
            params.append({"url": parsed_link, "name": key, "sample": value})

    api_hints = []
    path_hints = []
    for candidate in normalized_links + normalized_scripts:
        lowered = candidate.lower()
        if any(token in lowered for token in ("/api/", "swagger", "openapi", "graphql", ".json")):
            api_hints.append(candidate)
        path_tag = _classify_path_hint(lowered)
        if path_tag:
            path_hints.append({"url": candidate, "kind": path_tag})

    forms = [_normalize_form(base_url, form) for form in parser.forms[:50]]
    headers_snapshot = dict(response.headers)
    set_cookie_headers = list(response.headers.get_list("set-cookie")) if hasattr(response.headers, "get_list") else []
    tech_hints = _extract_tech_hints(headers_snapshot, parser.meta_generators, normalized_scripts, body)
    cms_hints = _extract_cms_hints(parser.meta_generators, body, normalized_scripts)
    redirect_chain = [
        {
            "url": str(item.url),
            "status_code": item.status_code,
            "location": item.headers.get("location"),
        }
        for item in response.history
    ]

    return {
        "seed_url": url,
        "final_url": base_url,
        "status_code": response.status_code,
        "scheme": final_parsed.scheme,
        "headers": headers_snapshot,
        "set_cookie_headers": set_cookie_headers[:20],
        "redirect_chain": redirect_chain[:10],
        "tech_hints": tech_hints[:20],
        "cms_hints": cms_hints[:10],
        "pages": [{"url": base_url, "title": _extract_title(body), "content_type": response.headers.get("content-type", "")}] + [
            {"url": link, "title": "", "content_type": ""} for link in normalized_links[:100]
        ],
        "forms": forms,
        "scripts": normalized_scripts[:100],
        "params": params[:200],
        "api_hints": sorted(set(api_hints))[:100],
        "path_hints": path_hints[:100],
        "body_preview": body[:4000],
    }



