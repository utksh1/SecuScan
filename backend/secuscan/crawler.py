"""Lightweight authenticated crawl helpers for modular scanners."""

from __future__ import annotations

from html.parser import HTMLParser
import asyncio
import logging
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse

import httpx

from .config import settings

logger = logging.getLogger(__name__)

# HTTP statuses that trigger redirect following. httpx also follows 303/307/308
# alongside 301/302; we enumerate them explicitly because redirects are handled
# manually so every hop can be re-validated.
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


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


def _is_same_origin(a: Any, b: Any) -> bool:
    """Return True when two parsed URLs share scheme, host, and effective port.

    Mirrors the same-origin definition browsers use for credential handling: a
    redirect to a different scheme, host, or port is a new origin and must not
    inherit the seed's credentials.
    """
    try:
        scheme_a = (a.scheme or "").lower()
        scheme_b = (b.scheme or "").lower()
        host_a = (a.hostname or "").lower()
        host_b = (b.hostname or "").lower()
        port_a = a.port if a.port is not None else (443 if scheme_a == "https" else 80)
        port_b = b.port if b.port is not None else (443 if scheme_b == "https" else 80)
    except ValueError:
        # Malformed port on either side: treat as cross-origin so credentials
        # are never forwarded.
        return False
    return scheme_a == scheme_b and host_a == host_b and port_a == port_b


def _validate_redirect_target(url: str) -> Tuple[bool, str, str | None]:
    """Re-validate a redirect destination against the network policy.

    The seed target is validated by the executor before the scanner runs, but
    httpx-followed redirects are not. Without this check a hostile or
    compromised seed can pivot the crawler into cloud-metadata, loopback,
    private/CGNAT, or IPv6 link-local/ULA ranges that were never authorized.

    Resolves DNS up front and validates every returned IP so that the caller
    can pin the connection to the validated address, closing any
    DNS-rebinding window between validation and fetch.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, f"redirect to unsupported scheme '{parsed.scheme}'", None
    hostname = parsed.hostname
    if not hostname:
        return False, "redirect target has no hostname", None

    import socket as _socket
    try:
        addr_infos = _socket.getaddrinfo(
            hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
            proto=_socket.IPPROTO_TCP,
        )
    except OSError:
        return False, "redirect hostname could not be resolved", None

    from .network_policy import get_policy_engine

    try:
        engine = get_policy_engine()
    except Exception as exc:
        logger.warning("Redirect target validation failed for %s: %s", url, exc)
        return False, "redirect target could not be validated", None

    validated_ip: str | None = None
    for _family, _stype, _proto, _cname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        try:
            allowed, reason, _ = engine.check_access(
                dest_ip=ip_str,
                dest_hostname=hostname,
                plugin_id="crawler",
                task_id="crawler-redirect",
            )
        except Exception as exc:
            logger.warning("Redirect target validation failed for %s: %s", url, exc)
            return False, "redirect target could not be validated", None
        if not allowed:
            return False, reason, None
        if validated_ip is None:
            validated_ip = ip_str

    if validated_ip is None:
        return False, "redirect target did not resolve to any address", None
    return True, "Allowed", validated_ip


async def crawl_target(
    url: str,
    *,
    timeout: int = 10,
    cookies: Dict[str, str] | None = None,
    extra_headers: Dict[str, Any] | None = None,
    max_redirects: int = 10,
    max_size: int = 5 * 1024 * 1024,
) -> Dict[str, Any]:
    """Fetch a target and normalize discovered links/forms/scripts/API hints.

    Redirects are followed manually rather than by httpx's automatic handling
    so every hop is re-validated:

    - Each redirect destination is checked against the network policy before
      it is fetched, closing the SSRF gap where a hostile seed pivots the
      crawler into internal or metadata-only networks that were never
      authorized (active when ``enforce_network_policy`` is enabled, matching
      how the executor validates the seed target).
    - Credentials supplied via ``extra_headers``/``cookies`` are only sent to
      the seed origin; they are stripped on any cross-origin redirect so vault
      credentials cannot be exfiltrated to an attacker-controlled host.
    """
    base_headers = _build_headers(None)
    seed_origin = urlparse(url)
    redirect_chain: List[Dict[str, Any]] = []
    current_url = url
    redirects_followed = 0
    final_response: httpx.Response | None = None
    body_bytes = b""
    response_headers: Dict[str, str] = {}
    set_cookie_headers: List[str] = []
    forward_credentials = True

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        headers=base_headers,
        verify=settings.verify_ssl,
    ) as client:
        for _ in range(max_redirects + 1):
            if not _is_same_origin(seed_origin, urlparse(current_url)):
                forward_credentials = False

            hop_headers = dict(base_headers)
            if forward_credentials and extra_headers:
                for key, value in extra_headers.items():
                    if key and value is not None:
                        hop_headers[str(key)] = str(value)
            hop_cookies = dict(cookies or {}) if forward_credentials else {}

            # Pin the connection address for redirect hops to prevent
            # DNS-rebinding: the hostname is resolved once for policy
            # validation and the same IP is used for the actual fetch.
            pinned_url = current_url
            pinned_headers = dict(hop_headers)

            if redirects_followed > 0 and settings.enforce_network_policy:
                allowed, reason, validated_ip = await asyncio.to_thread(
                    _validate_redirect_target, current_url
                )
                if not allowed:
                    raise ValueError(
                        f"Redirect to {current_url} rejected by network policy: {reason}"
                    )
                if validated_ip:
                    parsed_hop = urlparse(current_url)
                    hop_host = parsed_hop.hostname
                    new_netloc = (
                        f"[{validated_ip}]" if ":" in validated_ip else validated_ip
                    )
                    if parsed_hop.port:
                        new_netloc = f"{new_netloc}:{parsed_hop.port}"
                    pinned_url = urlunparse((
                        parsed_hop.scheme,
                        new_netloc,
                        parsed_hop.path,
                        parsed_hop.params,
                        parsed_hop.query,
                        parsed_hop.fragment,
                    ))
                    pinned_headers["Host"] = hop_host

            async with client.stream(
                "GET", pinned_url, headers=pinned_headers, cookies=hop_cookies
            ) as response:
                # Check Content-Length header if present
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        cl_val = int(content_length)
                    except ValueError:
                        cl_val = 0
                    if cl_val > max_size:
                        raise ValueError(f"Response size exceeds limit of {max_size} bytes")

                # Read response in chunks to enforce size limit
                body_chunks: List[bytes] = []
                bytes_read = 0
                async for chunk in response.aiter_bytes():
                    bytes_read += len(chunk)
                    if bytes_read > max_size:
                        raise ValueError(f"Response size exceeds limit of {max_size} bytes")
                    body_chunks.append(chunk)
                hop_body = b"".join(body_chunks)

                status = response.status_code
                location = response.headers.get("location")
                if status in _REDIRECT_STATUSES and location:
                    redirect_chain.append(
                        {
                            "url": str(response.url),
                            "status_code": status,
                            "location": location,
                        }
                    )
                    if redirects_followed >= max_redirects:
                        raise httpx.TooManyRedirects(
                            f"Exceeded maximum redirects ({max_redirects})",
                            request=response.request,
                        )
                    redirects_followed += 1
                    current_url = urljoin(str(response.url), location)
                    continue

                final_response = response
                body_bytes = hop_body
                response_headers = dict(response.headers)
                set_cookie_headers = (
                    list(response.headers.get_list("set-cookie"))
                    if hasattr(response.headers, "get_list")
                    else []
                )
                break
        else:
            raise httpx.TooManyRedirects(
                f"Exceeded maximum redirects ({max_redirects})",
                request=None,
            )

    if final_response is None:
        raise httpx.TooManyRedirects(
            f"Exceeded maximum redirects ({max_redirects})",
            request=None,
        )

    body = body_bytes.decode("utf-8", errors="replace")
    parser = _SurfaceParser()
    parser.feed(body)

    base_url = str(final_response.url)
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
    headers_snapshot = response_headers
    tech_hints = _extract_tech_hints(headers_snapshot, parser.meta_generators, normalized_scripts, body)
    cms_hints = _extract_cms_hints(parser.meta_generators, body, normalized_scripts)

    return {
        "seed_url": url,
        "final_url": base_url,
        "status_code": final_response.status_code,
        "scheme": final_parsed.scheme,
        "headers": headers_snapshot,
        "set_cookie_headers": set_cookie_headers[:20],
        "redirect_chain": redirect_chain[:10],
        "tech_hints": tech_hints[:20],
        "cms_hints": cms_hints[:10],
        "pages": [{"url": base_url, "title": _extract_title(body), "content_type": response_headers.get("content-type", "")}] + [
            {"url": link, "title": "", "content_type": ""} for link in normalized_links[:100]
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
    return html[start + len("<title>"):end].strip()


def _normalize_form(page_url: str, form: Dict[str, Any]) -> Dict[str, Any]:
    inputs = form.get("inputs", []) if isinstance(form.get("inputs"), list) else []
    method = str(form.get("method") or "get").lower()
    action = urljoin(page_url, str(form.get("action") or ""))
    state_changing = method in {"post", "put", "patch", "delete"} or any(
        str(item.get("type") or "").lower() in {"password", "file", "hidden"}
        for item in inputs
        if isinstance(item, dict)
    )
    csrf_names = {"csrf", "_csrf", "csrfmiddlewaretoken", "authenticity_token", "__requestverificationtoken"}
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
        if any(token in lowered for token in ("react", "vue", "angular", "jquery", "bootstrap")):
            hints.append(script.rsplit("/", 1)[-1])
    return sorted({item.strip() for item in hints if str(item).strip()})


def _extract_cms_hints(meta_generators: List[str], body: str, scripts: List[str]) -> List[str]:
    hints: List[str] = []
    combined = " ".join(meta_generators).lower()
    if "wordpress" in combined or "wp-content" in body.lower():
        hints.append("wordpress")
    if "drupal" in combined or "/sites/default/" in body.lower():
        hints.append("drupal")
    if "joomla" in combined or any("/media/system/js/" in script.lower() for script in scripts):
        hints.append("joomla")
    return sorted(set(hints))
