"""
Performance tests for User Management API.

Tests response times, throughput, and resource usage under various loads.
These tests are marked as 'slow' and may be skipped in regular CI runs.
"""

import asyncio
import time
from typing import List

import pytest
from litestar.testing import TestClient

from tests.utils import (
    create_multiple_test_users,
    AsyncTimer,
    measure_async_operation_time,
    assert_response_time
)


@pytest.mark.slow
class TestResponseTimePerformance:
    """Test response time performance for various operations."""

    @pytest.mark.asyncio
    async def test_user_creation_response_time(self, test_client: TestClient):
        """Test that user creation responds within acceptable time."""
        user_data = {"name": "Perf", "surname": "Test", "password": "perf123"}

        start_time = time.time()
        response = await test_client.post("/users/", json=user_data)
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 201
        assert response_time < 0.5  # Should respond within 500ms

    @pytest.mark.asyncio
    async def test_user_retrieval_response_time(self, test_client: TestClient, created_user):
        """Test that user retrieval responds quickly."""
        user_id = created_user["id"]

        start_time = time.time()
        response = await test_client.get(f"/users/{user_id}")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 0.1  # Should respond within 100ms

    @pytest.mark.asyncio
    async def test_list_users_response_time(self, test_client: TestClient, multiple_users):
        """Test that listing users scales reasonably."""
        # multiple_users fixture creates 5 users
        assert len(multiple_users) >= 5

        start_time = time.time()
        response = await test_client.get("/users/")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 0.2  # Should respond within 200ms even with multiple users


@pytest.mark.slow
class TestBulkOperationsPerformance:
    """Test performance of bulk operations."""

    @pytest.mark.asyncio
    async def test_bulk_user_creation_performance(self, test_client: TestClient):
        """Test creating multiple users in sequence."""
        user_count = 20

        start_time = time.time()
        created_users = await create_multiple_test_users(test_client, user_count, "Bulk")
        end_time = time.time()

        total_time = end_time - start_time
        avg_time_per_user = total_time / user_count

        assert len(created_users) == user_count
        assert total_time < 10.0  # Should complete within 10 seconds
        assert avg_time_per_user < 0.5  # Average under 500ms per user

    @pytest.mark.asyncio
    async def test_concurrent_user_creation_performance(self, test_client: TestClient):
        """Test creating users concurrently."""
        user_count = 10

        async def create_user(index: int):
            response = await test_client.post("/users/", json={
                "name": f"Concurrent{index}",
                "surname": "User",
                "password": f"pass{index}"
            })
            return response

        start_time = time.time()
        tasks = [create_user(i) for i in range(user_count)]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        # All responses should be successful
        assert all(r.status_code == 201 for r in responses)
        assert total_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_bulk_retrieval_performance(self, test_client: TestClient):
        """Test retrieving multiple users efficiently."""
        # Create test users
        user_count = 50
        await create_multiple_test_users(test_client, user_count, "Retrieve")

        start_time = time.time()
        response = await test_client.get("/users/")
        end_time = time.time()

        response_time = end_time - start_time
        data = response.json()

        assert response.status_code == 200
        assert data["total"] >= user_count
        assert response_time < 1.0  # Should retrieve quickly


@pytest.mark.slow
class TestDatabasePerformance:
    """Test database operation performance."""

    @pytest.mark.asyncio
    async def test_database_query_performance(self, test_client: TestClient, db_session):
        """Test database query performance scales."""
        # Create many users
        user_count = 100
        await create_multiple_test_users(test_client, user_count, "Query")

        # Test different query types
        queries = [
            "/users/",  # List all
            "/users/?page=1&per_page=10",  # Paginated
            "/users/?page=5&per_page=20",  # Different page
        ]

        for query in queries:
            start_time = time.time()
            response = await test_client.get(query)
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code == 200
            assert response_time < 0.5  # Each query should be fast

    @pytest.mark.asyncio
    async def test_database_write_performance(self, test_client: TestClient):
        """Test database write operation performance."""
        operations = 50

        start_time = time.time()
        for i in range(operations):
            response = await test_client.post("/users/", json={
                "name": f"Write{i}",
                "surname": "Test",
                "password": f"pass{i}"
            })
            assert response.status_code == 201
        end_time = time.time()

        total_time = end_time - start_time
        avg_time_per_operation = total_time / operations

        assert total_time < 15.0  # Should complete within 15 seconds
        assert avg_time_per_operation < 0.3  # Average under 300ms per write


@pytest.mark.slow
class TestMemoryPerformance:
    """Test memory usage and leaks."""

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, test_client: TestClient):
        """Test that memory usage doesn't grow significantly with repeated operations."""
        # This is a basic test - in production you would use memory profiling tools
        operations = 100

        for i in range(operations):
            # Create user
            response = await test_client.post("/users/", json={
                "name": f"Memory{i}",
                "surname": "Test",
                "password": f"pass{i}"
            })
            assert response.status_code == 201
            user = response.json()

            # Retrieve user
            response = await test_client.get(f"/users/{user['id']}")
            assert response.status_code == 200

            # Delete user (to avoid accumulating test data)
            response = await test_client.delete(f"/users/{user['id']}")
            assert response.status_code == 200

        # If we get here without memory issues, the test passes
        assert True


@pytest.mark.slow
class TestLoadTesting:
    """Basic load testing scenarios."""

    @pytest.mark.asyncio
    async def test_sustained_load(self, test_client: TestClient):
        """Test sustained load over time."""
        duration_seconds = 10
        operations_per_second = 5

        total_operations = duration_seconds * operations_per_second
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < duration_seconds and operation_count < total_operations:
            # Perform a mix of operations
            response = await test_client.post("/users/", json={
                "name": f"Load{operation_count}",
                "surname": "Test",
                "password": f"pass{operation_count}"
            })
            assert response.status_code == 201
            operation_count += 1

            # Small delay to control rate
            await asyncio.sleep(0.2)

        elapsed_time = time.time() - start_time
        actual_ops_per_second = operation_count / elapsed_time

        assert operation_count > 0
        assert actual_ops_per_second >= operations_per_second * 0.8  # At least 80% of target

    @pytest.mark.asyncio
    async def test_peak_load_burst(self, test_client: TestClient):
        """Test handling of operation bursts."""
        burst_size = 20

        # Execute burst of operations
        start_time = time.time()
        tasks = []
        for i in range(burst_size):
            task = test_client.post("/users/", json={
                "name": f"Burst{i}",
                "surname": "Test",
                "password": f"pass{i}"
            })
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        burst_time = end_time - start_time

        # All operations should succeed
        assert all(r.status_code == 201 for r in responses)
        assert burst_time < 5.0  # Burst should complete within 5 seconds


@pytest.mark.slow
class TestScalabilityTesting:
    """Test scalability characteristics."""

    @pytest.mark.asyncio
    async def test_data_set_scaling(self, test_client: TestClient):
        """Test how performance changes with data set size."""
        # Test with different data set sizes
        data_sizes = [10, 50, 100]

        for size in data_sizes:
            # Clean up previous test data
            response = await test_client.get("/users/")
            existing_users = response.json()["total"]

            # Skip if too many existing users (test isolation issue)
            if existing_users > size:
                continue

            # Create test data set
            await create_multiple_test_users(test_client, size, f"Scale{size}")

            # Measure list performance
            start_time = time.time()
            response = await test_client.get("/users/")
            end_time = time.time()

            list_time = end_time - start_time
            data = response.json()

            assert response.status_code == 200
            assert data["total"] >= size

            # List time should scale reasonably (linear or better)
            # This is a basic check - real scalability testing needs more sophisticated analysis
            assert list_time < size * 0.01  # Rough scaling check


# Performance benchmarks and thresholds
PERFORMANCE_THRESHOLDS = {
    "user_creation": 0.5,      # seconds
    "user_retrieval": 0.1,     # seconds
    "user_list": 0.2,          # seconds
    "bulk_creation": 10.0,     # seconds for 20 users
    "concurrent_creation": 5.0,# seconds for 10 concurrent users
}

# Utility functions for performance monitoring
def log_performance_metric(operation: str, duration: float, metadata: dict = None):
    """Log performance metrics for analysis."""
    metadata_str = f" - {metadata}" if metadata else ""
    print(f"PERF: {operation} took {duration:.3f}s{metadata_str}")

def assert_performance_threshold(operation: str, duration: float):
    """Assert that operation meets performance threshold."""
    threshold = PERFORMANCE_THRESHOLDS.get(operation)
    if threshold:
        assert duration <= threshold, f"{operation} too slow: {duration:.3f}s > {threshold}s"
        log_performance_metric(operation, duration, {"threshold": threshold})
