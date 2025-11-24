"""
Database configuration and session management.

This module configures the PostgreSQL database connection using Advanced SQLAlchemy
with async support. It provides session management and dependency injection
for database operations throughout the application.
"""

from advanced_alchemy import SQLAlchemyAsyncConfig, AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings

# Load application settings
settings = get_settings()

# Database configuration using Advanced SQLAlchemy
# This provides connection pooling, transaction management, and async support
db_config = SQLAlchemyAsyncConfig(
    connection_string=settings.database_url,
    # Enable SQL query logging in debug mode for development
    echo=settings.debug,
)

# Create async database engine
# The engine manages connection pooling and provides the foundation for database operations
engine: AsyncEngine = db_config.get_engine()

# Create async session factory
# Sessions are created per request and automatically handle transactions
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Keep objects loaded after commit for response serialization
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """
    Dependency injection function to provide database sessions.

    This function is used by LiteStar's dependency injection system to provide
    a database session to route handlers. Each request gets its own session
    that is automatically closed when the request completes.

    Yields:
        AsyncSession: Database session for the current request

    Note:
        This is a generator function that yields the session. LiteStar will
        automatically handle session cleanup after the request.
    """
    async with async_session() as session:
        yield session
