"""
Main application entry point for the User Management REST API.

This module configures and initializes the LiteStar application with all
necessary components including database, middleware, API routes, and
RabbitMQ integration.
"""

from contextlib import asynccontextmanager

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.config.openapi import OpenAPIConfig
from litestar.openapi import Server

from app.api.v1.users import UserController
from app.config import get_settings
from app.database.config import engine
from app.database.models import Base
from app.middleware import LoggingMiddleware
from app.rabbitmq.consumer import start_consumer, stop_consumer

# Global application settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: Litestar):
    """
    Application lifespan context manager for startup and shutdown procedures.

    This context manager handles:
    - Database table creation on startup
    - RabbitMQ consumer initialization
    - Graceful shutdown of services

    Args:
        app: The Litestar application instance

    Yields:
        None
    """
    # Startup phase
    print(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database: Create all tables defined in SQLAlchemy models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize message queue consumer for user events
    await start_consumer()

    # Application runs here
    yield

    # Shutdown phase
    print(f"Shutting down {settings.app_name}")

    # Gracefully stop the RabbitMQ consumer
    await stop_consumer()


# CORS configuration to allow cross-origin requests from any origin
# In production, this should be restricted to specific domains
cors_config = CORSConfig(allow_origins=["*"])

# OpenAPI/Swagger configuration for API documentation
openapi_config = OpenAPIConfig(
    title=settings.app_name,
    version=settings.app_version,
    description="REST API for user management with CRUD operations, structured logging, and event-driven architecture",
    servers=[
        Server(
            url="http://localhost:8000",
            description="Development server"
        )
    ],
    contact={"name": "API Support", "email": "support@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# Create the main LiteStar application instance
app = Litestar(
    # Register API route handlers
    route_handlers=[UserController],
    # Apply logging middleware for request tracing
    middleware=[LoggingMiddleware],
    # Configure startup/shutdown lifecycle
    lifespan=[lifespan],
    # Enable CORS for web clients
    cors_config=cors_config,
    # Configure OpenAPI documentation
    openapi_config=openapi_config,
    # Enable debug mode based on configuration
    debug=settings.debug,
)
