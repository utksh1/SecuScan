from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx

from .base import BaseScanner
from ..crawler import crawl_target


class APIScanner(BaseScanner):
    """API discovery plus lightweight REST/GraphQL assessment."""

    COMMON_SPEC_PATHS = [
        "/openapi.json",
        "/swagger.json",
        "/v3/api-docs",
        "/api/openapi.json",
        "/swagger/v1/swagger.json",
    ]

    GRAPHQL_PATHS = ["/graphql", "/api/graphql", "/query"]
    HIGH_VALUE_TOKENS = ("/admin", "/internal", "/users", "/accounts", "/tokens", "/auth", "/config")
    RISKY_METHODS = {"put", "patch", "delete"}

    @property
    def name(self) -> str:
        return "API Scanner"

    @property
    def category(self) -> str:
        return "API Security"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        timeout = int(inputs.get("timeout") or 10)
        extra_headers = inputs.get("__extra_headers") if isinstance(inputs.get("__extra_headers"), dict) else {}
        cookies = inputs.get("__cookies") if isinstance(inputs.get("__cookies"), dict) else {}
        execution_context = inputs.get("__execution_context") if isinstance(inputs.get("__execution_context"), dict) else {}
        target_policy = inputs.get("__target_policy") if isinstance(inputs.get("__target_policy"), dict) else {}

        self.update_progress(0.1)
        crawl = await crawl_target(target, timeout=timeout, cookies=cookies, extra_headers=extra_headers)
        findings: List[Dict[str, Any]] = []
        api_hints = list(crawl.get("api_hints", []))
        endpoint_inventory: List[Dict[str, Any]] = []

        self.update_progress(0.3)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={str(k): str(v) for k, v in extra_headers.items()},
            cookies={str(k): str(v) for k, v in cookies.items()},
            verify=False,
        ) as client:
            for path in self.COMMON_SPEC_PATHS:
                url = urljoin(target.rstrip("/") + "/", path.lstrip("/"))
                document = await self._fetch_spec(client, url)
                if not document:
                    continue
                api_hints.append(url)
                spec_findings, endpoints = self._analyze_spec(url, document, target)
                findings.extend(spec_findings)
                endpoint_inventory.extend(endpoints)

            allow_graphql_introspection = bool(
                target_policy.get("allow_exploit_validation")
                and execution_context.get("validation_mode") != "detect_only"
            )
            graphql_findings, graphql_endpoints = await self._probe_graphql(
                client,
                target,
                allow_introspection=allow_graphql_introspection,
            )
            findings.extend(graphql_findings)
            endpoint_inventory.extend(graphql_endpoints)
            api_hints.extend(item["url"] for item in graphql_endpoints if item.get("url"))

            method_findings = await self._probe_api_hints(client, sorted(set(api_hints))[:30], target)
            findings.extend(method_findings)

        if crawl.get("api_hints"):
            findings.append(
                {
                    "title": "API Paths Identified from Crawl Artifacts",
                    "category": "API Discovery",
                    "severity": "low",
                    "target": target,
                    "description": "The crawl discovered API-like paths, scripts, or schema references that should be included in route inventory and authorization coverage.",
                    "validated": True,
                    "validation_method": "passive_crawl",
                    "confidence_reason": "API-like paths were observed directly in application responses and scripts.",
                    "evidence": [{"type": "url", "label": "API hint", "value": item, "source": "crawl"} for item in sorted(set(crawl.get("api_hints", [])))[:10]],
                    "references": [],
                    "metadata": {"api_hint_count": len(crawl.get("api_hints", []))},
                }
            )

        unique_hints = sorted(set(api_hints))
        endpoint_inventory = self._dedupe_endpoints(endpoint_inventory)
        self.update_progress(1.0)
        return {
            "status": "completed",
            "summary": [
                f"API discovery completed for {target}.",
                f"Collected {len(unique_hints)} API-related path hints and normalized {len(endpoint_inventory)} endpoint records.",
            ],
            "findings": findings,
            "crawl": crawl,
            "api_hints": unique_hints,
            "endpoint_inventory": endpoint_inventory,
            "rows": endpoint_inventory[:200],
        }

    async def _fetch_spec(self, client: httpx.AsyncClient, url: str) -> Dict[str, Any] | None:
        try:
            response = await client.get(url)
        except Exception:
            return None
        if response.status_code != 200 or "json" not in response.headers.get("content-type", "").lower():
            return None
        try:
            parsed = response.json()
        except Exception:
            return None
        return {"url": url, "document": parsed, "status_code": response.status_code, "content_type": response.headers.get("content-type", "")}

    def _analyze_spec(self, url: str, document_bundle: Dict[str, Any], target: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        document = document_bundle.get("document")
        if not isinstance(document, dict):
            return [], []

        findings: List[Dict[str, Any]] = [
            {
                "title": f"API Specification Exposed at {url}",
                "category": "API Discovery",
                "severity": "medium",
                "target": target,
                "description": f"A machine-readable API specification is reachable at {url}.",
                "remediation": "Ensure API documentation exposure matches the intended environment and access policy.",
                "validated": True,
                "validation_method": "http_fetch",
                "confidence_reason": "HTTP 200 response returned a machine-readable API schema document.",
                "evidence": [
                    {"type": "url", "label": "Specification URL", "value": url, "source": "openapi"},
                    {"type": "status_code", "label": "Status code", "value": document_bundle.get("status_code"), "source": "openapi"},
                ],
                "references": [],
                "metadata": {"url": url, "content_type": document_bundle.get("content_type", "")},
            }
        ]

        endpoints: List[Dict[str, Any]] = []
        paths = document.get("paths", {})
        if not isinstance(paths, dict):
            return findings, endpoints

        for path, operations in paths.items():
            if not isinstance(operations, dict):
                continue
            methods = [method.lower() for method, details in operations.items() if isinstance(details, dict)]
            if not methods:
                continue
            endpoint_url = urljoin(target.rstrip("/") + "/", str(path).lstrip("/"))
            endpoint_inventory = {
                "type": "api_endpoint",
                "url": endpoint_url,
                "path": path,
                "methods": methods,
                "source": "openapi",
            }
            endpoints.append(endpoint_inventory)
            risky = sorted(self.RISKY_METHODS.intersection(methods))
            if risky:
                findings.append(
                    {
                        "title": f"High-Impact Methods Exposed on {path}",
                        "category": "API Exposure",
                        "severity": "medium",
                        "target": target,
                        "description": f"The API specification advertises state-changing methods ({', '.join(risky).upper()}) for {path}.",
                        "remediation": "Review authorization, CSRF protections for browser-invoked routes, and route-level policy before exposure.",
                        "validated": True,
                        "validation_method": "openapi_spec_analysis",
                        "confidence_reason": "The OpenAPI document explicitly lists these methods for the route.",
                        "evidence": [
                            {"type": "endpoint", "label": "Route", "value": endpoint_url, "source": "openapi"},
                            {"type": "methods", "label": "Methods", "value": ", ".join(sorted(methods)), "source": "openapi"},
                        ],
                        "metadata": {"path": path, "methods": methods},
                    }
                )
            if any(token in path.lower() for token in self.HIGH_VALUE_TOKENS):
                findings.append(
                    {
                        "title": f"High-Value API Route Present: {path}",
                        "category": "API Exposure",
                        "severity": "low",
                        "target": target,
                        "description": "A high-value route was enumerated from the API inventory and should receive focused authorization review.",
                        "validated": True,
                        "validation_method": "openapi_route_inventory",
                        "confidence_reason": "The route was listed directly in the exposed API definition.",
                        "evidence": [{"type": "endpoint", "label": "Route", "value": endpoint_url, "source": "openapi"}],
                        "metadata": {"path": path, "methods": methods},
                    }
                )
        return findings, endpoints

    async def _probe_graphql(
        self,
        client: httpx.AsyncClient,
        target: str,
        *,
        allow_introspection: bool,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        findings: List[Dict[str, Any]] = []
        endpoints: List[Dict[str, Any]] = []
        for path in self.GRAPHQL_PATHS:
            url = urljoin(target.rstrip("/") + "/", path.lstrip("/"))
            try:
                response = await client.options(url)
            except Exception:
                continue

            allowed_methods = response.headers.get("allow", "")
            if response.status_code < 500:
                endpoints.append(
                    {
                        "type": "graphql_endpoint",
                        "url": url,
                        "path": path,
                        "methods": [item.strip().lower() for item in allowed_methods.split(",") if item.strip()],
                        "source": "graphql",
                    }
                )
            if "GET" in allowed_methods.upper() and "POST" in allowed_methods.upper():
                findings.append(
                    {
                        "title": f"GraphQL Endpoint Exposed at {path}",
                        "category": "API Exposure",
                        "severity": "low",
                        "target": target,
                        "description": "A GraphQL endpoint responded to method discovery and should be included in schema, authorization, and query-cost review.",
                        "validated": True,
                        "validation_method": "graphql_method_discovery",
                        "confidence_reason": "The endpoint responded directly to an OPTIONS request with advertised methods.",
                        "evidence": [
                            {"type": "url", "label": "Endpoint", "value": url, "source": "graphql"},
                            {"type": "methods", "label": "Allowed methods", "value": allowed_methods, "source": "graphql"},
                        ],
                        "metadata": {"url": url},
                    }
                )

            if not allow_introspection:
                continue

            try:
                gql_response = await client.post(url, json={"query": "{__schema{queryType{name}}}"})
            except Exception:
                continue
            if gql_response.status_code == 200 and "__schema" in gql_response.text:
                findings.append(
                    {
                        "title": "GraphQL Introspection Enabled",
                        "category": "API Exposure",
                        "severity": "medium",
                        "target": target,
                        "description": "GraphQL introspection responded successfully and disclosed schema metadata.",
                        "remediation": "Restrict introspection in production or ensure the endpoint is appropriately authenticated.",
                        "validated": True,
                        "validation_method": "graphql_introspection",
                        "confidence_reason": "The endpoint returned GraphQL schema metadata to an introspection query under an explicitly allowed policy.",
                        "evidence": [
                            {"type": "url", "label": "Endpoint", "value": url, "source": "graphql"},
                            {"type": "status_code", "label": "Status code", "value": gql_response.status_code, "source": "graphql"},
                        ],
                        "references": [],
                        "metadata": {"url": url},
                    }
                )
        return findings, endpoints

    async def _probe_api_hints(self, client: httpx.AsyncClient, api_hints: List[str], target: str) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for url in api_hints:
            try:
                response = await client.options(url)
            except Exception:
                continue
            allow_header = response.headers.get("allow", "")
            if not allow_header:
                continue
            methods = [item.strip().lower() for item in allow_header.split(",") if item.strip()]
            risky = sorted(self.RISKY_METHODS.intersection(methods))
            if not risky:
                continue
            findings.append(
                {
                    "title": f"State-Changing Methods Exposed on {url}",
                    "category": "API Exposure",
                    "severity": "medium" if any(token in url.lower() for token in self.HIGH_VALUE_TOKENS) else "low",
                    "target": target,
                    "description": "The endpoint advertises state-changing methods and should be reviewed for authorization and browser abuse protections.",
                    "validated": True,
                    "validation_method": "options_method_discovery",
                    "confidence_reason": "The endpoint responded directly with allowed methods via HTTP OPTIONS.",
                    "evidence": [
                        {"type": "url", "label": "Endpoint", "value": url, "source": "http_options"},
                        {"type": "methods", "label": "Allowed methods", "value": ", ".join(sorted(methods)), "source": "http_options"},
                    ],
                    "metadata": {"url": url, "methods": methods},
                }
            )
        return findings

    def _dedupe_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        staged: Dict[str, Dict[str, Any]] = {}
        for endpoint in endpoints:
            key = f"{endpoint.get('source')}::{endpoint.get('url') or endpoint.get('path')}"
            current = staged.get(key)
            if current is None:
                staged[key] = dict(endpoint)
                continue
            current_methods = set(current.get("methods", []))
            current_methods.update(endpoint.get("methods", []))
            current["methods"] = sorted(current_methods)
        return list(staged.values())
