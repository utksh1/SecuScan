"""Lightweight authenticated crawl helpers for modular scanners."""

from __future__ import annotations

from html.parser import HTMLParser
import re
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urljoin, urlparse

import httpx


class _SurfaceParser(HTMLParser):
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
    headers: Dict[str, str] = {
        "User-Agent": "SecuScan-Crawler/1.0",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    }
    if extra_headers:
        for key, value in extra_headers.items():
            if key and value is not None:
                headers[str(key)] = str(value)
    return headers


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
    normalized_links = sorted(
        {urljoin(base_url, link) for link in parser.links if link}
    )
    normalized_scripts = sorted(
        {urljoin(base_url, script) for script in parser.scripts if script}
    )

    params = []
    for parsed_link in normalized_links:
        for key, value in parse_qsl(
            urlparse(parsed_link).query, keep_blank_values=True
        ):
            params.append({"url": parsed_link, "name": key, "sample": value})

    api_hints = []
    path_hints = []
    for candidate in normalized_links + normalized_scripts:
        lowered = candidate.lower()
        if any(
            token in lowered
            for token in ("/api/", "swagger", "openapi", "graphql", ".json")
        ):
            api_hints.append(candidate)
        path_tag = _classify_path_hint(lowered)
        if path_tag:
            path_hints.append({"url": candidate, "kind": path_tag})

    forms = [_normalize_form(base_url, form) for form in parser.forms[:50]]
    headers_snapshot = dict(response.headers)
    set_cookie_headers = (
        list(response.headers.get_list("set-cookie"))
        if hasattr(response.headers, "get_list")
        else []
    )
    tech_hints = _extract_tech_hints(
        headers_snapshot, parser.meta_generators, normalized_scripts, body
    )
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
        "pages": [
            {
                "url": base_url,
                "title": _extract_title(body),
                "content_type": response.headers.get("content-type", ""),
            }
        ]
        + [
            {"url": link, "title": "", "content_type": ""}
            for link in normalized_links[:100]
        ],
        "forms": forms,
        "scripts": normalized_scripts[:100],
        "params": params[:200],
        "api_hints": sorted(set(api_hints))[:100],
        "path_hints": path_hints[:100],
        "body_preview": body[:4000],
    }


def _extract_title(html: str) -> str:
    start = html.lower().find("<title>")
    end = html.lower().find("</title>")
    if start == -1 or end == -1 or end <= start:
        return ""
    return html[start + len("<title>") : end].strip()


def _normalize_form(page_url: str, form: Dict[str, Any]) -> Dict[str, Any]:
    inputs = form.get("inputs", []) if isinstance(form.get("inputs"), list) else []
    method = str(form.get("method") or "get").lower()
    action = urljoin(page_url, str(form.get("action") or ""))
    state_changing = method in {"post", "put", "patch", "delete"} or any(
        str(item.get("type") or "").lower() in {"password", "file", "hidden"}
        for item in inputs
        if isinstance(item, dict)
    )
    csrf_names = {
        "csrf",
        "_csrf",
        "csrfmiddlewaretoken",
        "authenticity_token",
        "__requestverificationtoken",
    }
    has_csrf_token = any(
        str(item.get("name") or "").strip().lower() in csrf_names
        for item in inputs
        if isinstance(item, dict)
    )
    password_fields = sum(
        1
        for item in inputs
        if isinstance(item, dict) and str(item.get("type") or "").lower() == "password"
    )
    return {
        **form,
        "page_url": page_url,
        "action": action,
        "state_changing": state_changing,
        "has_csrf_token": has_csrf_token,
        "password_fields": password_fields,
        "input_count": len(inputs),
    }


def _classify_path_hint(value: str) -> str | None:
    patterns = {
        "admin": ("/admin", "/administrator", "/wp-admin"),
        "login": ("/login", "/signin", "/auth", "/user/login"),
        "debug": ("/debug", "/console", "/actuator", "/_profiler"),
        "docs": ("/docs", "/swagger", "/openapi", "/redoc"),
    }
    for label, tokens in patterns.items():
        if any(token in value for token in tokens):
            return label
    return None


def _extract_tech_hints(
    headers: Dict[str, str],
    meta_generators: List[str],
    scripts: List[str],
    body: str,
) -> List[str]:
    hints: List[str] = []
    for key in ("server", "x-powered-by", "x-generator"):
        value = headers.get(key) or headers.get(key.title())
        if value:
            hints.append(str(value))
    hints.extend(meta_generators)
    body_lower = body.lower()
    if "wp-content" in body_lower:
        hints.append("WordPress")
    if "/sites/default/" in body_lower:
        hints.append("Drupal")
    if "joomla!" in body_lower or "/media/system/js/" in body_lower:
        hints.append("Joomla")
    for script in scripts:
        lowered = script.lower()
        if any(
            token in lowered
            for token in ("react", "vue", "angular", "jquery", "bootstrap")
        ):
            hints.append(script.rsplit("/", 1)[-1])
    return sorted({item.strip() for item in hints if str(item).strip()})


def _extract_cms_hints(
    meta_generators: List[str], body: str, scripts: List[str]
) -> List[str]:
    hints: List[str] = []
    combined = " ".join(meta_generators).lower()
    if "wordpress" in combined or "wp-content" in body.lower():
        hints.append("wordpress")
    if "drupal" in combined or "/sites/default/" in body.lower():
        hints.append("drupal")
    if "joomla" in combined or any(
        "/media/system/js/" in script.lower() for script in scripts
    ):
        hints.append("joomla")
    return sorted(set(hints))
