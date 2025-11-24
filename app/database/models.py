"""
Base database models and metadata configuration.

This module defines the base SQLAlchemy model class that all database models
inherit from. It also imports all model classes for easy access and ensures
they are registered with SQLAlchemy's metadata system.
"""

from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy database models.

    This declarative base provides the foundation for all database tables
    in the application. It includes metadata that SQLAlchemy uses to
    create, manage, and interact with database tables.

    All models should inherit from this base class to ensure they are
    properly registered with SQLAlchemy's metadata system.

    Example:
        class MyModel(Base):
            __tablename__ = "my_table"
            id = Column(Integer, primary_key=True)
    """
    pass


# Import all model classes here to ensure they are registered with SQLAlchemy
# This allows SQLAlchemy to discover and manage all tables
from app.models.user import User
