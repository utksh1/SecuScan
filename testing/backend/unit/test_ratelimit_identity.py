"""
Unit tests for resolve_client_identity in ratelimit.py.
"""
import pytest
from unittest.mock import MagicMock

from backend.secuscan.ratelimit import resolve_client_identity


class TestResolveClientIdentity:
    def test_x_api_key_header(self):
        request = MagicMock()
        request.headers = {"x-api-key": "secret-abc"}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "apikey:secret-abc"

    def test_x_key_header(self):
        request = MagicMock()
        request.headers = {"x-key": "secret-xyz"}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "apikey:secret-xyz"

    def test_bearer_token(self):
        request = MagicMock()
        request.headers = {"authorization": "Bearer tok123"}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "apikey:tok123"

    def test_basic_auth(self):
        request = MagicMock()
        request.headers = {"authorization": "Basic YWJjOjEyMw=="}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "apikey:YWJjOjEyMw=="

    def test_authorization_header_no_scheme(self):
        request = MagicMock()
        request.headers = {"authorization": "raw-token-456"}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "apikey:raw-token-456"

    def test_x_user_id_header(self):
        request = MagicMock()
        request.headers = {"x-user-id": "uid-99"}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "user:uid-99"

    def test_request_state_user_id_attribute(self):
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])
        request.state.user_id = "uid-42"
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "user:uid-42"

    def test_request_state_user_object_with_id_attribute(self):
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])
        request.state.user = MagicMock()
        request.state.user.id = "uid-7"
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "user:uid-7"

    def test_request_state_user_dict(self):
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])
        request.state.user = {"id": "uid-7"}
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "user:uid-7"

    def test_request_state_user_string(self):
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])
        request.state.user = "uid-string"
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "user:uid-string"

    def test_falls_back_to_client_ip(self):
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])
        request.client.host = "10.0.0.5"
        assert resolve_client_identity(request) == "ip:10.0.0.5"

    def test_x_forwarded_for_respected_for_trusted_proxy(self):
        # 127.0.0.1 is in settings.trusted_proxies
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.state = MagicMock(spec=[])
        request.client.host = "127.0.0.1"
        assert resolve_client_identity(request) == "ip:1.2.3.4"

    def test_x_forwarded_for_ignored_for_untrusted_proxy(self):
        # Non-trusted proxy: uses connection IP directly
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.state = MagicMock(spec=[])
        request.client.host = "10.9.8.7"  # not a trusted proxy
        assert resolve_client_identity(request) == "ip:10.9.8.7"

    def test_no_client_falls_back_to_localhost(self):
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])
        request.client = None
        assert resolve_client_identity(request) == "ip:127.0.0.1"
