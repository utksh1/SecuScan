import pytest
from httpx import AsyncClient
from backend.secuscan.models import Finding
from typing import Dict, Any

@pytest.mark.asyncio
async def test_create_ticket_missing_provider(client: AsyncClient):
    finding = {
        "id": "123",
        "task_id": "task-1",
        "title": "SQL Injection",
        "description": "Found SQLi",
        "remediation": "Use prepared statements",
        "severity": "critical",
        "category": "Injection",
        "target": "http://example.com"
    }

    response = await client.post("/api/v1/integrations/ticket", json={
        "provider": "unknown_provider",
        "finding": finding
    })

    assert response.status_code == 400
    assert "Unsupported provider" in response.text

@pytest.mark.asyncio
async def test_create_ticket_missing_credentials(client: AsyncClient):
    finding = {
        "id": "123",
        "task_id": "task-1",
        "title": "SQL Injection",
        "description": "Found SQLi",
        "remediation": "Use prepared statements",
        "severity": "critical",
        "category": "Injection",
        "target": "http://example.com"
    }

    response = await client.post("/api/v1/integrations/ticket", json={
        "provider": "jira",
        "finding": finding
    })

    assert response.status_code == 400
    assert "Missing integration configuration" in response.text
