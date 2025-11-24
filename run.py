#!/usr/bin/env python3
"""
Application runner script.

This script provides a convenient way to start the User Management API server
using Uvicorn ASGI server. It loads configuration from environment variables
and supports development features like auto-reload.

Usage:
    python run.py

Environment Variables:
    HOST: Server bind address (default: 0.0.0.0)
    PORT: Server port (default: 8000)
    DEBUG: Enable debug mode and auto-reload (default: true)
    LOG_LEVEL: Logging level (default: INFO)

The script will start the server and make the API available at:
http://localhost:8000

Swagger UI will be available at:
http://localhost:8000/schema
"""

import uvicorn
from app.config import get_settings


def main():
    """
    Main entry point for starting the application server.

    Loads configuration settings and starts Uvicorn with appropriate parameters
    for development or production use.
    """
    # Load application configuration
    settings = get_settings()

    # Start Uvicorn ASGI server with application configuration
    uvicorn.run(
        "app.main:app",  # Application module and app instance
        host=settings.host,  # Bind address
        port=settings.port,  # Port number
        reload=settings.debug,  # Enable auto-reload in debug mode
        log_level=settings.log_level.lower(),  # Uvicorn log level
    )


if __name__ == "__main__":
    main()
