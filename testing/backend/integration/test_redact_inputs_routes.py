"""
Integration tests verifying that task inputs containing sensitive values
(api_key, token, password, private_key) are never returned in plain text
by the list, status, or result API endpoints.
"""

import time
from unittest.mock import patch

from backend.secuscan.models import TaskStatus


SENSITIVE_INPUTS = {
    "url": "http://127.0.0.1:8000",
    "api_key": "supersecret_api_key_value",
    "token": "supersecret_token_value_1234",
    "password": "supersecret_password_99",
    "private_key": "supersecret_private_key_pem",
}

SENSITIVE_VALUES = [
    SENSITIVE_INPUTS["api_key"],
    SENSITIVE_INPUTS["token"],
    SENSITIVE_INPUTS["password"],
    SENSITIVE_INPUTS["private_key"],
]


def _start_task_with_sensitive_inputs(test_client) -> str:
    """Start a task carrying all four sensitive input fields and return the task_id."""
    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = ("Mocked output", 0)

        payload = {
            "plugin_id": "http_inspector",
            "preset": "quick",
            "inputs": SENSITIVE_INPUTS,
            "consent_granted": True,
        }
        resp = test_client.post("/api/v1/task/start", json=payload)
        assert resp.status_code == 200, f"Task start failed: {resp.text}"
        task_id = resp.json()["task_id"]

        # Give the executor time to complete
        time.sleep(0.3)

    return task_id


def _assert_no_secrets_in_response(data: dict | list | str, label: str = ""):
    """Recursively assert that none of the known secret strings appear in data."""
    text = str(data)
    for secret in SENSITIVE_VALUES:
        assert secret not in text, (
            f"Secret '{secret}' was found in {label} response body.\n"
            f"Full response: {text}"
        )


class TestRedactInputsRoutes:
    """Route-level tests proving inputs redaction is applied consistently."""

    def test_status_endpoint_does_not_expose_sensitive_inputs(self, test_client):
        """GET /api/v1/task/{id}/status must not return raw api_key, token, password, or private_key."""
        task_id = _start_task_with_sensitive_inputs(test_client)

        resp = test_client.get(f"/api/v1/task/{task_id}/status")
        assert resp.status_code == 200
        _assert_no_secrets_in_response(resp.json(), label="status")

    def test_result_endpoint_does_not_expose_sensitive_inputs(self, test_client):
        """GET /api/v1/task/{id}/result must not return raw sensitive input values."""
        task_id = _start_task_with_sensitive_inputs(test_client)

        resp = test_client.get(f"/api/v1/task/{task_id}/result")
        assert resp.status_code == 200
        _assert_no_secrets_in_response(resp.json(), label="result")

    def test_list_endpoint_does_not_expose_sensitive_inputs(self, test_client):
        """GET /api/v1/tasks must not expose raw sensitive input values in the task list."""
        _start_task_with_sensitive_inputs(test_client)

        resp = test_client.get("/api/v1/tasks")
        assert resp.status_code == 200
        _assert_no_secrets_in_response(resp.json(), label="task list")

    def test_status_endpoint_returns_redacted_placeholder(self, test_client):
        """The status response inputs field must contain [REDACTED] for sensitive keys."""
        task_id = _start_task_with_sensitive_inputs(test_client)

        resp = test_client.get(f"/api/v1/task/{task_id}/status")
        assert resp.status_code == 200
        body = resp.json()

        inputs = body.get("inputs", {})
        if inputs:
            # If the response includes an inputs field, sensitive keys must be [REDACTED]
            for key in ("api_key", "token", "password", "private_key"):
                if key in inputs:
                    assert inputs[key] == "[REDACTED]", (
                        f"Expected [REDACTED] for key '{key}', got: {inputs[key]!r}"
                    )

    def test_non_sensitive_inputs_pass_through_unchanged(self, test_client):
        """The 'url' (non-sensitive) input value must still be accessible in responses."""
        task_id = _start_task_with_sensitive_inputs(test_client)

        resp = test_client.get(f"/api/v1/task/{task_id}/status")
        assert resp.status_code == 200
        body = resp.json()

        # url is not a sensitive key and must not be redacted
        inputs = body.get("inputs", {})
        if inputs and "url" in inputs:
            assert inputs["url"] == SENSITIVE_INPUTS["url"], (
                f"Non-sensitive 'url' value was unexpectedly altered: {inputs['url']!r}"
            )
