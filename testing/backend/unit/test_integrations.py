import pytest
from httpx import AsyncClient
from backend.secuscan.models import Finding
from typing import Dict, Any

def test_create_ticket_missing_provider(test_client):
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

    response = test_client.post("/api/v1/integrations/ticket", json={
        "provider": "unknown_provider",
        "finding": finding
    })

    assert response.status_code == 400
    assert "Unsupported provider" in response.text

def test_create_ticket_missing_credentials(test_client):
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

    response = test_client.post("/api/v1/integrations/ticket", json={
        "provider": "jira",
        "finding": finding
    })

    assert response.status_code == 400
    assert "Missing integration configuration" in response.text
