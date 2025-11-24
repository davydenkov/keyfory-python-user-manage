# User Management REST API

REST API for user management built with LiteStar, PostgreSQL, and RabbitMQ.


### Features

- ✅ Full CRUD operations for users
- ✅ Swagger/OpenAPI documentation
- ✅ Structured logging with trace_id support using structlog
- ✅ RabbitMQ integration for event publishing
- ✅ PostgreSQL database with SQLAlchemy
- ✅ Docker support

## Architecture

### System Overview

This application implements a **REST API for user management** with the following architectural components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REST API      │    │   Database      │    │  Message Queue  │
│   (LiteStar)    │◄──►│  (PostgreSQL)   │    │   (RabbitMQ)    │
│                 │    │                 │    │                 │
│ • CRUD Users    │    │ • User Storage  │    │ • Event Pub/Sub │
│ • Input Valid.  │    │ • Auto Timestamps│    │ • Async Proc.   │
│ • OpenAPI Docs  │    │ • ACID Trans.   │    │ • Trace Correl. │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │  Structured     │
                    │   Logging       │
                    │  (structlog)    │
                    │                 │
                    │ • Request Trace │
                    │ • Error Track   │
                    │ • JSON Output   │
                    └─────────────────┘
```

### Key Design Patterns

- **Event-Driven Architecture**: User operations publish events for loose coupling
- **Dependency Injection**: Clean separation via LiteStar's DI container
- **Repository Pattern**: Database operations abstracted through SQLAlchemy
- **Middleware Pattern**: Cross-cutting concerns (logging, tracing) handled centrally
- **Async/Await**: Full asynchronous processing for high concurrency

## Prerequisites

- **Python 3.12+** - Required for modern async features and optimal performance
- **Docker & Docker Compose** - For infrastructure (PostgreSQL, RabbitMQ)
- **Git** - For version control

### Required Python Packages

The application requires these key packages:
- `pydantic` - Data validation and serialization
- `pydantic-settings` - Settings management
- `litestar` - Web framework
- `advanced-alchemy` - Enhanced SQLAlchemy async support
- `asyncpg` - PostgreSQL async driver
- `aio-pika` - RabbitMQ client

**Automatic Installation**: Run `./setup.sh` to install all dependencies automatically.

**Manual Installation**:
```bash
pip install pydantic pydantic-settings litestar[standard] sqlalchemy aio-pika
```

### Troubleshooting

#### Import Errors

**ModuleNotFoundError: No module named 'pydantic_settings'**
```bash
# Install missing packages
pip install pydantic pydantic-settings

# Or run the automated setup
./setup.sh
```

**ModuleNotFoundError: No module named 'litestar'**
```bash
# Install web framework
pip install litestar[standard]

# Or run the automated setup
./setup.sh
```

**ModuleNotFoundError: No module named 'litestar.config.openapi'**
```bash
# This usually means LiteStar is not installed or import paths have changed
pip install litestar[standard]

# If still failing, try reinstalling
pip uninstall litestar -y && pip install litestar[standard]

# Or run the automated setup
./setup.sh
```

**ImportError: cannot import name 'SQLAlchemyAsyncConfig' from 'advanced_alchemy'**
```bash
# This usually means advanced-alchemy is not installed or API has changed
pip install advanced-alchemy

# If still failing, try reinstalling
pip uninstall advanced-alchemy -y && pip install advanced-alchemy

# Or run the automated setup
./setup.sh
```

**ModuleNotFoundError: No module named 'asyncpg'**
```bash
# PostgreSQL async driver is required for database connections
pip install asyncpg

# Or run the automated setup
./setup.sh
```

**TypeError: OpenAPIConfig.__init__() got an unexpected keyword argument 'license_info'**
```bash
# This usually means you're using a different version of LiteStar where parameter names have changed
# The parameter should be 'license' instead of 'license_info'
# The application will automatically fall back to basic OpenAPI config if this occurs

# To fix permanently, ensure you have the correct LiteStar version:
pip install litestar[standard]

# Or run the automated setup
./setup.sh
```

**ImproperlyConfiguredException: A status code 204, 304 or in the range below 200 does not support a response body**
```bash
# This occurs when DELETE operations try to return a response body with status codes that don't allow bodies
# The fix is to change the status code to 200 (OK) for DELETE operations that return confirmation messages

# Check that your DELETE route handlers use status_code=200 if they return response bodies
@delete("/path", status_code=200)  # ✅ Allows response body
async def delete_handler(self) -> dict:
    return {"message": "Deleted successfully"}

# Status codes 204, 304, and codes below 200 do not allow response bodies
@delete("/path")  # ❌ Defaults to 204, no response body allowed
async def delete_handler(self):
    return {"message": "Deleted successfully"}
```

**InvalidAuthorizationSpecificationError: role "user_manager" does not exist**
```bash
# This PostgreSQL error occurs when the database user doesn't exist or services aren't running

# Option 1: Quick fix script (recommended for existing databases)
./fix-db-user.sh
# This script creates the user_manager role in your existing database

# Option 2: Use the automated setup (for fresh installations)
./setup.sh
# This automatically creates the PostgreSQL user and database

# Option 3: Manual setup
# 1. Start Docker services (required for database and message queue)
docker-compose up -d

# 2. Wait for services to be healthy
docker-compose ps                    # Check service status
docker-compose logs postgres        # Check PostgreSQL startup logs

# 3. Create the database user manually
docker-compose exec postgres psql -U postgres -c "
    CREATE ROLE user_manager LOGIN PASSWORD 'password';
    CREATE DATABASE user_management OWNER user_manager;
    GRANT ALL PRIVILEGES ON DATABASE user_management TO user_manager;
"

# 4. Verify database connectivity
docker-compose exec postgres psql -U user_manager -d user_management -c "SELECT version();"

# Option 4: If issues persist, reset the database (WARNING: deletes all data)
docker-compose down -v             # Remove containers and volumes
docker-compose up -d               # Recreate fresh services

# Default connection settings (from env-example.txt):
# DATABASE_URL=postgresql+asyncpg://user_manager:password@localhost:5432/user_management
```

#### Database Connection Issues

**Connection refused / No such file or directory**
```bash
# Start database services
docker-compose up -d postgres

# Wait for database to be ready
docker-compose logs postgres
```

#### RabbitMQ Connection Issues

**Connection refused**
```bash
# Start message queue services
docker-compose up -d rabbitmq

# Check RabbitMQ status
docker-compose logs rabbitmq
```

#### Port Already in Use

**Address already in use**
```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
PORT=8001 python run.py
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Runtime** | Python 3.12+ | Modern async features and performance |
| **Backend Framework** | LiteStar 2.x | High-performance async web framework |
| **Database** | PostgreSQL 15 + Advanced SQLAlchemy | Robust data persistence with async support |
| **Message Queue** | RabbitMQ + aio-pika + faststream | Event-driven architecture and decoupling |
| **Logging** | structlog | Structured JSON logging with trace correlation |
| **Serialization** | msgspec | Fast JSON/MessagePack serialization |
| **Testing** | pytest + pytest-asyncio | Comprehensive async test suite |
| **Infrastructure** | Docker + docker-compose | Containerized development environment |

## Quick Start

### Automated Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone git@github.com:davydenkov/keyfory-python-user-manage.git
   cd keyfory-python-user-manage
   ```

2. **Run the automated setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   This will automatically:
   - ✅ Create Python virtual environment
   - ✅ Install all dependencies
   - ✅ Start Docker services (PostgreSQL + RabbitMQ)
   - ✅ PostgreSQL auto-creates user and database via init script (with fallback)
   - ✅ Configure development environment

3. **Run the application**
   ```bash
   source venv/bin/activate
   python run.py
   ```
   **Note**: If you haven't run `./setup.sh` first, the application will automatically detect missing database users and set them up.

5. **Access the application**
   - **API**: http://localhost:8000
   - **Swagger UI**: http://localhost:8000/schema
   - **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### Manual Setup

If you prefer manual setup or the automated script doesn't work:

1. **Prerequisites**
   - Python 3.12+
   - Docker & Docker Compose

2. **Start infrastructure**
   ```bash
   docker-compose up -d
   ```

3. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install python-dotenv "litestar[standard]" litestar-granian litestar-asyncpg advanced-alchemy msgspec structlog aio-pika faststream
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/` | Get list of users (paginated) |
| GET | `/users/{id}` | Get user by ID |
| POST | `/users/` | Create new user |
| PUT | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Delete user |

### Example API Usage

**Create a user:**
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John",
    "surname": "Doe",
    "password": "securepassword"
  }'
```

**Get users:**
```bash
curl "http://localhost:8000/users/"
```

## Logging and Trace ID

The API includes comprehensive logging with trace_id support:

- Each request gets a unique trace_id (from X-Request-Id header or auto-generated)
- All logs include the trace_id for request tracking
- Request start/end, execution time, and errors are logged
- trace_id is returned in X-Trace-Id response header

Example log output:
```json
{"event": "Request started", "trace_id": "12345678-1234-1234-1234-123456789abc", "method": "POST", "path": "/users/", "timestamp": "2025-01-01T12:00:00.000000Z"}
{"event": "Request completed", "trace_id": "12345678-1234-1234-1234-123456789abc", "method": "POST", "path": "/users/", "status": 201, "execution_time": "0.0456s", "timestamp": "2025-01-01T12:00:00.045600Z"}
```

## RabbitMQ Events

User CRUD operations publish events to RabbitMQ:

- `user.created` - When a user is created
- `user.updated` - When a user is updated
- `user.deleted` - When a user is deleted

The consumer logs these events with the same trace_id for end-to-end tracking.

## Project Structure

```
keyfory-python-user-manage/
├── app/                          # Main application package
│   ├── api/v1/users.py          # User CRUD API endpoints
│   ├── config/settings.py       # Application configuration
│   ├── database/                # Database layer
│   │   ├── config.py           # Connection & session management
│   │   └── models.py           # SQLAlchemy models
│   ├── middleware/logging.py    # Request tracing middleware
│   ├── models/                  # Data models & schemas
│   │   ├── user.py             # User database model
│   │   └── schemas.py          # API request/response schemas
│   ├── rabbitmq/               # Message queue integration
│   │   ├── producer.py         # Event publishing
│   │   └── consumer.py         # Event consumption
│   └── main.py                 # Application entry point
├── tests/                       # Test suite
│   └── test_user_api.py        # API endpoint tests
├── docker-compose.yml           # Infrastructure configuration
├── pyproject.toml              # Python project metadata
├── run.py                      # Application runner script
├── setup.sh                    # Automated setup script
├── README.md                   # This documentation
├── API_REFERENCE.md            # Comprehensive API reference
├── DEPLOYMENT.md               # Production deployment guide
├── CONTRIBUTING.md             # Contribution guidelines
└── IMPLEMENTATION_SUMMARY.md   # Detailed implementation notes
```

## 📚 Documentation

This project includes comprehensive documentation for all audiences:

### 🚀 **Getting Started**
- **[README.md](README.md)** - Quick start guide and project overview
- **[setup.sh](setup.sh)** - Automated development environment setup
- **[run.py](run.py)** - Application runner script

### 👨‍💻 **For Developers**
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation with examples
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details
- **[pyproject.toml](pyproject.toml)** - Project configuration and dependencies

### 🏗️ **For DevOps & Deployers**
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment and scaling guide
- **[docker-compose.yml](docker-compose.yml)** - Infrastructure configuration with detailed comments

### 🤝 **For Contributors**
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and development workflow
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes

### 🧪 **For Testers**
- **tests/** - Comprehensive test suite with examples
- **pytest configuration** in pyproject.toml

## Database Schema

### User Table

```sql
CREATE TABLE "user" (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name TEXT NOT NULL,
    surname TEXT NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_user_id ON "user"(id);
CREATE INDEX idx_user_created_at ON "user"(created_at);
```

**Field Descriptions:**
- `id`: Auto-incrementing primary key (BIGINT for scalability)
- `name`: User's first name (required)
- `surname`: User's last name/family name (required)
- `password`: User password (should be hashed in production)
- `created_at`: Automatic UTC timestamp on creation
- `updated_at`: Automatic UTC timestamp on updates

## Development

### Environment Setup

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Install development dependencies** (if needed)
   ```bash
   pip install pytest pytest-asyncio
   ```

### Running Tests

The project includes comprehensive test suites with multiple test categories:

#### Quick Test Commands

```bash
# Run all tests (excluding slow performance tests)
python test_run.py

# Run specific test categories
python test_run.py --api          # API endpoint tests
python test_run.py --unit         # Unit tests
python test_run.py --integration  # Integration tests
python test_run.py --validation   # Input validation tests
python test_run.py --middleware   # Middleware tests
python test_run.py --models       # Database model tests

# Run performance tests (slow)
python test_run.py --performance

# Run with coverage report
python test_run.py --coverage

# Run all tests including slow ones
python test_run.py --no-slow
```

#### Manual Pytest Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_user_api.py -v

# Run tests with specific marker
pytest -m "api"

# Run tests and stop on first failure
pytest --tb=short
```

#### Test Categories

- **Unit Tests**: Individual component testing
- **API Tests**: REST endpoint functionality
- **Integration Tests**: Component interaction testing
- **Validation Tests**: Input validation and error handling
- **Middleware Tests**: Logging and request processing
- **Model Tests**: Database model and schema testing
- **Performance Tests**: Response time and load testing

**Test Coverage:**
- ✅ User CRUD operations
- ✅ Input validation and error handling
- ✅ Pagination functionality
- ✅ Trace ID header validation
- ✅ HTTP status codes
- ✅ Data integrity
- ✅ Database constraints
- ✅ Concurrent operations
- ✅ Performance benchmarks

### Database Management

**Automatic Table Creation:**
The application automatically creates database tables on startup using SQLAlchemy's `create_all()`.

**For Production:**
Consider using Alembic for proper database migrations:

```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Create user table"

# Apply migration
alembic upgrade head
```

### Code Quality

**Formatting and Linting:**
```bash
# Install development tools
pip install black isort flake8 mypy

# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/
mypy app/
```

**Pre-commit Hooks:**
Consider setting up pre-commit hooks for automatic code quality checks:

```bash
pip install pre-commit
pre-commit install
```

### API Documentation

**Swagger/OpenAPI:**
- Interactive API documentation: http://localhost:8000/schema
- Auto-generated from type hints and docstrings
- Test API endpoints directly from the browser

**Additional Documentation:**
- `IMPLEMENTATION_SUMMARY.md`: Detailed technical implementation notes
- Inline code documentation with comprehensive docstrings
- Type hints for better IDE support and validation

## Deployment

### Production Considerations

1. **Password Hashing**: Implement proper password hashing (bcrypt, argon2)
2. **Input Validation**: Add comprehensive input validation
3. **Authentication**: Add JWT or session-based authentication
4. **Rate Limiting**: Implement rate limiting middleware
5. **Database Migrations**: Use Alembic for database migrations
6. **Environment Variables**: Use proper environment variable management
7. **Health Checks**: Add health check endpoints
8. **Monitoring**: Integrate with monitoring tools (Prometheus, Grafana)

### Docker Production Build

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-dev

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
