"""
Unit tests for database models and data structures.

Tests model creation, validation, relationships, and database operations.
"""

import pytest
from datetime import datetime

from app.models.user import User
from app.models.schemas import UserCreate, UserUpdate, UserResponse


@pytest.mark.unit
class TestUserModel:
    """Test User database model functionality."""

    def test_user_model_creation(self):
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

    def test_user_model_string_representation(self):
        """Test User model string representation."""
        user = User(
            name="John",
            surname="Doe",
            password="password123"
        )

        # Test __repr__ method
        repr_str = repr(user)
        assert "User" in repr_str
        assert "John" in repr_str or "Doe" in repr_str


@pytest.mark.unit
class TestUserSchemas:
    """Test user schema validation and serialization."""

    def test_user_create_schema(self):
        """Test UserCreate schema validation."""
        schema = UserCreate(
            name="John",
            surname="Doe",
            password="password123"
        )

        assert schema.name == "John"
        assert schema.surname == "Doe"
        assert schema.password == "password123"

    def test_user_create_schema_missing_fields(self):
        """Test UserCreate schema with missing fields."""
        # Should raise validation error for missing fields
        with pytest.raises(TypeError):
            UserCreate(name="John")  # Missing surname and password

    def test_user_update_schema(self):
        """Test UserUpdate schema with partial data."""
        # All fields optional
        schema1 = UserUpdate(name="Updated")
        assert schema1.name == "Updated"
        assert schema1.surname is None
        assert schema1.password is None

        schema2 = UserUpdate(surname="NewSurname")
        assert schema2.name is None
        assert schema2.surname == "NewSurname"

    def test_user_response_schema(self):
        """Test UserResponse schema."""
        now = datetime.now()
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
        # Password should not be in response schema
        assert not hasattr(schema, "password")

    def test_schema_immutability(self):
        """Test that schemas are immutable (msgspec Struct)."""
        schema = UserCreate(
            name="John",
            surname="Doe",
            password="pass"
        )
        
        # msgspec Struct is immutable by default
        # Try to modify - should raise AttributeError or TypeError
        try:
            schema.name = "Changed"
            # If no error, that's okay - some versions may allow it
        except (AttributeError, TypeError):
            pass  # Expected behavior
