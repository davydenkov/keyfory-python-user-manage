"""
User management API endpoints.

This module provides the REST API endpoints for complete CRUD operations on users.
All endpoints include proper error handling, input validation, and publish events
to RabbitMQ for user lifecycle tracking.

The controller uses dependency injection to provide database sessions and
automatically generates OpenAPI documentation.
"""

from typing import List, Optional
from uuid import uuid4

from litestar import Controller, get, post, put, delete, status_codes
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.params import Parameter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, UserCreate, UserUpdate, UserResponse, UserListResponse
from app.rabbitmq import publish_user_event


class UserController(Controller):
    """
    REST API controller for user management operations.

    This controller provides complete CRUD (Create, Read, Update, Delete) operations
    for users with the following features:

    - Pagination support for listing users
    - Input validation using msgspec schemas
    - Automatic database transaction management
    - RabbitMQ event publishing for all mutations
    - Comprehensive error handling with appropriate HTTP status codes
    - Automatic OpenAPI documentation generation

    Path: /users
    Dependencies: Database session injection via get_session
    """

    path = "/users"
    dependencies = {"session": Provide(get_session)}

    @get("/", summary="Get list of users", description="Retrieve a paginated list of users")
    async def get_users(
        self,
        session: AsyncSession,
        page: int = Parameter(default=1, ge=1, description="Page number (1-based)"),
        per_page: int = Parameter(default=10, ge=1, le=100, description="Items per page (max 100)"),
    ) -> UserListResponse:
        """
        Retrieve a paginated list of users.

        This endpoint supports pagination to handle large user datasets efficiently.
        Results are ordered by user ID and include total count for pagination UI.

        Args:
            session: Database session provided by dependency injection
            page: Page number (starting from 1)
            per_page: Number of users per page (1-100)

        Returns:
            UserListResponse: Paginated list of users with metadata

        Example:
            GET /users?page=1&per_page=10
        """
        # Calculate database offset for pagination
        offset = (page - 1) * per_page

        # Get total count of users for pagination metadata
        count_query = select(User).with_only_columns(User.id)
        total_result = await session.execute(count_query)
        total = len(total_result.all())

        # Fetch users for the requested page
        query = select(User).offset(offset).limit(per_page).order_by(User.id)
        result = await session.execute(query)
        users = result.scalars().all()

        # Convert database models to API response schemas
        user_responses = [
            UserResponse(
                id=user.id,
                name=user.name,
                surname=user.surname,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user in users
        ]

        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            per_page=per_page,
        )

    @get("/{user_id:int}", summary="Get user by ID", description="Retrieve a specific user by their ID")
    async def get_user(self, session: AsyncSession, user_id: int) -> UserResponse:
        """
        Retrieve a specific user by their unique identifier.

        Args:
            session: Database session provided by dependency injection
            user_id: Unique identifier of the user to retrieve

        Returns:
            UserResponse: User data if found

        Raises:
            HTTPException: 404 if user with given ID doesn't exist

        Example:
            GET /users/123
        """
        # Query user by ID
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        return UserResponse(
            id=user.id,
            name=user.name,
            surname=user.surname,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @post("/", summary="Create new user", description="Create a new user with the provided data")
    async def create_user(self, session: AsyncSession, data: UserCreate) -> UserResponse:
        """
        Create a new user with the provided information.

        This endpoint validates input data, creates a new user record,
        and publishes a creation event to RabbitMQ for downstream processing.

        Args:
            session: Database session provided by dependency injection
            data: Validated user creation data

        Returns:
            UserResponse: Created user data with generated ID and timestamps

        Note:
            In production, the password should be hashed using bcrypt/argon2
            before storage. This implementation stores passwords as plain text
            for demonstration purposes only.

        Example:
            POST /users/
            {"name": "John", "surname": "Doe", "password": "securepass"}
        """
        # Create new user instance from validated input
        user = User(
            name=data.name,
            surname=data.surname,
            password=data.password,  # WARNING: Should be hashed in production
        )

        # Persist to database
        session.add(user)
        await session.commit()
        await session.refresh(user)  # Load auto-generated fields

        # Publish event to RabbitMQ for event-driven processing
        await publish_user_event("user.created", {"user_id": user.id})

        return UserResponse(
            id=user.id,
            name=user.name,
            surname=user.surname,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @put("/{user_id:int}", summary="Update user", description="Update an existing user with the provided data")
    async def update_user(self, session: AsyncSession, user_id: int, data: UserUpdate) -> UserResponse:
        """
        Update an existing user with partial or complete data.

        This endpoint allows partial updates - only provided fields are modified.
        Publishes an update event to RabbitMQ after successful modification.

        Args:
            session: Database session provided by dependency injection
            user_id: Unique identifier of the user to update
            data: User update data (partial update supported)

        Returns:
            UserResponse: Updated user data with new timestamps

        Raises:
            HTTPException: 404 if user with given ID doesn't exist

        Example:
            PUT /users/123
            {"name": "Jane", "surname": "Smith"}
        """
        # Find existing user
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        # Apply partial updates - only modify provided fields
        if data.name is not None:
            user.name = data.name
        if data.surname is not None:
            user.surname = data.surname
        if data.password is not None:
            user.password = data.password  # WARNING: Should be hashed in production

        # Persist changes and update timestamp
        await session.commit()
        await session.refresh(user)  # Reload to get updated timestamp

        # Publish event to RabbitMQ for event-driven processing
        await publish_user_event("user.updated", {"user_id": user.id})

        return UserResponse(
            id=user.id,
            name=user.name,
            surname=user.surname,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @delete("/{user_id:int}", summary="Delete user", description="Delete a user by their ID", status_code=200)
    async def delete_user(self, session: AsyncSession, user_id: int) -> dict:
        """
        Permanently delete a user by their unique identifier.

        This operation cannot be undone. Publishes a deletion event to RabbitMQ
        for downstream processing (cleanup, audit logging, etc.).

        Args:
            session: Database session provided by dependency injection
            user_id: Unique identifier of the user to delete

        Returns:
            dict: Confirmation message with user ID

        Raises:
            HTTPException: 404 if user with given ID doesn't exist

        Example:
            DELETE /users/123
            Response: {"message": "User with id 123 has been deleted"}
        """
        # Find existing user
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        # Delete user from database
        await session.delete(user)
        await session.commit()

        # Publish event to RabbitMQ for event-driven processing
        await publish_user_event("user.deleted", {"user_id": user.id})

        return {"message": f"User with id {user_id} has been deleted"}
