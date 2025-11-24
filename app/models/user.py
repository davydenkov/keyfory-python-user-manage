"""
User database model definition.

This module defines the User SQLAlchemy model that represents a user entity
in the PostgreSQL database. The model includes all required fields as specified
in the project requirements.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, func

from app.database.models import Base


class User(Base):
    """
    User database model representing a user in the system.

    This model maps to the 'user' table in PostgreSQL and provides the
    data structure for user management operations. It includes automatic
    timestamp management for creation and update tracking.

    Database Schema:
        id: BIGINT PRIMARY KEY (auto-increment)
        name: TEXT NOT NULL
        surname: TEXT NOT NULL
        password: TEXT NOT NULL (should be hashed in production)
        created_at: TIMESTAMP WITH TIME ZONE (UTC)
        updated_at: TIMESTAMP WITH TIME ZONE (UTC)
    """

    __tablename__ = "user"

    # Primary key with auto-increment
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        index=True,
        doc="Unique identifier for the user (auto-generated)"
    )

    # User personal information
    name = Column(
        Text,
        nullable=False,
        doc="User's first name"
    )
    surname = Column(
        Text,
        nullable=False,
        doc="User's last name/family name"
    )
    password = Column(
        Text,
        nullable=False,
        doc="User's password (should be hashed using bcrypt/argon2 in production)"
    )

    # Automatic timestamp fields
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the user was created (UTC)"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the user was last updated (UTC)"
    )

    def __repr__(self) -> str:
        """
        String representation of the User instance.

        Provides a readable representation useful for debugging and logging.
        Only includes non-sensitive information (id, name, surname).

        Returns:
            str: String representation of the user
        """
        return f"<User(id={self.id}, name={self.name}, surname={self.surname})>"
