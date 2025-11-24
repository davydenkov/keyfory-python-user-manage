#!/bin/bash

# ========================================================================
# Quick Fix Script: Create user_manager PostgreSQL User
# ========================================================================
#
# This script fixes the "role user_manager does not exist" error by
# creating the user_manager user in an existing PostgreSQL database.
#
# Usage:
#   chmod +x fix-db-user.sh
#   ./fix-db-user.sh
#
# ========================================================================

set -e

echo "🔧 Fixing PostgreSQL user_manager role..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Check if postgres container is running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "⚠️  PostgreSQL container is not running. Starting it..."
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo "⏳ Waiting for PostgreSQL to be ready..."
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        # Try postgres superuser first, then user_manager (in case POSTGRES_USER was set)
        if docker-compose exec -T postgres pg_isready -U postgres -h localhost > /dev/null 2>&1 || \
           docker-compose exec -T postgres pg_isready -U user_manager -h localhost > /dev/null 2>&1; then
            echo "✅ PostgreSQL is ready!"
            break
        fi
        echo "⏳ Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "❌ PostgreSQL failed to start"
        exit 1
    fi
fi

# Determine which superuser to use for administrative operations
# Try postgres first (default), fall back to user_manager if postgres doesn't exist
ADMIN_USER="postgres"
ADMIN_DB="postgres"  # Default admin database

# Try connecting as postgres user (default superuser)
if docker-compose exec -T postgres psql -U postgres -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
    ADMIN_USER="postgres"
    ADMIN_DB="postgres"
    echo "ℹ️  Using postgres as admin user"
elif docker-compose exec -T postgres psql -U user_manager -d user_management -c "SELECT 1;" > /dev/null 2>&1; then
    # If postgres user doesn't work, try user_manager (superuser if POSTGRES_USER was set)
    ADMIN_USER="user_manager"
    ADMIN_DB="user_management"
    echo "ℹ️  Using user_manager as admin user"
elif docker-compose exec -T postgres psql -U user_manager -d template1 -c "SELECT 1;" > /dev/null 2>&1; then
    # Try template1 database as fallback
    ADMIN_USER="user_manager"
    ADMIN_DB="template1"
    echo "ℹ️  Using user_manager with template1 database"
else
    echo "❌ Cannot connect to PostgreSQL with either postgres or user_manager superuser"
    echo "💡 Check Docker logs: docker-compose logs postgres"
    exit 1
fi

# Create the user_manager role if it doesn't exist (use admin superuser)
echo "👤 Creating user_manager role..."
CREATE_USER_SQL="
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_manager') THEN
      CREATE ROLE \"user_manager\" LOGIN PASSWORD 'password';
      RAISE NOTICE 'Created user \"user_manager\"';
   ELSE
      RAISE NOTICE 'User \"user_manager\" already exists';
   END IF;
END
\$\$;
"

if docker-compose exec -T postgres psql -U "$ADMIN_USER" -d "$ADMIN_DB" -c "$CREATE_USER_SQL" 2>/dev/null; then
    echo "✅ User creation command executed"
else
    echo "❌ Failed to create user. Check Docker logs: docker-compose logs postgres"
    exit 1
fi

# Ensure the database exists and grant privileges (use determined admin user)
echo "🗄️  Ensuring database exists and granting privileges..."
docker-compose exec -T postgres psql -U "$ADMIN_USER" -d "$ADMIN_DB" -c "
SELECT 'CREATE DATABASE user_management OWNER \"user_manager\"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user_management')\gexec
" 2>/dev/null || true

docker-compose exec -T postgres psql -U "$ADMIN_USER" -d "$ADMIN_DB" -c "GRANT ALL PRIVILEGES ON DATABASE user_management TO \"user_manager\";" 2>/dev/null || true

# Test the connection
echo "🔍 Testing connection as user_manager..."
if docker-compose exec -T postgres psql -U user_manager -d user_management -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Success! user_manager can now connect to the database."
    echo ""
    echo "📋 Next steps:"
    echo "   1. Restart your application"
    echo "   2. Verify connection: docker-compose exec postgres psql -U user_manager -d user_management -c 'SELECT 1;'"
else
    echo "⚠️  Connection test failed, but user was created."
    echo "💡 Try restarting the PostgreSQL container: docker-compose restart postgres"
fi

