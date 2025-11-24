# Production Deployment Guide

## Overview

This guide covers deploying the User Management API to production environments. The application is designed to be cloud-native and can be deployed to various platforms including Docker, Kubernetes, and traditional servers.

## Prerequisites

- Docker & Docker Compose
- Python 3.12+
- PostgreSQL 15+
- RabbitMQ 3.12+
- Reverse proxy (nginx/Caddy/Traefik)

## Quick Deployment

### 1. Infrastructure Setup

```bash
# Clone repository
git clone <git@github.com:davydenkov/keyfory-python-user-manage.git>
cd keyfory-python-user-manage

# Start infrastructure services
docker-compose up -d postgres rabbitmq

# Wait for services to be healthy
docker-compose ps
```

### 2. Environment Configuration

Create production environment file:

```bash
# .env.production
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:secure_password@postgres:5432/user_management

# RabbitMQ Configuration
RABBITMQ_URL=amqp://user:secure_password@rabbitmq:5672/

# Application Configuration
APP_NAME=keyfory-python-user-manage
APP_VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security (generate strong secrets)
SECRET_KEY=your-256-bit-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Logging Configuration
LOG_LEVEL=INFO

# Redis (optional, for caching)
REDIS_URL=redis://redis:6379/0
```

### 3. Application Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or run directly
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Docker Deployment

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/user_management
      - RABBITMQ_URL=amqp://user:password@rabbitmq:5672/
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    environment:
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  rabbitmq:
    environment:
      RABBITMQ_DEFAULT_USER: user
      RABBITMQ_DEFAULT_PASS: secure_password_here
    volumes:
      - rabbitmq_prod_data:/var/lib/rabbitmq

volumes:
  postgres_prod_data:
  rabbitmq_prod_data:
```

### Production Dockerfile

```dockerfile
# Dockerfile.prod
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-dev

# Copy application code
COPY app/ ./app/

# Change ownership
RUN chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Kubernetes Deployment

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: user-management
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-management-config
  namespace: user-management
data:
  APP_NAME: "keyfory-python-user-manage"
  APP_VERSION: "1.0.0"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: user-management-secret
  namespace: user-management
type: Opaque
data:
  # Base64 encoded values
  DATABASE_PASSWORD: <base64-encoded-password>
  RABBITMQ_PASSWORD: <base64-encoded-password>
  SECRET_KEY: <base64-encoded-secret>
```

### PostgreSQL Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: user-management
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: "user_management"
        - name: POSTGRES_USER
          value: "user"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: user-management-secret
              key: DATABASE_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

### RabbitMQ Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rabbitmq
  namespace: user-management
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
      - name: rabbitmq
        image: rabbitmq:3-management
        env:
        - name: RABBITMQ_DEFAULT_USER
          value: "user"
        - name: RABBITMQ_DEFAULT_PASS
          valueFrom:
            secretKeyRef:
              name: user-management-secret
              key: RABBITMQ_PASSWORD
        ports:
        - containerPort: 5672
        - containerPort: 15672
        volumeMounts:
        - name: rabbitmq-storage
          mountPath: /var/lib/rabbitmq
      volumes:
      - name: rabbitmq-storage
        persistentVolumeClaim:
          claimName: rabbitmq-pvc
```

### API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-management-api
  namespace: user-management
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-management-api
  template:
    metadata:
      labels:
        app: user-management-api
    spec:
      containers:
      - name: api
        image: your-registry/user-management-api:latest
        env:
        - name: DATABASE_URL
          value: "postgresql+asyncpg://user:$(DATABASE_PASSWORD)@postgres:5432/user_management"
        - name: RABBITMQ_URL
          value: "amqp://user:$(RABBITMQ_PASSWORD)@rabbitmq:5672/"
        envFrom:
        - configMapRef:
            name: user-management-config
        - secretRef:
            name: user-management-secret
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-management-api
  namespace: user-management
spec:
  selector:
    app: user-management-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: user-management-api
  namespace: user-management
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: user-management-api
            port:
              number: 80
```

## Security Configuration

### 1. Password Security

```python
# app/utils/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 2. JWT Authentication

```python
# app/utils/auth.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    # Get user from database
    return user_id
```

### 3. CORS Configuration

```python
# app/config/cors.py
from fastapi.middleware.cors import CORSMiddleware

# Production CORS settings
cors_origins = [
    "https://yourfrontend.com",
    "https://admin.yourfrontend.com",
]

cors_middleware = CORSMiddleware(
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 4. Rate Limiting

```python
# app/middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.window_seconds
            ]

        # Check rate limit
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Too many requests")

        # Add current request
        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        return response
```

## Monitoring & Observability

### 1. Health Checks

```python
# app/api/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import aio_pika

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}

@router.get("/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_session)
):
    """Readiness check with database connectivity."""
    try:
        # Test database connection
        await session.execute("SELECT 1")

        # Test RabbitMQ connection (if needed)
        # connection = await aio_pika.connect(settings.rabbitmq_url)
        # await connection.close()

        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Service unavailable")
```

### 2. Prometheus Metrics

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

# Database metrics
DB_CONNECTIONS = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

# Business metrics
USER_CREATED = Counter(
    'users_created_total',
    'Total number of users created'
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)

    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 3. Structured Logging

```python
# app/config/logging.py
import logging
import structlog
from pythonjsonlogger import jsonlogger

def setup_logging(log_level: str = "INFO"):
    """Configure structured JSON logging."""

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    # Configure structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure JSON logging for third-party libraries
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter())
    logging.getLogger().addHandler(handler)
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Indexes for performance
CREATE INDEX CONCURRENTLY idx_user_email ON "user"(email);
CREATE INDEX CONCURRENTLY idx_user_created_at ON "user"(created_at DESC);
CREATE INDEX CONCURRENTLY idx_user_updated_at ON "user"(updated_at DESC);

-- Partitioning for large datasets (if needed)
-- CREATE TABLE user_y2024 PARTITION OF "user"
--     FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### 2. Caching Strategy

```python
# app/utils/cache.py
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

async def get_cached_user(user_id: int) -> Optional[dict]:
    """Get user from cache."""
    key = f"user:{user_id}"
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None

async def set_cached_user(user_id: int, user_data: dict, ttl: int = 300):
    """Cache user data with TTL."""
    key = f"user:{user_id}"
    await redis_client.setex(key, ttl, json.dumps(user_data))

async def invalidate_user_cache(user_id: int):
    """Remove user from cache."""
    key = f"user:{user_id}"
    await redis_client.delete(key)
```

### 3. Connection Pooling

```python
# app/database/config.py
from sqlalchemy.ext.asyncio import create_async_engine

# Production database configuration
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Disable in production
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Max overflow connections
    pool_timeout=30,  # Connection timeout
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Test connections before use
)
```

## Backup & Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/user_management_$DATE.sql"

# Create backup
docker exec postgres pg_dump -U user user_management > "$BACKUP_FILE"

# Compress
gzip "$BACKUP_FILE"

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
```

### Disaster Recovery

```bash
# Restore from backup
gunzip backup_file.sql.gz
docker exec -i postgres psql -U user user_management < backup_file.sql
```

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use nginx, HAProxy, or cloud load balancer
2. **Session Management**: Use Redis for session storage
3. **Database**: Consider read replicas for read-heavy workloads
4. **Message Queue**: Scale RabbitMQ cluster as needed

### Vertical Scaling

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Auto-scaling**: Configure based on CPU/memory metrics
3. **Database**: Increase instance size for better performance

### Microservices Split (Future)

If the application grows, consider splitting into microservices:

- **User Service**: User CRUD operations
- **Auth Service**: Authentication and authorization
- **Notification Service**: Email and push notifications
- **Analytics Service**: User analytics and reporting

## Compliance & Security

### GDPR Compliance

1. **Data Encryption**: Encrypt sensitive data at rest and in transit
2. **Data Retention**: Implement data retention policies
3. **Right to Deletion**: Support user data deletion
4. **Audit Logging**: Log all data access and modifications

### Security Headers

```python
# app/middleware/security.py
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   docker exec postgres pg_isready -U user -d user_management
   ```

2. **RabbitMQ Connection Issues**
   ```bash
   # Check RabbitMQ status
   docker exec rabbitmq rabbitmq-diagnostics ping
   ```

3. **Application Health**
   ```bash
   # Check application health
   curl http://localhost:8000/health
   ```

### Monitoring Commands

```bash
# View application logs
docker-compose logs -f api

# Check resource usage
docker stats

# Database performance
docker exec postgres psql -U user -d user_management -c "SELECT * FROM pg_stat_activity;"

# RabbitMQ management
open http://localhost:15672
```

## Maintenance Tasks

### Regular Maintenance

1. **Update Dependencies**: Monthly security updates
2. **Database Vacuum**: Regular maintenance for PostgreSQL
3. **Log Rotation**: Implement log rotation policies
4. **Backup Verification**: Test backup restoration regularly

### Emergency Procedures

1. **Application Restart**
   ```bash
   docker-compose restart api
   ```

2. **Database Recovery**
   ```bash
   # Stop application
   docker-compose stop api

   # Restore database
   gunzip backup.sql.gz
   docker exec -i postgres psql -U user user_management < backup.sql

   # Restart application
   docker-compose start api
   ```

This deployment guide provides a comprehensive foundation for production deployment. Adjust configurations based on your specific requirements and infrastructure.
