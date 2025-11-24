"""
API request and response schemas using msgspec.

This module defines all the data structures used for API communication.
msgspec provides fast serialization/deserialization and automatic OpenAPI
schema generation. These schemas validate input data and structure output data.

All schemas inherit from msgspec.Struct for optimal performance and type safety.
"""

from datetime import datetime
from typing import Optional

from msgspec import Struct


class UserCreate(Struct):
    """
    Schema for creating a new user.

    This schema validates the data sent in POST requests to create users.
    All fields are required for user creation.
    """
    name: str
    surname: str
    password: str


class UserUpdate(Struct):
    """
    Schema for updating an existing user.

    This schema validates the data sent in PUT requests to update users.
    All fields are optional since updates can be partial.
    """
    name: Optional[str] = None
    surname: Optional[str] = None
    password: Optional[str] = None


class UserResponse(Struct):
    """
    Schema for individual user response data.

    This schema structures the data returned for single user queries.
    It includes all user fields except the password for security.
    """
    id: int
    name: str
    surname: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(Struct):
    """
    Schema for paginated user list response.

    This schema structures the data returned for user listing endpoints
    with pagination metadata.
    """
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
