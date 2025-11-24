"""
Unit tests for database models and data structures.

Tests model creation, validation, relationships, and database operations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.models.schemas import UserCreate, UserUpdate, UserResponse


class TestUserModel:
    """Test User database model functionality."""

    @pytest.mark.asyncio
    async def test_user_model_creation(self, db_session: AsyncSession):
        """Test creating a User model instance."""
        user = User(
            name="Test",
            surname="User",
            password="password123"
        )

        # Verify attributes are set
        assert user.name == "Test"
        assert user.surname == "User"
        assert user.password == "password123"

        # Verify ID is not set yet (auto-generated)
        assert user.id is None

        # Verify timestamps are None before database save
        assert user.created_at is None
        assert user.updated_at is None

    @pytest.mark.asyncio
    async def test_user_model_string_representation(self, db_session: AsyncSession):
        """Test User model string representation."""
        user = User(
            name="John",
            surname="Doe",
            password="password123"
        )

        # Test __repr__ method
        repr_str = repr(user)
        assert "User" in repr_str
        assert "id=None" in repr_str
        assert "name=John" in repr_str
        assert "surname=Doe" in repr_str

        # Password should not be in repr for security
        assert "password" not in repr_str

    @pytest.mark.asyncio
    async def test_user_database_persistence(self, db_session: AsyncSession):
        """Test saving and retrieving User from database."""
        # Create user
        user = User(
            name="Database",
            surname="Test",
            password="dbpassword123"
        )

        # Save to database
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Verify auto-generated fields
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at == user.updated_at  # Should be equal on creation

        # Retrieve from database
        query = select(User).where(User.id == user.id)
        result = await db_session.execute(query)
        retrieved_user = result.scalar_one()

        # Verify retrieved data matches
        assert retrieved_user.id == user.id
        assert retrieved_user.name == "Database"
        assert retrieved_user.surname == "Test"
        assert retrieved_user.password == "dbpassword123"
        assert retrieved_user.created_at == user.created_at
        assert retrieved_user.updated_at == user.updated_at

    @pytest.mark.asyncio
    async def test_user_update_timestamp(self, db_session: AsyncSession):
        """Test that updated_at timestamp changes on update."""
        import asyncio

        # Create user
        user = User(
            name="Timestamp",
            surname="Test",
            password="timestamp123"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        original_updated_at = user.updated_at

        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.01)

        # Update user
        user.name = "Updated"
        await db_session.commit()
        await db_session.refresh(user)

        # Verify updated_at changed
        assert user.updated_at > original_updated_at
        assert user.name == "Updated"


class TestUserSchemas:
    """Test User data schemas and validation."""

    def test_user_create_schema(self):
        """Test UserCreate schema validation."""
        # Valid data
        schema = UserCreate(name="John", surname="Doe", password="password123")
        assert schema.name == "John"
        assert schema.surname == "Doe"
        assert schema.password == "password123"

    def test_user_create_schema_missing_fields(self):
        """Test UserCreate schema with missing fields."""
        with pytest.raises(TypeError):
            # Missing required fields
            UserCreate(name="John")  # type: ignore

        with pytest.raises(TypeError):
            UserCreate(name="John", surname="Doe")  # Missing password

    def test_user_update_schema(self):
        """Test UserUpdate schema with optional fields."""
        # All fields provided
        schema = UserUpdate(name="John", surname="Doe", password="password123")
        assert schema.name == "John"
        assert schema.surname == "Doe"
        assert schema.password == "password123"

        # Partial update - only name
        schema = UserUpdate(name="John")
        assert schema.name == "John"
        assert schema.surname is None
        assert schema.password is None

        # Empty update
        schema = UserUpdate()
        assert schema.name is None
        assert schema.surname is None
        assert schema.password is None

    def test_user_response_schema(self):
        """Test UserResponse schema structure."""
        from datetime import datetime

        now = datetime.utcnow()
        schema = UserResponse(
            id=1,
            name="John",
            surname="Doe",
            created_at=now,
            updated_at=now
        )

        assert schema.id == 1
        assert schema.name == "John"
        assert schema.surname == "Doe"
        assert schema.created_at == now
        assert schema.updated_at == now

    def test_schema_immutability(self):
        """Test that schemas are immutable (msgspec Struct behavior)."""
        schema = UserCreate(name="John", surname="Doe", password="password123")

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            schema.name = "Jane"  # type: ignore

    def test_schema_serialization(self):
        """Test schema JSON serialization."""
        import json

        schema = UserCreate(name="John", surname="Doe", password="password123")

        # Convert to dict (msgspec Struct has to_dict method)
        data = schema.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert parsed["name"] == "John"
        assert parsed["surname"] == "Doe"
        assert parsed["password"] == "password123"


class TestDatabaseConstraints:
    """Test database-level constraints and validations."""

    @pytest.mark.asyncio
    async def test_unique_constraints(self, db_session: AsyncSession):
        """Test database unique constraints (if any)."""
        # Note: Current schema doesn't have unique constraints
        # This test serves as a placeholder for future constraints

        # Create two users with same data (should succeed)
        user1 = User(name="Same", surname="Name", password="pass1")
        user2 = User(name="Same", surname="Name", password="pass2")

        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()

        # Both should be created successfully
        assert user1.id is not None
        assert user2.id is not None
        assert user1.id != user2.id

    @pytest.mark.asyncio
    async def test_not_null_constraints(self, db_session: AsyncSession):
        """Test NOT NULL constraints on required fields."""
        # Try to create user with None values (should fail at database level)
        user = User(name=None, surname=None, password=None)  # type: ignore

        db_session.add(user)

        # This should raise an exception due to NOT NULL constraints
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            await db_session.commit()

        # Rollback the failed transaction
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_session: AsyncSession):
        """Test foreign key constraints (if any)."""
        # Note: Current schema has no foreign keys
        # This test serves as a placeholder for future relationships
        pass


class TestModelSerialization:
    """Test model data serialization and deserialization."""

    @pytest.mark.asyncio
    async def test_model_to_dict_conversion(self, db_session: AsyncSession):
        """Test converting model instances to dictionaries."""
        user = User(
            name="Serialization",
            surname="Test",
            password="serial123"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Convert to dict (manual implementation)
        user_dict = {
            "id": user.id,
            "name": user.name,
            "surname": user.surname,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

        # Verify structure
        assert user_dict["id"] is not None
        assert user_dict["name"] == "Serialization"
        assert user_dict["surname"] == "Test"
        assert user_dict["created_at"] is not None
        assert user_dict["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_bulk_operations(self, db_session: AsyncSession):
        """Test bulk database operations."""
        # Create multiple users
        users = [
            User(name=f"User{i}", surname=f"Surname{i}", password=f"pass{i}")
            for i in range(5)
        ]

        # Bulk insert
        db_session.add_all(users)
        await db_session.commit()

        # Refresh all users
        for user in users:
            await db_session.refresh(user)

        # Verify all were created
        assert all(user.id is not None for user in users)
        assert all(user.created_at is not None for user in users)

        # Bulk query
        query = select(User).where(User.name.like("User%")).order_by(User.name)
        result = await db_session.execute(query)
        retrieved_users = result.scalars().all()

        assert len(retrieved_users) == 5
        assert all(user.name.startswith("User") for user in retrieved_users)
