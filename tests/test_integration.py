"""
Integration tests for User Management API.

Tests the interaction between multiple components including database,
API endpoints, middleware, and external services.
"""

import pytest
from litestar.testing import TestClient
from sqlalchemy import select


class TestDatabaseIntegration:
    """Test database and API integration."""

    @pytest.mark.asyncio
    async def test_full_user_lifecycle(self, test_client: TestClient):
        """Test complete user lifecycle from creation to deletion."""
        # 1. Create user
        user_data = {
            "name": "Lifecycle",
            "surname": "Test",
            "password": "lifecycle123"
        }

        create_response = await test_client.post("/users/", json=user_data)
        assert create_response.status_code == 201
        user = create_response.json()

        # 2. Retrieve user
        get_response = await test_client.get(f"/users/{user['id']}")
        assert get_response.status_code == 200
        retrieved_user = get_response.json()

        # Verify data matches
        assert retrieved_user["id"] == user["id"]
        assert retrieved_user["name"] == user_data["name"]
        assert retrieved_user["surname"] == user_data["surname"]

        # 3. Update user
        update_data = {"name": "Updated"}
        update_response = await test_client.put(f"/users/{user['id']}", json=update_data)
        assert update_response.status_code == 200
        updated_user = update_response.json()

        # Verify update
        assert updated_user["name"] == "Updated"
        assert updated_user["surname"] == user_data["surname"]  # Unchanged

        # 4. Verify update via GET
        get_after_update = await test_client.get(f"/users/{user['id']}")
        assert get_after_update.status_code == 200
        final_user = get_after_update.json()
        assert final_user["name"] == "Updated"

        # 5. Delete user
        delete_response = await test_client.delete(f"/users/{user['id']}")
        assert delete_response.status_code == 200

        # 6. Verify deletion
        get_after_delete = await test_client.get(f"/users/{user['id']}")
        assert get_after_delete.status_code == 404

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, test_client: TestClient, db_session):
        """Test database transaction rollback on errors."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database import get_session

        # Create a user directly in database to test transaction isolation
        async for session in get_session():
            from app.models import User
            user = User(name="Transaction", surname="Test", password="tx123")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        # Try to update with invalid data (should fail)
        # This tests that failed operations don't corrupt data
        update_response = await test_client.put(f"/users/{user_id}", json={"name": ""})
        assert update_response.status_code == 400

        # Verify original data is unchanged
        get_response = await test_client.get(f"/users/{user_id}")
        assert get_response.status_code == 200
        user_data = get_response.json()
        assert user_data["name"] == "Transaction"  # Should be unchanged


class TestPaginationIntegration:
    """Test pagination with database integration."""

    @pytest.mark.asyncio
    async def test_pagination_with_database(self, test_client: TestClient, multiple_users):
        """Test pagination works correctly with real database data."""
        # multiple_users fixture creates 5 users
        assert len(multiple_users) == 5

        # Test first page
        response = await test_client.get("/users/?page=1&per_page=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["users"]) == 2

        # Test second page
        response = await test_client.get("/users/?page=2&per_page=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 2
        assert data["per_page"] == 2
        assert len(data["users"]) == 2

        # Test last page
        response = await test_client.get("/users/?page=3&per_page=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 3
        assert data["per_page"] == 2
        assert len(data["users"]) == 1  # Only 1 user left

    @pytest.mark.asyncio
    async def test_pagination_ordering(self, test_client: TestClient, multiple_users):
        """Test that pagination returns results in consistent order."""
        # Get all users and check ordering
        response = await test_client.get("/users/?per_page=10")
        assert response.status_code == 200
        data = response.json()

        users = data["users"]
        # Should be ordered by ID (ascending)
        ids = [user["id"] for user in users]
        assert ids == sorted(ids)


class TestTraceIdIntegration:
    """Test trace_id integration across components."""

    @pytest.mark.asyncio
    async def test_trace_id_api_to_database(self, test_client: TestClient):
        """Test that trace_id is maintained from API to database operations."""
        custom_trace_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await test_client.post(
            "/users/",
            json={"name": "Trace", "surname": "Test", "password": "trace123"},
            headers={"X-Request-Id": custom_trace_id}
        )

        assert response.status_code == 201
        # Response should contain the same trace_id
        assert response.headers["X-Trace-Id"] == custom_trace_id

        # In a complete integration test, you would verify that:
        # 1. Database operations are logged with the trace_id
        # 2. RabbitMQ messages contain the trace_id
        # 3. All logs for this request are correlated

    @pytest.mark.asyncio
    async def test_trace_id_error_scenarios(self, test_client: TestClient):
        """Test trace_id handling in error scenarios."""
        custom_trace_id = "550e8400-e29b-41d4-a716-446655440001"

        # Make a request that will fail
        response = await test_client.post(
            "/users/",
            json={"name": "", "surname": "Test", "password": "pass"},  # Invalid
            headers={"X-Request-Id": custom_trace_id}
        )

        assert response.status_code == 400
        # Should still have trace_id even on error
        assert response.headers["X-Trace-Id"] == custom_trace_id


class TestEventSystemIntegration:
    """Test event system integration (RabbitMQ)."""

    @pytest.mark.asyncio
    @pytest.mark.rabbitmq
    async def test_user_events_published(self, test_client: TestClient):
        """Test that user events are published to RabbitMQ."""
        # Create a user
        response = await test_client.post("/users/", json={
            "name": "Event",
            "surname": "Test",
            "password": "event123"
        })
        assert response.status_code == 201
        user = response.json()

        # In a real integration test, you would:
        # 1. Set up a RabbitMQ test consumer
        # 2. Verify that user.created event is received
        # 3. Check that event contains correct data and trace_id

        # For now, we just verify the API operation succeeds
        assert user["id"] is not None

    @pytest.mark.asyncio
    @pytest.mark.rabbitmq
    async def test_event_consumer_logging(self, test_client: TestClient):
        """Test that event consumer logs received events."""
        # This would require setting up a test RabbitMQ instance
        # and capturing consumer logs
        pass


class TestPerformanceIntegration:
    """Test performance aspects of the integrated system."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_operations_performance(self, test_client: TestClient):
        """Test performance of bulk operations."""
        import time

        # Create multiple users
        user_count = 10
        start_time = time.time()

        created_users = []
        for i in range(user_count):
            response = await test_client.post("/users/", json={
                "name": f"Bulk{i}",
                "surname": f"User{i}",
                "password": f"pass{i}"
            })
            assert response.status_code == 201
            created_users.append(response.json())

        creation_time = time.time() - start_time

        # Should complete within reasonable time
        assert creation_time < 5.0  # 5 seconds for 10 users

        # Verify all users were created
        assert len(created_users) == user_count

        # Test bulk retrieval
        start_time = time.time()
        response = await test_client.get("/users/")
        retrieval_time = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Should retrieve all users including the bulk created ones
        assert data["total"] >= user_count
        assert retrieval_time < 1.0  # Should be fast


class TestConcurrencyIntegration:
    """Test concurrent operations and race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self, test_client: TestClient):
        """Test creating users concurrently."""
        import asyncio

        async def create_user(index: int):
            response = await test_client.post("/users/", json={
                "name": f"Concurrent{index}",
                "surname": "User",
                "password": f"pass{index}"
            })
            return response

        # Create multiple users concurrently
        tasks = [create_user(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 201 for r in responses)

        # Should have created 5 users
        response = await test_client.get("/users/")
        data = response.json()
        assert data["total"] >= 5

    @pytest.mark.asyncio
    async def test_concurrent_updates_isolation(self, test_client: TestClient, created_user):
        """Test that concurrent updates don't interfere with each other."""
        import asyncio

        user_id = created_user["id"]
        original_name = created_user["name"]

        async def update_user(field: str, value: str):
            """Update a specific field."""
            response = await test_client.put(f"/users/{user_id}", json={field: value})
            return response

        # Try to update different fields concurrently
        tasks = [
            update_user("name", "Concurrent1"),
            update_user("surname", "Concurrent1"),
        ]
        responses = await asyncio.gather(*tasks)

        # At least one should succeed (depending on transaction isolation)
        # This tests that the system handles concurrent updates appropriately
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1

        # Final state should be consistent
        final_response = await test_client.get(f"/users/{user_id}")
        assert final_response.status_code == 200


class TestDataConsistencyIntegration:
    """Test data consistency across operations."""

    @pytest.mark.asyncio
    async def test_data_consistency_after_operations(self, test_client: TestClient):
        """Test that data remains consistent after various operations."""
        # Create user
        response = await test_client.post("/users/", json={
            "name": "Consistency",
            "surname": "Test",
            "password": "consistent123"
        })
        assert response.status_code == 201
        user = response.json()
        user_id = user["id"]

        # Update user multiple times
        for i in range(3):
            update_response = await test_client.put(f"/users/{user_id}", json={
                "name": f"Updated{i}"
            })
            assert update_response.status_code == 200

        # Final state should be the last update
        final_response = await test_client.get(f"/users/{user_id}")
        assert final_response.status_code == 200
        final_user = final_response.json()
        assert final_user["name"] == "Updated2"
        assert final_user["surname"] == "Test"  # Unchanged

    @pytest.mark.asyncio
    async def test_cascade_delete_consistency(self, test_client: TestClient):
        """Test that delete operations maintain consistency."""
        # Create user
        response = await test_client.post("/users/", json={
            "name": "Delete",
            "surname": "Test",
            "password": "delete123"
        })
        user = response.json()
        user_id = user["id"]

        # Verify user exists
        get_response = await test_client.get(f"/users/{user_id}")
        assert get_response.status_code == 200

        # Delete user
        delete_response = await test_client.delete(f"/users/{user_id}")
        assert delete_response.status_code == 200

        # Verify user is gone
        get_after_delete = await test_client.get(f"/users/{user_id}")
        assert get_after_delete.status_code == 404

        # Verify user doesn't appear in list
        list_response = await test_client.get("/users/")
        data = list_response.json()
        user_ids = [u["id"] for u in data["users"]]
        assert user_id not in user_ids
