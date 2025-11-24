"""
Main application entry point for the User Management REST API.

This module configures and initializes the LiteStar application with all
necessary components including database, middleware, API routes, and
RabbitMQ integration.

Requires Python 3.12+ for optimal performance and modern async features.
"""

import sys
from contextlib import asynccontextmanager

# Ensure we're running on Python 3.12+
if sys.version_info < (3, 12):
    raise RuntimeError(
        f"Python 3.12+ is required. Current version: {sys.version_info.major}.{sys.version_info.minor}"
    )

# Import LiteStar with fallback handling
try:
    from litestar import Litestar
    from litestar.config.cors import CORSConfig
    # Try different import paths for OpenAPIConfig
    try:
        from litestar.config.openapi import OpenAPIConfig
    except ImportError:
        try:
            from litestar.openapi import OpenAPIConfig
        except ImportError:
            # Fallback: try to create a basic config or disable OpenAPI
            OpenAPIConfig = None

    try:
        from litestar.openapi.spec import Server
    except ImportError:
        try:
            from litestar.openapi.spec.server import Server
        except ImportError:
            # Fallback: disable Server usage if import fails
            Server = None

except ImportError as e:
    raise ImportError(
        f"LiteStar is required but not installed. "
        f"Please install it with: pip install litestar[standard]\n"
        f"Or run the setup script: ./setup.sh\n"
        f"Original error: {e}"
    )

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

    Uses Python 3.12+ async features for optimal performance.

    Args:
        app: The Litestar application instance

    Yields:
        None
    """
    # Startup phase with enhanced logging (Python 3.12+ f-string improvements)
    startup_msg = (
        f"🚀 Starting {settings.app_name} v{settings.app_version} "
        f"(Python {sys.version_info.major}.{sys.version_info.minor})"
    )
    print(startup_msg)

    # Initialize database: Create all tables defined in SQLAlchemy models
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(bind=sync_conn))

    # Initialize message queue consumer for user events
    await start_consumer()

    # Application runs here
    yield

    # Shutdown phase with enhanced logging
    shutdown_msg = f"🛑 Shutting down {settings.app_name}"
    print(shutdown_msg)

    # Gracefully stop the RabbitMQ consumer
    await stop_consumer()


# CORS configuration to allow cross-origin requests from any origin
# In production, this should be restricted to specific domains
cors_config = CORSConfig(allow_origins=["*"])

# OpenAPI/Swagger configuration for API documentation
if OpenAPIConfig is not None:
    try:
        # Build servers list only if Server class is available
        servers_list = None
        if Server is not None:
            servers_list = [
                Server(
                    url="http://localhost:8000",
                    description="Development server"
                )
            ]
        
        openapi_config = OpenAPIConfig(
            title=settings.app_name,
            version=settings.app_version,
            description="REST API for user management with CRUD operations, structured logging, and event-driven architecture",
            servers=servers_list,
            contact={"name": "API Support", "email": "support@example.com"},
            license={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
            path="/schema",  # Explicitly set the OpenAPI schema path
            root_schema_site="swagger",  # Set default UI to Swagger
        )
    except TypeError as e:
        # Fallback if OpenAPIConfig parameters have changed
        print(f"Warning: OpenAPI configuration failed ({e}), using basic config")
        try:
            openapi_config = OpenAPIConfig(
                title=settings.app_name,
                version=settings.app_version,
                description="REST API for user management with CRUD operations, structured logging, and event-driven architecture",
            )
        except Exception:
            # Last resort: disable OpenAPI
            openapi_config = None
else:
    # Fallback when OpenAPIConfig is not available
    openapi_config = None

# Create the main LiteStar application instance
app_kwargs = {
    # Register API route handlers
    "route_handlers": [UserController],
    # Apply logging middleware for request tracing
    "middleware": [LoggingMiddleware],
    # Configure startup/shutdown lifecycle
    "lifespan": [lifespan],
    # Enable CORS for web clients
    "cors_config": cors_config,
    # Enable debug mode based on configuration
    "debug": settings.debug,
}

# Conditionally add OpenAPI config if available
if openapi_config is not None:
    app_kwargs["openapi_config"] = openapi_config

app = Litestar(**app_kwargs)
