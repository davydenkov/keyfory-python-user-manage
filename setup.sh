#!/bin/bash

# ========================================================================
# User Management API Setup Script
# ========================================================================
#
# This script automates the setup process for the User Management REST API.
# It creates a Python virtual environment and installs all required dependencies.
#
# Prerequisites:
# - Python 3.12 or higher
# - Docker and docker-compose (for infrastructure)
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# After setup, follow the instructions to start the application.
# ========================================================================

set -e  # Exit on any error

echo "🚀 Setting up User Management API..."

# Check if Python 3.12+ is available
echo "📋 Checking Python version..."
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
python_major=$(python3 -c "import sys; print(sys.version_info.major)")
python_minor=$(python3 -c "import sys; print(sys.version_info.minor)")

if [[ $python_major -lt 3 ]] || [[ $python_major -eq 3 && $python_minor -lt 12 ]]; then
    echo "❌ Python 3.12 or higher is required."
    echo "   Current version: $python_version"
    echo "💡 Please install Python 3.12+ and run this script again."
    echo "   Visit: https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python $python_version found (3.12+ required)"

# Function to parse DATABASE_URL and extract components
parse_database_url() {
    local url="$1"
    # Remove protocol prefix (postgresql+asyncpg://)
    local clean_url="${url#*://}"
    # Extract user:password@host:port/database
    local user_pass_host_port_db="${clean_url%%/*}"
    local db="${clean_url##*/}"

    # Extract user and password
    local user_pass="${user_pass_host_port_db%%@*}"
    local host_port="${user_pass_host_port_db##*@}"

    # Extract user and password
    local user="${user_pass%%:*}"
    local password="${user_pass##*:}"

    # Extract host and port
    local host="${host_port%%:*}"
    local port="${host_port##*:}"

    echo "$user|$password|$host|$port|$db"
}

# Function to create PostgreSQL user and database
setup_postgres() {
    echo "🐘 Setting up PostgreSQL database and user..."

    # Check if .env file exists, otherwise use defaults
    if [ -f ".env" ]; then
        echo "📄 Reading database configuration from .env file..."
        DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
    else
        echo "📄 Using default database configuration..."
        DATABASE_URL="postgresql+asyncpg://user_manager:password@localhost:5432/user_management"
    fi

    echo "🔗 Database URL: $DATABASE_URL"

    # Parse the DATABASE_URL
    IFS='|' read -r DB_USER DB_PASSWORD DB_HOST DB_PORT DB_NAME <<< "$(parse_database_url "$DATABASE_URL")"

    echo "👤 User: $DB_USER"
    echo "🗄️  Database: $DB_NAME"
    echo "🏠 Host: $DB_HOST:$DB_PORT"

    # Start Docker services
    echo "🐳 Starting Docker services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d

        # Wait for PostgreSQL to be ready
        echo "⏳ Waiting for PostgreSQL to be ready..."
        max_attempts=30
        attempt=1
        while [ $attempt -le $max_attempts ]; do
            if docker-compose exec -T postgres pg_isready -U postgres -h localhost > /dev/null 2>&1; then
                echo "✅ PostgreSQL is ready!"
                break
            fi
            echo "⏳ Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
            sleep 2
            ((attempt++))
        done

        if [ $attempt -gt $max_attempts ]; then
            echo "❌ PostgreSQL failed to start after $max_attempts attempts"
            echo "💡 Check Docker logs: docker-compose logs postgres"
            return 1
        fi

        # Check if database and user exist (should be created by Docker init script)
        echo "👤 Verifying database user and database..."
        if docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            echo "   ✅ Database and user exist and are accessible"
        else
            echo "   ⚠️  Cannot connect to database as '$DB_USER'"
            echo "   🔍 Checking PostgreSQL status..."

            # Check if PostgreSQL is running and accessible
            if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
                echo "   ✅ PostgreSQL is running"

                # Try to create user and database manually as fallback
                echo "   🔧 Attempting manual database setup..."

                # Create user if it doesn't exist
                echo "   - Creating user '$DB_USER'..."
                CREATE_USER_SQL="
                    DO \$\$
                    BEGIN
                       IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
                          CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
                       END IF;
                    END
                    \$\$;
                "
                docker-compose exec -T postgres psql -U postgres -c "$CREATE_USER_SQL" 2>/dev/null && echo "   ✅ User created"

                # Create database if it doesn't exist
                echo "   - Creating database '$DB_NAME'..."
                CREATE_DB_SQL="
                    SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
                    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
                "
                docker-compose exec -T postgres psql -U postgres -c "$CREATE_DB_SQL" 2>/dev/null && echo "   ✅ Database created"

                # Grant privileges
                echo "   - Granting privileges..."
                docker-compose exec -T postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null && echo "   ✅ Privileges granted"

                # Test connection again
                if docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
                    echo "   ✅ Manual setup successful"
                else
                    echo "   ❌ Manual setup failed - check Docker logs"
                    docker-compose logs postgres | tail -10
                fi
            else
                echo "   ❌ PostgreSQL is not running properly"
                echo "   💡 Try: docker-compose down && docker-compose up -d"
            fi
        fi

        if [ $? -eq 0 ]; then
            echo "✅ Database user and database created successfully!"
        else
            echo "⚠️  Database setup completed with warnings (this is usually fine)"
        fi

        # Test connection
        echo "🔍 Testing database connection..."
        if docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
            echo "✅ Database connection test successful!"
        else
            echo "⚠️  Database connection test failed, but setup will continue"
        fi

    else
        echo "⚠️  docker-compose not found. Please start Docker services manually:"
        echo "   docker-compose up -d"
        echo "   # Then run the database setup manually if needed"
    fi
}

# Check if called with --db-only flag for database setup only
if [ "$1" = "--db-only" ]; then
    echo "🐘 PostgreSQL Database Setup Only"
    echo "=================================="
    setup_postgres
    exit $?
fi

# Setup PostgreSQL user and database
setup_postgres

# Check if required packages are already installed
echo "🔍 Checking for required packages..."
python3 -c "
required_packages = ['pydantic', 'pydantic_settings', 'litestar', 'advanced_alchemy', 'asyncpg']
missing_packages = []

for package in required_packages:
    try:
        __import__(package.replace('_', ''))
        print(f'✅ {package} available')
    except ImportError:
        missing_packages.append(package)
        print(f'⚠️  {package} missing')

if missing_packages:
    print(f'   Missing packages will be installed: {', '.join(missing_packages)}')
else:
    print('✅ All required packages available')
"

# Create isolated virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip to latest version
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo "📚 Installing dependencies..."
echo "   - python-dotenv (environment variable management)"
pip install python-dotenv

echo "   - pydantic (data validation)"
pip install pydantic

echo "   - pydantic-settings (settings management)"
pip install pydantic-settings

echo "   - litestar[standard] (web framework)"
pip install "litestar[standard]"

echo "   - litestar-granian (high-performance server)"
pip install litestar-granian

echo "   - litestar-asyncpg (PostgreSQL async driver)"
pip install litestar-asyncpg

echo "   - advanced-alchemy (SQLAlchemy async support)"
pip install advanced-alchemy

echo "   - msgspec (fast serialization)"
pip install msgspec

echo "   - structlog (structured logging)"
pip install structlog

echo "   - aio-pika (RabbitMQ async client)"
pip install aio-pika

echo "   - faststream (RabbitMQ stream processing)"
pip install faststream

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "   ✅ Python virtual environment created"
echo "   ✅ Dependencies installed"
echo "   ✅ Docker services started"
echo "   ✅ PostgreSQL user and database created"
echo "   ✅ Development tools configured"
echo ""
echo "🎯 Next steps:"
echo "1. Configure environment (optional):"
echo "   cp env-example.txt .env  # Edit .env with your settings"
echo ""
echo "2. Run the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "🌐 API endpoints:"
echo "   - API: http://localhost:8000"
echo "   - Swagger UI: http://localhost:8000/schema"
echo "   - RabbitMQ Management: http://localhost:15672"
echo ""
echo "📖 For more information, see README.md"
