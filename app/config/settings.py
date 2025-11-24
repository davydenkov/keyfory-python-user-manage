"""
Application configuration management using Pydantic settings.

This module provides centralized configuration for all application components
including database, message queue, logging, and server settings. Configuration
can be provided via environment variables or .env files.
"""

import os
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Application settings with environment variable binding.

    All settings can be overridden using environment variables with the same
    names. Settings can also be loaded from a .env file in the project root.
    """

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/user_management",
        env="DATABASE_URL",
        description="PostgreSQL database connection URL with asyncpg driver"
    )

    # RabbitMQ Configuration
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        env="RABBITMQ_URL",
        description="RabbitMQ AMQP connection URL for message queue"
    )

    # Application Configuration
    app_name: str = Field(
        default="keyfory-python-user-manage",
        env="APP_NAME",
        description="Application name for identification and documentation"
    )
    app_version: str = Field(
        default="0.1.0",
        env="APP_VERSION",
        description="Application version for API documentation"
    )
    debug: bool = Field(
        default=True,
        env="DEBUG",
        description="Enable debug mode for development (disables in production)"
    )
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host binding address (0.0.0.0 for all interfaces)"
    )
    port: int = Field(
        default=8000,
        env="PORT",
        description="Server port for HTTP requests",
        ge=1,
        le=65535
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    class Config:
        """
        Pydantic configuration for settings loading.

        Enables loading from .env file and makes environment variable
        names case-insensitive for better compatibility.
        """
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """
    Get application settings instance.

    Returns a singleton instance of Settings with all configuration
    loaded from environment variables and .env file.

    Returns:
        Settings: Configured application settings instance
    """
    return Settings()
