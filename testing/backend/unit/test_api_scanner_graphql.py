from unittest.mock import AsyncMock

import pytest

from backend.secuscan.scanners.api_scanner import APIScanner


class MockResponse:
    def __init__(self, status_code, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


@pytest.mark.asyncio
async def test_graphql_404_response_not_classified_as_endpoint():
    scanner = APIScanner("test-task", None)

    client = AsyncMock()
    client.options.return_value = MockResponse(
        404,
        headers={"allow": "GET, POST"},
    )

    findings, endpoints = await scanner._probe_graphql(
        client,
        "https://example.com",
        allow_introspection=False,
    )

    assert endpoints == []
    assert findings == []


@pytest.mark.asyncio
async def test_graphql_200_response_classified_as_endpoint():
    scanner = APIScanner("test-task", None)

    client = AsyncMock()
    client.options.return_value = MockResponse(
        200,
        headers={"allow": "GET, POST"},
    )

    findings, endpoints = await scanner._probe_graphql(
        client,
        "https://example.com",
        allow_introspection=False,
    )

    assert len(endpoints) > 0
    assert any(item["type"] == "graphql_endpoint" for item in endpoints)
    assert any("GraphQL Endpoint Exposed" in item["title"] for item in findings)
