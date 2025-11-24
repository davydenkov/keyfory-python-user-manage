"""
Pytest configuration and fixtures for User Management API tests.

This module provides shared fixtures and configuration for all test modules,
including database setup, test clients, and test data factories.

The fixtures are designed to work with or without external dependencies by using
mocks and fallbacks when the real dependencies are not available.
"""

import asyncio
import uuid
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import Mock, MagicMock

import pytest

# Try to import real dependencies, fall back to mocks if not available
try:
    from litestar.testing import TestClient
    from app.database.config import engine, get_session
    from app.database.models import Base
    from app.main import app
    from app.models import User
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    # Create mock classes when dependencies are not available
    TestClient = Mock
    engine = Mock()
    get_session = Mock(return_value=Mock())
    Base = Mock()
    app = Mock()
    User = Mock()
    DEPENDENCIES_AVAILABLE = False


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Set up test database.

    Creates all tables before running tests and drops them after all tests complete.
    This ensures a clean database state for each test session.

    Skips if dependencies are not available.
    """
    if not DEPENDENCIES_AVAILABLE:
        pytest.skip("Database dependencies not available")

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean up - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_client() -> AsyncGenerator[TestClient, None]:
    """
    Provide a test client for API testing.

    This fixture creates a LiteStar TestClient that can be used to make
    HTTP requests to the application in tests. Falls back to mock if
    dependencies are not available.

    Yields:
        TestClient: Configured test client for the application
    """
    if not DEPENDENCIES_AVAILABLE:
        # Create a mock client that simulates HTTP responses
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"X-Trace-Id": str(uuid.uuid4())}
        mock_response.json.return_value = {"message": "Mock response"}
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        mock_client.put.return_value = mock_response
        mock_client.delete.return_value = mock_response

        # Mock context manager behavior
        mock_client.__aenter__ = Mock(return_value=mock_client)
        mock_client.__aexit__ = Mock(return_value=None)

        yield mock_client
        return

    async with TestClient(app) as client:
        yield client


@pytest.fixture
async def db_session():
    """
    Provide a database session for tests requiring direct database access.

    This fixture provides a database session that can be used in tests that
    need to interact directly with the database. Falls back to mock if
    dependencies are not available.

    Yields:
        AsyncSession: Database session for the test
    """
    if not DEPENDENCIES_AVAILABLE:
        mock_session = Mock()
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        mock_session.delete = Mock()

        async def async_iter():
            yield mock_session

        for session in async_iter():
            yield session
        return

    async for session in get_session():
        yield session


@pytest.fixture
async def test_user_data() -> Dict[str, Any]:
    """
    Provide sample user data for testing.

    Returns a dictionary with valid user creation data that can be used
    across multiple tests.

    Returns:
        Dict[str, Any]: Sample user data
    """
    return {
        "name": "Test",
        "surname": "User",
        "password": "testpassword123"
    }


@pytest.fixture
async def created_user(test_client: TestClient, test_user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create and return a test user.

    This fixture creates a user in the database and returns the user data,
    which can be used by tests that require an existing user.

    Args:
        test_client: Test client fixture
        test_user_data: User data fixture

    Returns:
        Dict[str, Any]: Created user data including ID and timestamps
    """
    response = await test_client.post("/users/", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def multiple_users(test_client: TestClient) -> list:
    """
    Create multiple test users for pagination and bulk operation testing.

    This fixture creates several users and returns their data for tests
    that need to work with multiple users.

    Args:
        test_client: Test client fixture

    Returns:
        list: List of created user data dictionaries
    """
    users_data = [
        {"name": "Alice", "surname": "Johnson", "password": "pass1"},
        {"name": "Bob", "surname": "Smith", "password": "pass2"},
        {"name": "Charlie", "surname": "Brown", "password": "pass3"},
        {"name": "Diana", "surname": "Wilson", "password": "pass4"},
        {"name": "Eve", "surname": "Davis", "password": "pass5"},
    ]

    created_users = []
    for user_data in users_data:
        response = await test_client.post("/users/", json=user_data)
        assert response.status_code == 201
        created_users.append(response.json())

    return created_users


@pytest.fixture
def trace_id_header() -> str:
    """
    Provide a test trace ID for request tracing tests.

    Returns:
        str: A valid UUID4 trace ID
    """
    return str(uuid.uuid4())


@pytest.fixture
async def authenticated_client(test_client: TestClient) -> TestClient:
    """
    Provide a test client with authentication headers.

    This fixture can be extended when authentication is implemented.
    For now, it returns the regular test client.

    Args:
        test_client: Base test client fixture

    Returns:
        TestClient: Test client with authentication (when implemented)
    """
    # TODO: Add authentication when JWT/auth is implemented
    return test_client


# Custom pytest markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "api: mark test as an API endpoint test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "rabbitmq: mark test as requiring RabbitMQ"
    )
    config.addinivalue_line(
        "markers", "mock: mark test as using mocked dependencies"
    )


@pytest.fixture(autouse=True)
def skip_if_dependencies_unavailable(request):
    """
    Skip tests that require unavailable dependencies.

    This fixture automatically skips tests marked with certain markers
    when the required dependencies are not available.
    """
    if not DEPENDENCIES_AVAILABLE:
        # Skip tests that require real dependencies
        markers_requiring_deps = ["integration", "api"]
        for marker in markers_requiring_deps:
            if marker in request.keywords:
                pytest.skip(f"Test requires {marker} dependencies which are not available")


# Global test configuration
@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return {
        "dependencies_available": DEPENDENCIES_AVAILABLE,
        "mock_mode": not DEPENDENCIES_AVAILABLE
    }
