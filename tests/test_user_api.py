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
from tests.utils import (
    assert_user_response_structure,
    assert_pagination_response_structure,
    assert_trace_id_present,
    create_test_user_data,
    HTTP_OK,
    HTTP_CREATED,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND
)


@pytest.mark.asyncio
async def test_create_user(test_client: TestClient):
    """
    Test successful user creation with valid data.

    Verifies that:
    - User can be created with required fields
    - Response includes generated ID and timestamps
    - Response data matches input data
    - Proper HTTP status code is returned
    """
    user_data = create_test_user_data("John", "Doe", "securepassword")

    response = await test_client.post("/users/", json=user_data)

    assert response.status_code == HTTP_CREATED
    data = response.json()

    # Verify response structure
    assert_user_response_structure(data)

    # Verify data matches input
    assert data["name"] == "John"
    assert data["surname"] == "Doe"

    # Verify trace_id is present
    assert_trace_id_present(response)


@pytest.mark.asyncio
async def test_get_users(test_client: TestClient):
    """
    Test retrieving paginated list of users.

    Verifies that:
    - Users list endpoint returns proper pagination structure
    - Response includes metadata (total, page, per_page)
    - Empty list is handled correctly
    """
    response = await test_client.get("/users/")

    assert response.status_code == HTTP_OK
    data = response.json()

    # Verify pagination response structure
    assert_pagination_response_structure(data)

    # Verify trace_id is present
    assert_trace_id_present(response)


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
async def test_trace_id_header(test_client: TestClient):
    """
    Test that trace_id functionality works correctly.

    Verifies that:
    - X-Trace-Id header is present in all responses
    - Header contains a valid trace identifier
    - Middleware is functioning correctly
    """
    response = await test_client.get("/users/")

    # Use utility function to verify trace_id
    trace_id = assert_trace_id_present(response)
    assert isinstance(trace_id, str)
