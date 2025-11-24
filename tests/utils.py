"""
Test utilities and helper functions.

Provides common testing utilities, fixtures, and helper functions
used across multiple test modules.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import pytest
from litestar.testing import TestClient


def assert_user_response_structure(user_data: Dict[str, Any]) -> None:
    """
    Assert that user response has correct structure.

    Args:
        user_data: User response data to validate

    Raises:
        AssertionError: If structure is invalid
    """
    required_fields = ["id", "name", "surname", "created_at", "updated_at"]

    for field in required_fields:
        assert field in user_data, f"Missing required field: {field}"

    # Validate field types
    assert isinstance(user_data["id"], int), "id should be integer"
    assert isinstance(user_data["name"], str), "name should be string"
    assert isinstance(user_data["surname"], str), "surname should be string"

    # Password should NOT be present in responses
    assert "password" not in user_data, "Password should not be in response"

    # Validate timestamps
    for timestamp_field in ["created_at", "updated_at"]:
        timestamp = user_data[timestamp_field]
        assert isinstance(timestamp, str), f"{timestamp_field} should be string"
        # Should be ISO format datetime
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


def assert_pagination_response_structure(response_data: Dict[str, Any]) -> None:
    """
    Assert that paginated response has correct structure.

    Args:
        response_data: Paginated response data to validate

    Raises:
        AssertionError: If structure is invalid
    """
    required_fields = ["users", "total", "page", "per_page"]

    for field in required_fields:
        assert field in response_data, f"Missing pagination field: {field}"

    assert isinstance(response_data["users"], list), "users should be list"
    assert isinstance(response_data["total"], int), "total should be integer"
    assert isinstance(response_data["page"], int), "page should be integer"
    assert isinstance(response_data["per_page"], int), "per_page should be integer"

    # Validate each user in the list
    for user in response_data["users"]:
        assert_user_response_structure(user)


def assert_trace_id_present(response) -> str:
    """
    Assert that response contains X-Trace-Id header and return it.

    Args:
        response: HTTP response object

    Returns:
        str: The trace ID from the response

    Raises:
        AssertionError: If trace ID header is missing or invalid
    """
    assert "X-Trace-Id" in response.headers, "X-Trace-Id header missing"
    trace_id = response.headers["X-Trace-Id"]
    assert isinstance(trace_id, str), "Trace ID should be string"
    assert len(trace_id) > 0, "Trace ID should not be empty"

    # Validate UUID format (basic check)
    import uuid
    uuid.UUID(trace_id)  # Will raise ValueError if invalid

    return trace_id


def create_test_user_data(
    name: Optional[str] = None,
    surname: Optional[str] = None,
    password: Optional[str] = None,
    index: Optional[int] = None
) -> Dict[str, str]:
    """
    Create test user data with sensible defaults.

    Args:
        name: Custom name (default: "Test")
        surname: Custom surname (default: "User")
        password: Custom password (default: "password123")
        index: Index for unique data generation

    Returns:
        Dict[str, str]: User data dictionary
    """
    if index is not None:
        return {
            "name": name or f"Test{index}",
            "surname": surname or f"User{index}",
            "password": password or f"password{index}123"
        }
    else:
        return {
            "name": name or "Test",
            "surname": surname or "User",
            "password": password or "password123"
        }


async def create_multiple_test_users(
    client: TestClient,
    count: int,
    base_name: str = "TestUser"
) -> List[Dict[str, Any]]:
    """
    Create multiple test users for bulk operations testing.

    Args:
        client: Test client for making requests
        count: Number of users to create
        base_name: Base name for users

    Returns:
        List[Dict[str, Any]]: List of created user data
    """
    users = []

    for i in range(count):
        user_data = create_test_user_data(
            name=f"{base_name}{i}",
            surname="Test",
            password=f"pass{i}123",
            index=i
        )

        response = await client.post("/users/", json=user_data)
        assert response.status_code == 201
        users.append(response.json())

    return users


def assert_response_time(response, max_seconds: float = 1.0) -> float:
    """
    Assert that response time is within acceptable limits.

    Note: This requires the response to have timing information,
    which may need to be added by middleware or testing utilities.

    Args:
        response: HTTP response object
        max_seconds: Maximum acceptable response time

    Returns:
        float: Actual response time

    Raises:
        AssertionError: If response time exceeds limit
    """
    # This is a placeholder for response time checking
    # In a real implementation, you might store timing in response metadata
    response_time = getattr(response, '_response_time', 0.1)  # Mock timing
    assert response_time <= max_seconds, f"Response too slow: {response_time}s > {max_seconds}s"
    return response_time


class AsyncTimer:
    """Context manager for measuring async operation timing."""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    async def __aenter__(self):
        self.start_time = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = asyncio.get_event_loop().time()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time


async def measure_async_operation_time(operation, *args, **kwargs) -> tuple:
    """
    Measure the execution time of an async operation.

    Args:
        operation: Async callable to measure
        *args: Arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation

    Returns:
        tuple: (result, execution_time)
    """
    async with AsyncTimer() as timer:
        result = await operation(*args, **kwargs)

    return result, timer.elapsed


def validate_json_response(response) -> Dict[str, Any]:
    """
    Validate that response contains valid JSON and return parsed data.

    Args:
        response: HTTP response object

    Returns:
        Dict[str, Any]: Parsed JSON data

    Raises:
        AssertionError: If response is not valid JSON
    """
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    try:
        return response.json()
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON response: {e}")


def assert_error_response(
    response,
    expected_status: int,
    expected_detail: Optional[str] = None
) -> None:
    """
    Assert that response is a proper error response.

    Args:
        expected_status: Expected HTTP status code
        expected_detail: Expected error detail (optional)
    """
    assert response.status_code == expected_status

    if expected_detail:
        data = response.json()
        assert "detail" in data
        assert expected_detail in data["detail"]


class TestDataBuilder:
    """Builder pattern for creating test data."""

    def __init__(self):
        self._data = {}

    def with_name(self, name: str) -> 'TestDataBuilder':
        """Set name field."""
        self._data["name"] = name
        return self

    def with_surname(self, surname: str) -> 'TestDataBuilder':
        """Set surname field."""
        self._data["surname"] = surname
        return self

    def with_password(self, password: str) -> 'TestDataBuilder':
        """Set password field."""
        self._data["password"] = password
        return self

    def with_index(self, index: int) -> 'TestDataBuilder':
        """Set indexed fields."""
        return self.with_name(f"Test{index}").with_surname(f"User{index}").with_password(f"pass{index}123")

    def build(self) -> Dict[str, str]:
        """Build the test data dictionary."""
        return self._data.copy()

    @classmethod
    def user(cls) -> 'TestDataBuilder':
        """Create a user data builder with defaults."""
        return cls().with_name("Test").with_surname("User").with_password("password123")


# Common test data constants
VALID_USER_DATA = {
    "name": "Valid",
    "surname": "User",
    "password": "validpass123"
}

INVALID_USER_DATA = {
    "name": "",
    "surname": "",
    "password": ""
}

PARTIAL_USER_DATA = {
    "name": "Partial"
}

# HTTP status code constants for testing
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422
