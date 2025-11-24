# User Management API Reference

## Overview

This document provides comprehensive API reference documentation for the User Management REST API. The API follows RESTful conventions and provides complete CRUD operations for user management with event-driven architecture.

## Base URL

```
http://localhost:8000
```

## Authentication

**Current Implementation**: No authentication required (development mode)

**Production Recommendation**: Implement JWT Bearer token authentication

## Headers

### Request Headers

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| `Content-Type` | Yes (POST/PUT) | Request content type | `application/json` |
| `X-Request-Id` | No | Client-provided trace ID | `abc-123-def` |

### Response Headers

| Header | Description | Example |
|--------|-------------|---------|
| `Content-Type` | Response content type | `application/json` |
| `X-Trace-Id` | Server-generated trace ID | `550e8400-e29b-41d4-a716-446655440000` |

---

## Users API

### List Users

Retrieve a paginated list of users.

```http
GET /users/?page=1&per_page=10
```

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number (1-based) |
| `per_page` | integer | No | 10 | Items per page (max 100) |

#### Response

**Status**: `200 OK`

```json
{
  "users": [
    {
      "id": 1,
      "name": "John",
      "surname": "Doe",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10
}
```

#### Error Responses

**Status**: `400 Bad Request` - Invalid query parameters

---

### Get User

Retrieve a specific user by ID.

```http
GET /users/{user_id}
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | User unique identifier |

#### Response

**Status**: `200 OK`

```json
{
  "id": 1,
  "name": "John",
  "surname": "Doe",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:00:00Z"
}
```

#### Error Responses

**Status**: `404 Not Found` - User not found

---

### Create User

Create a new user.

```http
POST /users/
Content-Type: application/json
```

#### Request Body

```json
{
  "name": "John",
  "surname": "Doe",
  "password": "securepassword123"
}
```

#### Request Schema

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | Yes | 1-255 chars | User's first name |
| `surname` | string | Yes | 1-255 chars | User's last name |
| `password` | string | Yes | 1+ chars | User's password |

#### Response

**Status**: `201 Created`

```json
{
  "id": 1,
  "name": "John",
  "surname": "Doe",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:00:00Z"
}
```

#### Error Responses

**Status**: `422 Unprocessable Entity` - Invalid request data

---

### Update User

Update an existing user (partial update supported).

```http
PUT /users/{user_id}
Content-Type: application/json
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | User unique identifier |

#### Request Body

```json
{
  "name": "Jane",
  "surname": "Smith"
}
```

#### Request Schema

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | No | 1-255 chars | User's first name |
| `surname` | string | No | 1-255 chars | User's last name |
| `password` | string | No | 1+ chars | User's password |

#### Response

**Status**: `200 OK`

```json
{
  "id": 1,
  "name": "Jane",
  "surname": "Smith",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:30:00Z"
}
```

#### Error Responses

**Status**: `404 Not Found` - User not found
**Status**: `422 Unprocessable Entity` - Invalid request data

---

### Delete User

Delete a user by ID.

```http
DELETE /users/{user_id}
```

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | User unique identifier |

#### Response

**Status**: `200 OK`

```json
{
  "message": "User with id 1 has been deleted"
}
```

#### Error Responses

**Status**: `404 Not Found` - User not found

---

## Event System

### User Events

The API publishes events to RabbitMQ for all user operations:

#### Event Types

| Event Type | Trigger | Routing Key |
|------------|---------|-------------|
| `user.created` | User creation | `user.created` |
| `user.updated` | User update | `user.updated` |
| `user.deleted` | User deletion | `user.deleted` |

#### Event Payload Structure

```json
{
  "event_type": "user.created",
  "data": {
    "user_id": 123
  },
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Event Consumer

The application includes a consumer that logs all events:

```
INFO - Received event user.created with user_id=123
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "User with id 999 not found",
  "status_code": 404,
  "extra": null
}
```

### Common HTTP Status Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| `200` | OK | Successful GET, PUT, DELETE |
| `201` | Created | Successful POST |
| `400` | Bad Request | Invalid query parameters |
| `404` | Not Found | User doesn't exist |
| `422` | Unprocessable Entity | Invalid request body |
| `500` | Internal Server Error | Server-side errors |

---

## Rate Limiting

**Current Implementation**: No rate limiting

**Production Recommendation**: Implement rate limiting middleware

---

## Data Validation

### Input Validation Rules

- **Names**: 1-255 characters, non-empty strings
- **Passwords**: 1+ characters (should be hashed)
- **IDs**: Positive integers

### Automatic Processing

- **Timestamps**: Automatically set in UTC
- **IDs**: Auto-generated sequential integers
- **Trimming**: Leading/trailing whitespace removed

---

## Pagination

### Default Behavior

- **Page**: 1 (first page)
- **Per Page**: 10 items
- **Maximum Per Page**: 100 items

### Response Metadata

```json
{
  "total": 150,
  "page": 2,
  "per_page": 20
}
```

### Calculating Pagination

```javascript
// Total pages calculation
const totalPages = Math.ceil(total / perPage);

// Current page info
const startItem = (page - 1) * perPage + 1;
const endItem = Math.min(page * perPage, total);
```

---

## Trace ID Tracking

### Request Flow

1. **Client Request**: Optional `X-Request-Id` header
2. **Server Processing**: Generate UUID if missing
3. **Logging**: All logs include trace_id
4. **Events**: RabbitMQ messages include trace_id
5. **Response**: `X-Trace-Id` header returned

### Log Correlation

```json
{
  "event": "Request started",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/users/",
  "timestamp": "2025-01-01T10:00:00.000000Z"
}
```

---

## SDK Examples

### JavaScript/Node.js

```javascript
const API_BASE = 'http://localhost:8000';

// Create user
async function createUser(userData) {
  const response = await fetch(`${API_BASE}/users/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-Id': 'custom-trace-123'
    },
    body: JSON.stringify(userData)
  });

  const traceId = response.headers.get('X-Trace-Id');
  return response.json();
}

// Get users with pagination
async function getUsers(page = 1, perPage = 10) {
  const response = await fetch(
    `${API_BASE}/users/?page=${page}&per_page=${perPage}`
  );
  return response.json();
}
```

### Python

```python
import httpx

API_BASE = "http://localhost:8000"

async def create_user(client: httpx.AsyncClient, user_data: dict) -> dict:
    response = await client.post(
        f"{API_BASE}/users/",
        json=user_data,
        headers={"X-Request-Id": "custom-trace-123"}
    )
    trace_id = response.headers.get("X-Trace-Id")
    return response.json()

async def get_users(client: httpx.AsyncClient, page: int = 1, per_page: int = 10) -> dict:
    response = await client.get(
        f"{API_BASE}/users/",
        params={"page": page, "per_page": per_page}
    )
    return response.json()
```

### cURL Examples

```bash
# List users
curl -X GET "http://localhost:8000/users/?page=1&per_page=10"

# Create user
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "surname": "Doe", "password": "secure123"}'

# Get specific user
curl -X GET "http://localhost:8000/users/1"

# Update user
curl -X PUT "http://localhost:8000/users/1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane"}'

# Delete user
curl -X DELETE "http://localhost:8000/users/1"

# With custom trace ID
curl -X GET "http://localhost:8000/users/" \
  -H "X-Request-Id: my-custom-trace-123"
```

---

## Monitoring & Observability

### Health Checks

**Current Implementation**: No health check endpoints

**Recommended**: Add `/health` and `/ready` endpoints

### Metrics

**Current Implementation**: Basic logging

**Recommended**: Add Prometheus metrics, request latency, error rates

### Tracing

**Current Implementation**: Basic trace_id correlation

**Recommended**: Distributed tracing with OpenTelemetry

---

## Production Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:secure_password@db:5432/user_management

# Message Queue
RABBITMQ_URL=amqp://user:secure_password@rabbitmq:5672/

# Security
SECRET_KEY=your-secret-key-here

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

### Security Considerations

1. **Password Hashing**: Implement bcrypt/argon2
2. **Input Validation**: Sanitize all inputs
3. **Rate Limiting**: Implement request rate limits
4. **CORS**: Configure appropriate origins
5. **HTTPS**: Enable SSL/TLS
6. **Authentication**: Add JWT or OAuth2

### Performance Optimization

1. **Database Indexing**: Add indexes for query optimization
2. **Caching**: Implement Redis for session/data caching
3. **Connection Pooling**: Configure database connection limits
4. **Async Processing**: Ensure all I/O operations are async

---

## Changelog

### Version 0.1.0
- Initial release with CRUD operations
- Event-driven architecture with RabbitMQ
- Structured logging with trace_id support
- OpenAPI/Swagger documentation
- Docker containerization
