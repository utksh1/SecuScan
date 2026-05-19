"""
Route-level tests for /task/start validation error responses.
Covers: consent, plugin_not_found, invalid_target, rate_limit, concurrency.
"""

from unittest.mock import AsyncMock, patch
from backend.secuscan.main import app
from fastapi.testclient import TestClient

ENDPOINT = "/api/v1/task/start"

VALID_PAYLOAD = {
    "plugin_id": "nmap",
    "inputs": {"target": "127.0.0.1"},
    "consent_granted": True,
    "preset": None,
}


def post(client, payload: dict):
    return client.post(ENDPOINT, json=payload)


def assert_error_shape(detail: dict, expected_code: str):
    assert "code" in detail, "detail missing 'code'"
    assert "message" in detail, "detail missing 'message'"
    assert detail["code"] == expected_code
    assert isinstance(detail["message"], str) and detail["message"]


class TestConsentFailure:
    def test_status_400(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "consent_granted": False})
        assert r.status_code == 400

    def test_detail_shape(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "consent_granted": False})
        assert_error_shape(r.json()["detail"], "consent_required")

    def test_no_raw_input_leaked(self, test_client):
        payload = {**VALID_PAYLOAD, "consent_granted": False, "inputs": {"target": "SENTINEL_VALUE_XYZ"}}
        r = post(test_client, payload)
        assert "SENTINEL_VALUE_XYZ" not in r.text


class TestPluginNotFound:
    def test_status_404(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "plugin_id": "definitely_not_a_real_plugin_abc123"})
        assert r.status_code == 404

    def test_detail_shape(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "plugin_id": "definitely_not_a_real_plugin_abc123"})
        assert_error_shape(r.json()["detail"], "plugin_not_found")

    def test_plugin_id_not_echoed_in_message(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "plugin_id": "definitely_not_a_real_plugin_abc123"})
        msg = r.json()["detail"].get("message", "")
        assert "definitely_not_a_real_plugin_abc123" not in msg

    def test_hints_contains_available_plugins_list(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "plugin_id": "definitely_not_a_real_plugin_abc123"})
        hints = r.json()["detail"].get("hints", {})
        assert "available_plugins" in hints
        assert isinstance(hints["available_plugins"], list)


class TestInvalidTarget:
    def test_status_400(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "inputs": {"target": "not-a-valid-target!!!@@##"}})
        assert r.status_code == 400

    def test_detail_shape(self, test_client):
        r = post(test_client, {**VALID_PAYLOAD, "inputs": {"target": "not-a-valid-target!!!@@##"}})
        assert_error_shape(r.json()["detail"], "invalid_target")

    def test_raw_target_not_in_response(self, test_client):
        sentinel = "SENTINEL_INVALID_TARGET_VALUE"
        r = post(test_client, {**VALID_PAYLOAD, "inputs": {"target": sentinel}})
        if r.status_code == 400:
            assert sentinel not in r.text


class TestRateLimitExceeded:
    @patch("backend.secuscan.routes.rate_limiter.can_execute", new_callable=AsyncMock)
    def test_status_429(self, mock_rate, test_client):
        mock_rate.return_value = (False, "rate limit exceeded")
        r = post(test_client, VALID_PAYLOAD)
        assert r.status_code == 429

    @patch("backend.secuscan.routes.rate_limiter.can_execute", new_callable=AsyncMock)
    def test_detail_shape(self, mock_rate, test_client):
        mock_rate.return_value = (False, "rate limit exceeded")
        r = post(test_client, VALID_PAYLOAD)
        assert_error_shape(r.json()["detail"], "rate_limit_exceeded")

    @patch("backend.secuscan.routes.rate_limiter.can_execute", new_callable=AsyncMock)
    def test_raw_error_msg_not_leaked(self, mock_rate, test_client):
        mock_rate.return_value = (False, "internal rate detail SENTINEL")
        r = post(test_client, VALID_PAYLOAD)
        assert "internal rate detail SENTINEL" not in r.text


class TestConcurrencyLimit:
    @patch("backend.secuscan.routes.concurrent_limiter.acquire", new_callable=AsyncMock)
    def test_status_503(self, mock_acquire, test_client):
        mock_acquire.return_value = (False, "concurrency limit hit")
        r = post(test_client, VALID_PAYLOAD)
        assert r.status_code == 503

    @patch("backend.secuscan.routes.concurrent_limiter.acquire", new_callable=AsyncMock)
    def test_detail_shape(self, mock_acquire, test_client):
        mock_acquire.return_value = (False, "concurrency limit hit")
        r = post(test_client, VALID_PAYLOAD)
        assert_error_shape(r.json()["detail"], "concurrency_limit")