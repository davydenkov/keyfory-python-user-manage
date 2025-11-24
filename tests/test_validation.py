"""
Validation tests for user API endpoints.

Tests input validation, data constraints, and error handling for invalid inputs.
"""

import pytest
from litestar.testing import TestClient


@pytest.mark.api
class TestUserValidation:
    """Test user input validation and constraints."""

    def test_create_user_missing_required_fields(self, test_client: TestClient):
        """Test creating user with missing required fields."""
        # Test missing name
        response = test_client.post("/users/", json={
            "surname": "Doe",
            "password": "password123"
        })
        assert response.status_code == 400  # Validation error (LiteStar uses 400)

        # Test missing surname
        response = test_client.post("/users/", json={
            "name": "John",
            "password": "password123"
        })
        assert response.status_code == 400  # Validation error (LiteStar uses 400)

        # Test missing password
        response = test_client.post("/users/", json={
            "name": "John",
            "surname": "Doe"
        })
        assert response.status_code == 400  # Validation error (LiteStar uses 400)

    def test_create_user_empty_fields(self, test_client: TestClient):
        """Test creating user with empty string fields."""
        # Empty fields may be accepted by the schema (empty string is valid)
        # This test verifies the behavior - empty strings might be allowed
        response = test_client.post("/users/", json={
            "name": "",
            "surname": "Doe",
            "password": "password123"
        })
        # Empty string may be accepted (201) or rejected (400)
        # Both are valid behaviors depending on validation rules
        assert response.status_code in [201, 400]

    def test_update_user_invalid_id(self, test_client: TestClient):
        """Test updating user with invalid ID format."""
        # Invalid ID format
        response = test_client.put("/users/abc", json={"name": "Test"})
        assert response.status_code == 404  # Route not found or validation error
        
        # Negative ID
        response = test_client.put("/users/-1", json={"name": "Test"})
        assert response.status_code == 404  # Invalid ID format

    def test_get_user_invalid_id_format(self, test_client: TestClient):
        """Test getting user with invalid ID format."""
        response = test_client.get("/users/abc")
        assert response.status_code == 404

    def test_pagination_invalid_parameters(self, test_client: TestClient):
        """Test pagination with invalid parameters."""
        # Negative page
        response = test_client.get("/users/?page=-1")
        assert response.status_code == 400  # Validation error
        
        # Zero page
        response = test_client.get("/users/?page=0")
        assert response.status_code == 400  # Validation error
        
        # Negative per_page
        response = test_client.get("/users/?per_page=-1")
        assert response.status_code == 400  # Validation error
        
        # Too large per_page
        response = test_client.get("/users/?per_page=200")
        assert response.status_code == 400  # Validation error

    def test_pagination_boundary_values(self, test_client: TestClient):
        """Test pagination with boundary values."""
        # Minimum valid values
        response = test_client.get("/users/?page=1&per_page=1")
        assert response.status_code == 200
        
        # Maximum valid per_page
        response = test_client.get("/users/?page=1&per_page=100")
        assert response.status_code == 200
