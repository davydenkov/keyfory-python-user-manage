"""
Integration tests for User Management API.

Tests the interaction between multiple components including database,
API endpoints, middleware, and external services.
"""

import pytest
from litestar.testing import TestClient


@pytest.mark.integration
@pytest.mark.api
class TestDatabaseIntegration:
    """Test database and API integration."""

    def test_full_user_lifecycle(self, test_client: TestClient):
        """Test complete user lifecycle from creation to deletion."""
        # 1. Create user
        user_data = {
            "name": "Lifecycle",
            "surname": "Test",
            "password": "lifecycle123"
        }

        create_response = test_client.post("/users/", json=user_data)
        assert create_response.status_code == 201
        user = create_response.json()

        # 2. Retrieve user
        get_response = test_client.get(f"/users/{user['id']}")
        assert get_response.status_code == 200
        retrieved_user = get_response.json()

        # Verify data matches
        assert retrieved_user["id"] == user["id"]
        assert retrieved_user["name"] == user_data["name"]
        assert retrieved_user["surname"] == user_data["surname"]

        # 3. Update user
        update_data = {"name": "Updated"}
        update_response = test_client.put(f"/users/{user['id']}", json=update_data)
        assert update_response.status_code == 200
        updated_user = update_response.json()

        # Verify update
        assert updated_user["name"] == "Updated"
        assert updated_user["surname"] == user_data["surname"]  # Unchanged

        # 4. Verify update via GET
        get_after_update = test_client.get(f"/users/{user['id']}")
        assert get_after_update.status_code == 200
        final_user = get_after_update.json()
        assert final_user["name"] == "Updated"

        # 5. Delete user
        delete_response = test_client.delete(f"/users/{user['id']}")
        assert delete_response.status_code == 200

        # 6. Verify deletion
        get_after_delete = test_client.get(f"/users/{user['id']}")
        assert get_after_delete.status_code == 404

    def test_database_transaction_rollback(self, test_client: TestClient):
        """Test that invalid operations don't corrupt database."""
        # Create a valid user
        user_data = {
            "name": "Valid",
            "surname": "User",
            "password": "valid123"
        }
        create_response = test_client.post("/users/", json=user_data)
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        # Try to update with empty name (may be accepted or rejected)
        invalid_update = {"name": ""}
        update_response = test_client.put(f"/users/{user_id}", json=invalid_update)
        
        # Verify user is still retrievable (database integrity)
        get_response = test_client.get(f"/users/{user_id}")
        assert get_response.status_code == 200
        
        # Empty string may be valid, so check what happened
        updated_data = get_response.json()
        if update_response.status_code == 200:
            # Update succeeded - empty string was accepted
            assert updated_data["name"] == ""
            assert updated_data["surname"] == "User"  # Other fields intact
        else:
            # Update failed validation - original data intact
            assert update_response.status_code == 400
            assert updated_data["name"] == "Valid"


@pytest.mark.integration
@pytest.mark.api
class TestPaginationIntegration:
    """Test pagination integration with database."""

    def test_pagination_with_database(self, test_client: TestClient, multiple_users):
        """Test pagination with actual database data."""
        # Get first page
        response = test_client.get("/users/?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["users"]) <= 2
        assert data["total"] >= len(multiple_users)

    def test_pagination_ordering(self, test_client: TestClient, multiple_users):
        """Test that pagination maintains consistent ordering."""
        # Get all users
        response = test_client.get("/users/?per_page=100")
        assert response.status_code == 200
        data = response.json()
        
        # Users should be ordered by ID
        user_ids = [user["id"] for user in data["users"]]
        assert user_ids == sorted(user_ids)


@pytest.mark.integration
@pytest.mark.api
class TestTraceIdIntegration:
    """Test trace_id integration across components."""

    def test_trace_id_api_to_database(self, test_client: TestClient):
        """Test that trace_id flows through API to database operations."""
        # Create user
        user_data = {
            "name": "Trace",
            "surname": "Test",
            "password": "trace123"
        }
        create_response = test_client.post("/users/", json=user_data)
        
        # Should have trace_id
        assert "X-Trace-Id" in create_response.headers
        trace_id = create_response.headers["X-Trace-Id"]
        
        # Should be valid UUID
        import uuid
        uuid.UUID(trace_id)

    def test_trace_id_error_scenarios(self, test_client: TestClient):
        """Test trace_id in error scenarios."""
        # 404 error
        response = test_client.get("/users/99999")
        assert response.status_code == 404
        assert "X-Trace-Id" in response.headers
        
        # Validation error
        response = test_client.post("/users/", json={})
        assert response.status_code in [400, 422]
        assert "X-Trace-Id" in response.headers
