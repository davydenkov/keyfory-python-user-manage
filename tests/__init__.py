"""
Test package for User Management API.

This package contains comprehensive test suites for all components of the
User Management API including unit tests, integration tests, and end-to-end tests.

Test Categories:
- Unit tests: Individual components and functions
- Integration tests: Component interactions
- API tests: REST endpoint functionality
- Performance tests: Load and stress testing
- Validation tests: Input validation and error handling

Test Fixtures:
- test_client: LiteStar test client for API testing
- test_db: Database session fixtures for data setup
- test_user: Pre-created user fixtures
- test_rabbitmq: Message queue testing fixtures

Usage:
    # Run all tests
    pytest

    # Run with coverage
    pytest --cov=app --cov-report=html

    # Run specific test category
    pytest -m "unit"
    pytest -m "integration"
    pytest -m "api"
"""
