"""
Comprehensive test suite for user API endpoints.

This module provides end-to-end tests for all CRUD operations on users,
including edge cases, error handling, and trace_id functionality verification.
"""

import pytest
from litestar.testing import TestClient

from app.main import app
from tests.utils import (
    assert_user_response_structure,
    assert_pagination_response_structure,
    assert_trace_id_present,
    create_test_user_data,
    HTTP_OK,
    HTTP_CREATED,
    HTTP_NOT_FOUND
)


@pytest.mark.api
def test_create_user(test_client: TestClient):
    """Test successful user creation with valid data."""
    user_data = create_test_user_data("John", "Doe", "securepassword")
    
    response = test_client.post("/users/", json=user_data)
    
    assert response.status_code == HTTP_CREATED
    data = response.json()
    
    # Verify response structure
    assert_user_response_structure(data)
    
    # Verify data matches input
    assert data["name"] == "John"
    assert data["surname"] == "Doe"
    
    # Verify trace_id is present
    assert_trace_id_present(response)


@pytest.mark.api
def test_get_users(test_client: TestClient):
    """Test retrieving paginated list of users."""
    response = test_client.get("/users/")
    
    assert response.status_code == HTTP_OK
    data = response.json()
    
    # Verify pagination response structure
    assert_pagination_response_structure(data)
    
    # Verify trace_id is present
    assert_trace_id_present(response)


@pytest.mark.api
def test_get_user_by_id(test_client: TestClient):
    """Test retrieving a specific user by ID."""
    # First create a user to retrieve
    user_data = create_test_user_data("Jane", "Smith", "password123")
    create_response = test_client.post("/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    # Then retrieve the created user
    response = test_client.get(f"/users/{user_id}")
    
    assert response.status_code == HTTP_OK
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == "Jane"
    assert data["surname"] == "Smith"
    assert_trace_id_present(response)


@pytest.mark.api
def test_get_nonexistent_user(test_client: TestClient):
    """Test error handling when requesting non-existent user."""
    response = test_client.get("/users/99999")
    
    assert response.status_code == HTTP_NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


@pytest.mark.api
def test_update_user(test_client: TestClient):
    """Test partial user update functionality."""
    # First create a user to update
    user_data = create_test_user_data("Bob", "Wilson", "oldpassword")
    create_response = test_client.post("/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    # Update only name (partial update)
    update_data = {"name": "Robert"}
    response = test_client.put(f"/users/{user_id}", json=update_data)
    
    assert response.status_code == HTTP_OK
    data = response.json()
    assert data["name"] == "Robert"  # Updated
    assert data["surname"] == "Wilson"  # Unchanged
    assert data["id"] == user_id  # Unchanged
    assert_trace_id_present(response)


@pytest.mark.api
def test_update_nonexistent_user(test_client: TestClient):
    """Test error handling when updating non-existent user."""
    update_data = {"name": "Ghost"}
    response = test_client.put("/users/99999", json=update_data)
    
    assert response.status_code == HTTP_NOT_FOUND
    data = response.json()
    assert "detail" in data


@pytest.mark.api
def test_delete_user(test_client: TestClient):
    """Test user deletion functionality."""
    # First create a user to delete
    user_data = create_test_user_data("Alice", "Brown", "password456")
    create_response = test_client.post("/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    # Delete the user
    response = test_client.delete(f"/users/{user_id}")
    
    assert response.status_code == HTTP_OK
    data = response.json()
    assert "message" in data
    assert str(user_id) in data["message"]
    
    # Verify user is actually deleted
    get_response = test_client.get(f"/users/{user_id}")
    assert get_response.status_code == HTTP_NOT_FOUND


@pytest.mark.api
def test_delete_nonexistent_user(test_client: TestClient):
    """Test error handling when deleting non-existent user."""
    response = test_client.delete("/users/99999")
    
    assert response.status_code == HTTP_NOT_FOUND
    data = response.json()
    assert "detail" in data


@pytest.mark.api
def test_trace_id_header(test_client: TestClient):
    """Test that trace_id functionality works correctly."""
    response = test_client.get("/users/")
    
    # Use utility function to verify trace_id
    trace_id = assert_trace_id_present(response)
    assert isinstance(trace_id, str)
    assert len(trace_id) > 0


@pytest.mark.api
def test_pagination(test_client: TestClient, multiple_users):
    """Test pagination functionality."""
    # Test first page
    response = test_client.get("/users/?page=1&per_page=2")
    assert response.status_code == HTTP_OK
    data = response.json()
    assert_pagination_response_structure(data)
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert len(data["users"]) <= 2
    
    # Test second page
    response = test_client.get("/users/?page=2&per_page=2")
    assert response.status_code == HTTP_OK
    data = response.json()
    assert data["page"] == 2


@pytest.mark.api
def test_create_user_missing_fields(test_client: TestClient):
    """Test user creation with missing required fields."""
    # Missing surname
    response = test_client.post("/users/", json={"name": "John", "password": "pass"})
    assert response.status_code == 400  # Validation error (LiteStar uses 400)
    
    # Missing name
    response = test_client.post("/users/", json={"surname": "Doe", "password": "pass"})
    assert response.status_code == 400  # Validation error (LiteStar uses 400)
    
    # Missing password
    response = test_client.post("/users/", json={"name": "John", "surname": "Doe"})
    assert response.status_code == 400  # Validation error (LiteStar uses 400)
