# Contributing Guide

## Welcome

Thank you for your interest in contributing to the User Management API! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git
- Basic knowledge of FastAPI/LiteStar, SQLAlchemy, and RabbitMQ

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/keyfory-python-user-manage.git
   cd keyfory-python-user-manage
   ```

2. **Set up Development Environment**
   ```bash
   # Run automated setup
   chmod +x setup.sh
   ./setup.sh

   # Or manual setup
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -e .[dev]
   ```

3. **Start Infrastructure**
   ```bash
   docker-compose up -d
   ```

4. **Run Tests**
   ```bash
   pytest tests/ -v
   ```

5. **Start Development Server**
   ```bash
   python run.py
   ```

## Development Workflow

### 1. Choose an Issue

- Check existing [issues](../../issues) for tasks to work on
- Create a new issue if you have a feature request or bug report
- Comment on the issue to indicate you're working on it

### 2. Create a Feature Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Follow the coding standards below
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 4. Commit Changes

```bash
# Add your changes
git add .

# Commit with descriptive message
git commit -m "feat: add user search functionality

- Add search endpoint with query parameters
- Implement database filtering
- Add comprehensive tests
- Update API documentation"
```

#### Commit Message Format

We follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

**Examples:**
```
feat: add user search functionality
fix(auth): resolve token expiration issue
docs: update API reference
test: add integration tests for user CRUD
```

### 5. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create pull request on GitHub
# - Provide clear description
# - Reference related issues
# - Add screenshots for UI changes
```

## Coding Standards

### Python Code Style

We use [Black](https://black.readthedocs.io/) for code formatting and [isort](https://isort.readthedocs.io/) for import sorting.

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check style (optional)
flake8 app/ tests/
mypy app/
```

### Code Quality Guidelines

#### 1. Type Hints

Use type hints for all function parameters and return values:

```python
from typing import Optional, List

def get_user(user_id: int) -> Optional[User]:
    """Get user by ID."""
    pass

def get_users(limit: int = 10) -> List[User]:
    """Get list of users."""
    pass
```

#### 2. Docstrings

Use Google-style docstrings for all public functions, classes, and modules:

```python
def create_user(user_data: UserCreate) -> UserResponse:
    """
    Create a new user with the provided data.

    Args:
        user_data: Validated user creation data

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException: If user creation fails
    """
    pass
```

#### 3. Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately
- Don't expose sensitive information

```python
try:
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

#### 4. Async/Await

- Use async/await for all I/O operations
- Avoid blocking operations in async functions
- Use `asyncio.gather()` for concurrent operations

```python
async def get_user_with_posts(user_id: int) -> UserWithPosts:
    """Get user with their posts concurrently."""
    user_task = get_user(user_id)
    posts_task = get_user_posts(user_id)

    user, posts = await asyncio.gather(user_task, posts_task)
    return UserWithPosts(user=user, posts=posts)
```

### Database Guidelines

#### 1. Use SQLAlchemy ORM

```python
# Good - Uses ORM
user = User(name="John", surname="Doe")
session.add(user)
await session.commit()

# Avoid - Raw SQL
await session.execute("INSERT INTO user (name, surname) VALUES (?, ?)", "John", "Doe")
```

#### 2. Use Transactions

```python
async def create_user_with_profile(user_data: UserCreate) -> User:
    """Create user with profile in transaction."""
    async with session.begin():
        user = User(**user_data.dict())
        session.add(user)

        profile = UserProfile(user_id=user.id, bio="New user")
        session.add(profile)

        await session.commit()
        return user
```

#### 3. Use Selectin/Eager Loading

```python
# Good - Eager loading
query = select(User).options(selectinload(User.posts))

# Avoid - N+1 queries
users = await session.execute(select(User))
for user in users:
    posts = await session.execute(select(Post).where(Post.user_id == user.id))
```

### API Design Guidelines

#### 1. RESTful Endpoints

- Use appropriate HTTP methods
- Use plural nouns for resources
- Use nested resources when appropriate

```python
# Good REST design
GET    /users          # List users
POST   /users          # Create user
GET    /users/{id}     # Get user
PUT    /users/{id}     # Update user
DELETE /users/{id}     # Delete user
```

#### 2. Consistent Response Format

```python
# Success responses
{"data": {...}, "message": "Success"}

# Error responses
{"detail": "Error message", "code": "ERROR_CODE"}

# Paginated responses
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 100,
    "total_pages": 10
  }
}
```

#### 3. Input Validation

```python
class UserCreate(Struct):
    """User creation schema with validation."""
    name: str = Field(min_length=1, max_length=255)
    surname: str = Field(min_length=1, max_length=255)
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    age: int = Field(ge=0, le=150)
```

### Testing Guidelines

#### 1. Test Structure

```python
# tests/test_user_api.py
import pytest
from litestar.testing import TestClient

class TestUserAPI:
    def test_create_user_success(self, client: TestClient):
        """Test successful user creation."""
        pass

    def test_create_user_validation_error(self, client: TestClient):
        """Test user creation with invalid data."""
        pass

    def test_get_user_not_found(self, client: TestClient):
        """Test getting non-existent user."""
        pass
```

#### 2. Test Coverage

- Aim for 80%+ code coverage
- Test happy paths and error cases
- Test edge cases and boundary conditions
- Mock external dependencies

#### 3. Test Naming

```python
# Good test names
def test_create_user_with_valid_data_returns_201()
def test_create_user_with_duplicate_email_returns_409()
def test_get_user_with_invalid_id_returns_404()
```

## Documentation

### Code Documentation

- All public functions need docstrings
- Complex logic needs inline comments
- Update README for new features
- Update API documentation

### API Documentation

- Update OpenAPI schemas for new endpoints
- Document request/response formats
- Provide usage examples
- Document error conditions

## Pull Request Process

### 1. Before Submitting

- [ ] Tests pass (`pytest tests/`)
- [ ] Code formatted (`black app/ tests/`)
- [ ] Imports sorted (`isort app/ tests/`)
- [ ] Type checking passes (`mypy app/`)
- [ ] Documentation updated
- [ ] Commit messages follow conventions

### 2. PR Template

Please use this template for pull requests:

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No breaking changes
```

### 3. Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: At least one maintainer reviews
3. **Approval**: PR approved and merged
4. **Deployment**: Changes deployed to staging/production

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Step-by-step instructions
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, etc.
- **Logs**: Relevant log output
- **Screenshots**: If applicable

### Feature Requests

When requesting features, please include:

- **Description**: Clear description of the feature
- **Use Case**: Why this feature is needed
- **Proposed Solution**: How it should work
- **Alternatives**: Other solutions considered
- **Additional Context**: Any other relevant information

## Getting Help

### Communication Channels

- **Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Pull Requests**: For code contributions

### Resources

- [API Reference](API_REFERENCE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [README](README.md)

## Recognition

Contributors will be recognized in:
- Repository contributor list
- Changelog entries
- Release notes

Thank you for contributing to the User Management API! 🎉
