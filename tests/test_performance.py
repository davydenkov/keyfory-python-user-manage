"""
Performance tests for User Management API.

Tests response times, throughput, and performance characteristics.
"""

import pytest
import time
from litestar.testing import TestClient


@pytest.mark.slow
@pytest.mark.api
class TestResponseTimePerformance:
    """Test API response time performance."""

    def test_user_creation_response_time(self, test_client: TestClient):
        """Test that user creation completes within acceptable time."""
        user_data = {
            "name": "Performance",
            "surname": "Test",
            "password": "perf123"
        }
        
        start_time = time.time()
        response = test_client.post("/users/", json=user_data)
        elapsed = time.time() - start_time
        
        assert response.status_code == 201
        assert elapsed < 1.0  # Should complete in under 1 second

    def test_user_retrieval_response_time(self, test_client: TestClient, created_user):
        """Test that user retrieval completes within acceptable time."""
        user_id = created_user["id"]
        
        start_time = time.time()
        response = test_client.get(f"/users/{user_id}")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 0.5  # Should complete in under 0.5 seconds

    def test_list_users_response_time(self, test_client: TestClient):
        """Test that listing users completes within acceptable time."""
        start_time = time.time()
        response = test_client.get("/users/")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 0.5  # Should complete in under 0.5 seconds


@pytest.mark.slow
@pytest.mark.api
class TestBulkOperationsPerformance:
    """Test bulk operations performance."""

    def test_bulk_user_creation_performance(self, test_client: TestClient):
        """Test creating multiple users performance."""
        users_data = [
            {"name": f"User{i}", "surname": "Test", "password": f"pass{i}"}
            for i in range(10)
        ]
        
        start_time = time.time()
        for user_data in users_data:
            response = test_client.post("/users/", json=user_data)
            assert response.status_code == 201
        elapsed = time.time() - start_time
        
        # Should create 10 users in reasonable time
        assert elapsed < 5.0  # Under 5 seconds for 10 users

    def test_bulk_retrieval_performance(self, test_client: TestClient, multiple_users):
        """Test retrieving multiple users performance."""
        start_time = time.time()
        response = test_client.get("/users/?per_page=100")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should complete in under 1 second
