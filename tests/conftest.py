"""
Pytest configuration and fixtures for User Management API tests.

This module provides shared fixtures and configuration for all test modules,
including database setup, test clients, and test data factories.
"""

import asyncio
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock

import pytest

# Import dependencies
try:
    from litestar.testing import TestClient
    from litestar import Litestar
    from litestar.config.cors import CORSConfig
    from app.database.models import Base
    from app.api.v1.users import UserController
    from app.middleware import LoggingMiddleware
    from app.config import get_settings
    
    # Import database config components
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession
    from app.database.config import get_session
    
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    from unittest.mock import Mock
    TestClient = Mock
    Base = Mock()
    Litestar = Mock()
    DEPENDENCIES_AVAILABLE = False


# Mock RabbitMQ consumer and producer for tests
if DEPENDENCIES_AVAILABLE:
    import app.rabbitmq.consumer as consumer_module
    import app.rabbitmq.producer as producer_module
    
    # Mock RabbitMQ functions to avoid connection issues
    consumer_module.start_consumer = AsyncMock(return_value=None)
    consumer_module.stop_consumer = AsyncMock(return_value=None)
    producer_module.publish_user_event = AsyncMock(return_value=None)


# Global test engine - will be recreated per test
_test_engine: AsyncEngine | None = None
_test_async_session = None


def _create_test_engine():
    """Create a fresh database engine for tests."""
    settings = get_settings()
    
    # Create engine with test-specific settings
    engine = create_async_engine(
        settings.database_url,
        echo=False,  # Disable SQL logging in tests
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
    )
    return engine


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Set up test database tables once per session.
    
    Creates all tables before tests run.
    """
    if not DEPENDENCIES_AVAILABLE:
        pytest.skip("Database dependencies not available")
    
    # Create event loop for database setup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Create temporary engine for setup
        temp_engine = _create_test_engine()
        
        async def _setup():
            try:
                async with temp_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            except Exception:
                # Tables might already exist, that's okay
                pass
        
        loop.run_until_complete(_setup())
        yield
        
        # Cleanup
        async def _teardown():
            try:
                async with temp_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            except Exception:
                pass
            await temp_engine.dispose()
        
        loop.run_until_complete(_teardown())
    finally:
        loop.close()


@pytest.fixture(scope="function", autouse=True)
def reset_database_engine():
    """
    Reset database engine for each test to avoid event loop issues.
    
    This ensures each test gets a fresh engine with the correct event loop.
    """
    if not DEPENDENCIES_AVAILABLE:
        return
    
    global _test_engine, _test_async_session
    
    # Dispose old engine if it exists
    if _test_engine:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_test_engine.dispose())
        except Exception:
            pass
        finally:
            loop.close()
    
    # Create new engine - will use TestClient's event loop
    _test_engine = None
    _test_async_session = None
    
    yield
    
    # Cleanup after test
    if _test_engine:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_test_engine.dispose())
            loop.close()
        except Exception:
            pass


@pytest.fixture(scope="session")
def test_app():
    """Create a test app instance without lifespan handler."""
    if not DEPENDENCIES_AVAILABLE:
        pytest.skip("Dependencies not available")
    
    settings = get_settings()
    cors_config = CORSConfig(allow_origins=["*"])
    
    # Create app without lifespan to avoid RabbitMQ connection issues
    test_app_instance = Litestar(
        route_handlers=[UserController],
        middleware=[LoggingMiddleware],
        cors_config=cors_config,
        debug=settings.debug,
    )
    
    return test_app_instance


@pytest.fixture
def test_client(test_app):
    """
    Provide a test client for API testing.
    
    Returns:
        TestClient: Configured test client for the application
    """
    if not DEPENDENCIES_AVAILABLE:
        pytest.skip("TestClient not available")
    
    # Patch the database engine to use a fresh one for this test
    # This ensures it uses the same event loop as TestClient
    import app.database.config as db_config
    
    # Create engine with current event loop
    test_engine = _create_test_engine()
    test_async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Temporarily replace the engine and session
    original_engine = db_config.engine
    original_async_session = db_config.async_session
    original_get_session = db_config.get_session
    
    db_config.engine = test_engine
    db_config.async_session = test_async_session
    
    # Create new get_session function
    async def test_get_session():
        async with test_async_session() as session:
            yield session
    
    db_config.get_session = test_get_session
    
    try:
        with TestClient(app=test_app) as client:
            yield client
    finally:
        # Restore original
        db_config.engine = original_engine
        db_config.async_session = original_async_session
        db_config.get_session = original_get_session
        
        # Dispose test engine
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(test_engine.dispose())
        except Exception:
            pass


@pytest.fixture(autouse=True)
def cleanup_database(test_client):
    """Clean up database between tests."""
    yield
    # After each test, truncate tables
    if DEPENDENCIES_AVAILABLE:
        try:
            import app.database.config as db_config
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                async def _cleanup():
                    try:
                        async with db_config.engine.begin() as conn:
                            await conn.run_sync(lambda sync_conn: sync_conn.execute(
                                "TRUNCATE TABLE \"user\" RESTART IDENTITY CASCADE"
                            ))
                    except Exception:
                        pass
                
                loop.run_until_complete(_cleanup())
        except Exception:
            pass


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Provide sample user data for testing."""
    return {
        "name": "Test",
        "surname": "User",
        "password": "testpassword123"
    }


@pytest.fixture
def created_user(test_client: TestClient, test_user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create and return a test user."""
    response = test_client.post("/users/", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def multiple_users(test_client: TestClient) -> list:
    """Create multiple test users for pagination testing."""
    users_data = [
        {"name": "Alice", "surname": "Johnson", "password": "pass1"},
        {"name": "Bob", "surname": "Smith", "password": "pass2"},
        {"name": "Charlie", "surname": "Brown", "password": "pass3"},
        {"name": "Diana", "surname": "Wilson", "password": "pass4"},
        {"name": "Eve", "surname": "Davis", "password": "pass5"},
    ]
    
    created_users = []
    for user_data in users_data:
        response = test_client.post("/users/", json=user_data)
        assert response.status_code == 201
        created_users.append(response.json())
    
    return created_users


@pytest.fixture
def trace_id_header() -> str:
    """Provide a test trace ID."""
    return str(uuid.uuid4())


# Custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "api: mark test as an API endpoint test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "rabbitmq: mark test as requiring RabbitMQ")
    config.addinivalue_line("markers", "database: mark test as requiring database")
    config.addinivalue_line("markers", "mock: mark test as using mocks")
