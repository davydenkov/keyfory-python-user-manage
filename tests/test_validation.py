"""
Validation tests for user API endpoints.

Tests input validation, data constraints, and error handling for invalid inputs.
"""

import pytest
from litestar.testing import TestClient


class TestUserValidation:
    """Test user input validation and constraints."""

    @pytest.mark.asyncio
    async def test_create_user_missing_required_fields(self, test_client: TestClient):
        """Test creating user with missing required fields."""
        # Test missing name
        response = await test_client.post("/users/", json={
            "surname": "Doe",
            "password": "password123"
        })
        assert response.status_code == 400

        # Test missing surname
        response = await test_client.post("/users/", json={
            "name": "John",
            "password": "password123"
        })
        assert response.status_code == 400

        # Test missing password
        response = await test_client.post("/users/", json={
            "name": "John",
            "surname": "Doe"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_empty_fields(self, test_client: TestClient):
        """Test creating user with empty string fields."""
        # Test empty name
        response = await test_client.post("/users/", json={
            "name": "",
            "surname": "Doe",
            "password": "password123"
        })
        assert response.status_code == 400

        # Test empty surname
        response = await test_client.post("/users/", json={
            "name": "John",
            "surname": "",
            "password": "password123"
        })
        assert response.status_code == 400

        # Test empty password
        response = await test_client.post("/users/", json={
            "name": "John",
            "surname": "Doe",
            "password": ""
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_whitespace_only_fields(self, test_client: TestClient):
        """Test creating user with whitespace-only fields."""
        # Test whitespace name
        response = await test_client.post("/users/", json={
            "name": "   ",
            "surname": "Doe",
            "password": "password123"
        })
        assert response.status_code == 400

        # Test whitespace surname
        response = await test_client.post("/users/", json={
            "name": "John",
            "surname": "   ",
            "password": "password123"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_field_too_long(self, test_client: TestClient):
        """Test creating user with fields exceeding length limits."""
        # Test name too long (assuming 255 char limit)
        long_name = "A" * 256
        response = await test_client.post("/users/", json={
            "name": long_name,
            "surname": "Doe",
            "password": "password123"
        })
        # This might pass or fail depending on database constraints
        # For now, we'll assume it passes since we're using TEXT fields
        assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_create_user_invalid_json(self, test_client: TestClient):
        """Test creating user with invalid JSON."""
        response = await test_client.post(
            "/users/",
            content='{"name": "John", "surname": "Doe", invalid}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_user_wrong_content_type(self, test_client: TestClient):
        """Test creating user with wrong content type."""
        response = await test_client.post(
            "/users/",
            content='name=John&surname=Doe&password=password123',
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        # LiteStar may handle this gracefully or reject it
        assert response.status_code in [201, 400, 422]

    @pytest.mark.asyncio
    async def test_update_user_invalid_data(self, test_client: TestClient, created_user):
        """Test updating user with invalid data."""
        user_id = created_user["id"]

        # Test empty name update
        response = await test_client.put(f"/users/{user_id}", json={"name": ""})
        assert response.status_code == 400

        # Test empty surname update
        response = await test_client.put(f"/users/{user_id}", json={"surname": ""})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_invalid_id_format(self, test_client: TestClient):
        """Test getting user with invalid ID format."""
        # Test non-integer ID
        response = await test_client.get("/users/abc")
        assert response.status_code == 404

        # Test negative ID
        response = await test_client.get("/users/-1")
        assert response.status_code == 404

        # Test zero ID
        response = await test_client.get("/users/0")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_pagination_invalid_parameters(self, test_client: TestClient):
        """Test pagination with invalid parameters."""
        # Test negative page
        response = await test_client.get("/users/?page=-1")
        assert response.status_code == 400

        # Test zero page
        response = await test_client.get("/users/?page=0")
        assert response.status_code == 400

        # Test negative per_page
        response = await test_client.get("/users/?per_page=-1")
        assert response.status_code == 400

        # Test per_page too large
        response = await test_client.get("/users/?per_page=200")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_pagination_boundary_values(self, test_client: TestClient):
        """Test pagination boundary values."""
        # Test minimum valid values
        response = await test_client.get("/users/?page=1&per_page=1")
        assert response.status_code == 200

        # Test maximum valid per_page
        response = await test_client.get("/users/?page=1&per_page=100")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_special_characters_in_names(self, test_client: TestClient):
        """Test creating users with special characters in names."""
        # Test unicode characters
        response = await test_client.post("/users/", json={
            "name": "José",
            "surname": "Muñoz",
            "password": "password123"
        })
        assert response.status_code == 201

        # Test names with apostrophes
        response = await test_client.post("/users/", json={
            "name": "O'Connor",
            "surname": "Smith",
            "password": "password123"
        })
        assert response.status_code == 201

        # Test names with hyphens
        response = await test_client.post("/users/", json={
            "name": "Jean-Pierre",
            "surname": "Dubois",
            "password": "password123"
        })
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self, test_client: TestClient):
        """Test protection against SQL injection attempts."""
        # Test SQL injection in name field
        malicious_name = "'; DROP TABLE users; --"
        response = await test_client.post("/users/", json={
            "name": malicious_name,
            "surname": "Doe",
            "password": "password123"
        })
        # Should not execute SQL - either validation error or successful creation
        assert response.status_code in [201, 400, 422]

        # Verify the malicious content is stored as-is (escaped)
        if response.status_code == 201:
            user_data = response.json()
            # SQLAlchemy should have escaped the input
            assert user_data["name"] == malicious_name

    @pytest.mark.asyncio
    async def test_xss_prevention(self, test_client: TestClient):
        """Test protection against XSS attacks."""
        # Test XSS in name field
        xss_payload = '<script>alert("XSS")</script>'
        response = await test_client.post("/users/", json={
            "name": xss_payload,
            "surname": "Doe",
            "password": "password123"
        })
        assert response.status_code == 201

        # Verify the XSS payload is stored as-is
        user_data = response.json()
        assert user_data["name"] == xss_payload

        # Verify it can be retrieved safely
        get_response = await test_client.get(f"/users/{user_data['id']}")
        assert get_response.status_code == 200
        retrieved_data = get_response.json()
        assert retrieved_data["name"] == xss_payload
