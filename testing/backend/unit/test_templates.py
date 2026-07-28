"""
Unit tests for the /api/v1/templates endpoint.
"""


class TestListTemplates:
    def test_returns_template_list(self, test_client):
        resp = test_client.get("/api/v1/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert "templates" in body
        assert len(body["templates"]) >= 5

    def test_templates_have_required_fields(self, test_client):
        resp = test_client.get("/api/v1/templates")
        templates = resp.json()["templates"]
        for tmpl in templates:
            assert tmpl["id"]
            assert tmpl["name"]
            assert tmpl["description"]
            assert tmpl["category"]
            assert tmpl["estimated_duration"]
            assert tmpl["risk_level"]
            assert isinstance(tmpl["steps"], list)
            assert len(tmpl["steps"]) > 0
            for step in tmpl["steps"]:
                assert step["tool_id"]
                assert step["tool_name"]
                assert step["description"]

    def test_templates_have_valid_steps(self, test_client):
        resp = test_client.get("/api/v1/templates")
        templates = resp.json()["templates"]
        for tmpl in templates:
            for step in tmpl["steps"]:
                assert step["tool_id"]
                assert step["tool_name"]

    def test_templates_authenticated(self, test_client):
        resp = test_client.get("/api/v1/templates")
        assert resp.status_code == 200

    def test_templates_no_auth_fails(self):
        from backend.secuscan.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/v1/templates")
        assert resp.status_code == 403
