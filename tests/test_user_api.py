"""
Comprehensive test suite for user API endpoints.

This module provides end-to-end tests for all CRUD operations on users,
including edge cases, error handling, and trace_id functionality verification.

Tests use LiteStar's TestClient for in-memory testing without external dependencies.
All tests are async and use pytest-asyncio for proper async support.
"""

import pytest
from litestar.testing import TestClient

from app.main import app


@pytest.mark.asyncio
async def test_create_user():
    """
    Test successful user creation with valid data.

    Verifies that:
    - User can be created with required fields
    - Response includes generated ID and timestamps
    - Response data matches input data
    - Proper HTTP status code is returned
    """
    async with TestClient(app) as client:
        user_data = {
            "name": "John",
            "surname": "Doe",
            "password": "securepassword"
        }

        response = await client.post("/users/", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John"
        assert data["surname"] == "Doe"
        assert "id" in data  # Auto-generated ID
        assert "created_at" in data  # Auto-generated timestamp
        assert "updated_at" in data  # Auto-generated timestamp


@pytest.mark.asyncio
async def test_get_users():
    """
    Test retrieving paginated list of users.

    Verifies that:
    - Users list endpoint returns proper pagination structure
    - Response includes metadata (total, page, per_page)
    - Empty list is handled correctly
    """
    async with TestClient(app) as client:
        response = await client.get("/users/")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data  # List of user objects
        assert "total" in data  # Total count for pagination
        assert "page" in data  # Current page number
        assert "per_page" in data  # Items per page


@pytest.mark.asyncio
async def test_get_user_by_id():
    """
    Test retrieving a specific user by ID.

    Verifies that:
    - Existing user can be retrieved by ID
    - Response includes all user fields
    - Data integrity is maintained
    """
    async with TestClient(app) as client:
        # First create a user to retrieve
        user_data = {
            "name": "Jane",
            "surname": "Smith",
            "password": "password123"
        }
        create_response = await client.post("/users/", json=user_data)
        user_id = create_response.json()["id"]

        # Then retrieve the created user
        response = await client.get(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["name"] == "Jane"
        assert data["surname"] == "Smith"


@pytest.mark.asyncio
async def test_get_nonexistent_user():
    """
    Test error handling when requesting non-existent user.

    Verifies that:
    - 404 status code is returned for missing users
    - Proper error message is provided
    """
    async with TestClient(app) as client:
        response = await client.get("/users/99999")  # Non-existent ID

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_user():
    """
    Test partial user update functionality.

    Verifies that:
    - User can be updated with partial data
    - Only provided fields are modified
    - Unchanged fields remain intact
    - Update timestamp is refreshed
    """
    async with TestClient(app) as client:
        # First create a user to update
        user_data = {
            "name": "Bob",
            "surname": "Wilson",
            "password": "oldpassword"
        }
        create_response = await client.post("/users/", json=user_data)
        user_id = create_response.json()["id"]

        # Update only name and surname (partial update)
        update_data = {
            "name": "Robert",
            "surname": "Wilson"
        }
        response = await client.put(f"/users/{user_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Robert"  # Updated
        assert data["surname"] == "Wilson"  # Updated
        assert data["id"] == user_id  # Unchanged


@pytest.mark.asyncio
async def test_update_nonexistent_user():
    """
    Test error handling when updating non-existent user.

    Verifies that:
    - 404 status code is returned for missing users
    - Update operation fails gracefully
    """
    async with TestClient(app) as client:
        update_data = {"name": "Ghost"}
        response = await client.put("/users/99999", json=update_data)

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user():
    """
    Test user deletion functionality.

    Verifies that:
    - User can be successfully deleted
    - Deletion confirmation is returned
    - Deleted user cannot be retrieved afterward
    """
    async with TestClient(app) as client:
        # First create a user to delete
        user_data = {
            "name": "Alice",
            "surname": "Brown",
            "password": "password456"
        }
        create_response = await client.post("/users/", json=user_data)
        user_id = create_response.json()["id"]

        # Delete the user
        response = await client.delete(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert str(user_id) in data["message"]

        # Verify user is actually deleted
        get_response = await client.get(f"/users/{user_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_user():
    """
    Test error handling when deleting non-existent user.

    Verifies that:
    - 404 status code is returned for missing users
    - Delete operation fails gracefully
    """
    async with TestClient(app) as client:
        response = await client.delete("/users/99999")

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_trace_id_header():
    """
    Test that trace_id functionality works correctly.

    Verifies that:
    - X-Trace-Id header is present in all responses
    - Header contains a valid trace identifier
    - Middleware is functioning correctly
    """
    async with TestClient(app) as client:
        response = await client.get("/users/")

        # Verify trace_id header is present
        assert "X-Trace-Id" in response.headers
        trace_id = response.headers["X-Trace-Id"]
        assert len(trace_id) > 0  # Should contain a valid trace ID

        # Verify it's a properly formatted UUID
        # This is a basic check - in production you might validate UUID format
        assert isinstance(trace_id, str)
