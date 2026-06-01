"""
Tests for pagination metadata in tasks list endpoint.
"""

import pytest


class TestTasksPagination:
    """Test pagination metadata for /api/v1/tasks endpoint"""

    def test_pagination_has_next_previous_fields(self, test_client):
        """Test that next and previous fields exist in response"""
        response = test_client.get("/api/v1/tasks")

        if response.status_code == 200:
            data = response.json()
            assert "pagination" in data
            pagination = data["pagination"]

            assert "next" in pagination
            assert "previous" in pagination
            assert "page" in pagination
            assert "per_page" in pagination
            assert "total_items" in pagination
            assert "total_pages" in pagination
        else:
            pytest.fail(f"API returned {response.status_code}")

    def test_default_pagination_values(self, test_client):
        """Test default page=1, per_page=25"""
        response = test_client.get("/api/v1/tasks")
        assert response.status_code == 200

        pagination = response.json()["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 25

    def test_custom_per_page(self, test_client):
        """Test that per_page parameter is respected"""
        response = test_client.get("/api/v1/tasks?page=1&per_page=10")
        assert response.status_code == 200

        pagination = response.json()["pagination"]
        assert pagination["per_page"] == 10

    @pytest.mark.parametrize(
        "qs",
        [
            "page=0",
            "page=-1",
            "per_page=0",
            "per_page=-5",
            "per_page=101",
        ],
    )
    def test_invalid_pagination_is_rejected(self, test_client, qs):
        response = test_client.get(f"/api/v1/tasks?{qs}")
        assert response.status_code == 422

    def test_first_page_previous_is_null(self, test_client):
        """Test that previous is None on first page"""
        response = test_client.get("/api/v1/tasks?page=1&per_page=10")
        assert response.status_code == 200

        pagination = response.json()["pagination"]
        assert pagination["previous"] is None

    def test_next_url_preserves_filters(self, test_client):
        """Test that next URL keeps filter parameters"""
        response = test_client.get(
            "/api/v1/tasks?page=1&per_page=5&status=completed&plugin_id=nmap"
        )
        assert response.status_code == 200

        data = response.json()
        next_url = data["pagination"]["next"]

        if next_url:
            assert "per_page=5" in next_url
            assert "status=completed" in next_url
            assert "plugin_id=nmap" in next_url
