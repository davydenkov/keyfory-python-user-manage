#!/usr/bin/env python3
"""
Application runner script.

Provides a convenient way to start the User Management API server
using Uvicorn ASGI server. It loads configuration from environment variables
and supports development features like auto-reload.

Requires Python 3.12+ for optimal performance and modern async features.

Usage:
    python run.py

Environment Variables:
    HOST: Server bind address (default: 0.0.0.0)
    PORT: Server port (default: 8000)
    DEBUG: Enable debug mode and auto-reload (default: true)
    LOG_LEVEL: Logging level (default: INFO)

The script will start the server and make the API available at:
http://localhost:8000

Swagger UI will be available at:
http://localhost:8000/schema
"""

import sys
import uvicorn
from app.config import get_settings

# Ensure we're running on Python 3.12+
if sys.version_info < (3, 12):
    print(
        f"❌ Python 3.12+ is required. Current version: {sys.version_info.major}.{sys.version_info.minor}",
        file=sys.stderr
    )
    sys.exit(1)


def main():
    """
    Main entry point for starting the application server.

    Loads configuration settings and starts Uvicorn with appropriate parameters
    for development or production use.
    """
    # Load application configuration
    settings = get_settings()

    # Check database connectivity before starting
    print("🔍 Checking database connectivity...")
    try:
        import asyncio
        from app.database.config import engine

        async def check_db():
            try:
                async with engine.begin() as conn:
                    await conn.execute("SELECT 1")
                return True
            except Exception as e:
                return str(e)

        result = asyncio.run(check_db())
        if result is True:
            print("✅ Database connection successful")
        else:
            print(f"⚠️  Database connection issue: {result}")

            # Check if it's a role/user issue and offer to set up automatically
            if "role" in result.lower() and "does not exist" in result.lower():
                print()
                print("🔧 It looks like the database user hasn't been created yet.")
                print("💡 Running automated database setup...")
                print()

                # Try to run database setup automatically
                try:
                    import subprocess
                    import sys
                    import os

                    # Get the directory of the current script
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    setup_script = os.path.join(script_dir, "setup.sh")

                    print("🐘 Setting up PostgreSQL database and user...")
                    result = subprocess.run([setup_script, "--db-only"], cwd=script_dir,
                                          capture_output=True, text=True)

                    if result.returncode == 0:
                        print("✅ Database setup completed successfully!")
                        print("🔄 Retrying database connection...")

                        # Try the database check again
                        result = asyncio.run(check_db())
                        if result is True:
                            print("✅ Database connection successful!")
                        else:
                            print(f"⚠️  Database still has issues: {result}")
                            print("Continuing anyway...")
                    else:
                        print("❌ Database setup failed:")
                        print(result.stderr)
                        print()
                        print("💡 Try running setup manually:")
                        print("   ./setup.sh")
                        print("Continuing anyway...")

                except Exception as setup_e:
                    print(f"❌ Could not run automated setup: {setup_e}")
                    print()
                    print("💡 Please run setup manually:")
                    print("   ./setup.sh")
                    print("Continuing anyway...")
            else:
                print("💡 Make sure Docker services are running:")
                print("   docker-compose up -d")
                print("   docker-compose ps")
                print()
                print("Continuing anyway (application will handle connection errors gracefully)...")
    except Exception as e:
        print(f"⚠️  Could not check database: {e}")
        print("Continuing anyway...")

    # Start Uvicorn ASGI server with application configuration
    uvicorn.run(
        "app.main:app",  # Application module and app instance
        host=settings.host,  # Bind address
        port=settings.port,  # Port number
        reload=settings.debug,  # Enable auto-reload in debug mode
        log_level=settings.log_level.lower(),  # Uvicorn log level
    )


if __name__ == "__main__":
    main()
