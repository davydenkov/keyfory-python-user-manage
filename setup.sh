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

# Check if Python 3.12 is available
echo "📋 Checking Python version..."
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is required but not found."
    echo "💡 Please install Python 3.12 and run this script again."
    echo "   Visit: https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python 3.12 found"

# Create isolated virtual environment
echo "📦 Creating virtual environment..."
python3.12 -m venv venv

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
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Start infrastructure services:"
echo "   docker-compose up -d"
echo ""
echo "2. Configure environment (optional):"
echo "   cp .env.example .env  # Edit .env with your settings"
echo ""
echo "3. Run the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "🌐 API endpoints:"
echo "   - API: http://localhost:8000"
echo "   - Swagger UI: http://localhost:8000/schema"
echo "   - RabbitMQ Management: http://localhost:15672"
echo ""
echo "📖 For more information, see README.md"
