from unittest.mock import patch
import time

from backend.secuscan.models import TaskStatus


def run_plugin_test(test_client, plugin_id, inputs, mock_output):
    """Helper to run a plugin test with mocked execution."""
    with patch("backend.secuscan.executor.TaskExecutor._execute_command") as mock_exec:
        mock_exec.return_value = (mock_output, 0)

        payload = {
            "plugin_id": plugin_id,
            "inputs": inputs,
            "consent_granted": True,
        }

        # Start task
        response = test_client.post("/api/v1/task/start", json=payload)
        assert (
            response.status_code == 200
        ), f"Failed to start {plugin_id}: {response.text}"
        task_id = response.json()["task_id"]

        # Wait for completion (since it's mocked, it should be fast)
        # In the test environment, the executor might be running in the same thread or very fast
        max_retries = 10
        for _ in range(max_retries):
            status_response = test_client.get(f"/api/v1/task/{task_id}/status")
            status = status_response.json()["status"]
            if status == TaskStatus.COMPLETED.value:
                break
            time.sleep(0.1)

        assert (
            status == TaskStatus.COMPLETED.value
        ), f"Task {task_id} did not complete for {plugin_id}"

        # Check result
        result_response = test_client.get(f"/api/v1/task/{task_id}/result")
        assert result_response.status_code == 200
        return result_response.json()


def test_uncover_schema_accessible(test_client):
    schema = test_client.get("/api/v1/plugin/uncover/schema")

    assert schema.status_code == 200


def test_uncover_parser_output(test_client):
    mock_out = """api.example.com
exposed.example.com
"""

    result = run_plugin_test(
        test_client,
        "uncover",
        {
            "query": "org:example",
            "limit": 10,
        },
        mock_out,
    )

    findings = result["structured"]["findings"]

    assert len(findings) > 0

    assert "api.example.com" in result["raw_output_excerpt"]
