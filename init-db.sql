-- ========================================================================
-- PostgreSQL Database Initialization Script
-- ========================================================================
--
-- This script runs automatically when the PostgreSQL container starts
-- for the first time. It sets up the database and user permissions
-- required by the User Management API.
--
-- Note: POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are already
-- created by PostgreSQL automatically from environment variables.
--
-- ========================================================================

-- Ensure the application user exists
-- Note: POSTGRES_USER environment variable should create this user automatically,
-- but we include this as a safety measure in case of timing issues or configuration problems
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_manager') THEN
      CREATE ROLE "user_manager" LOGIN PASSWORD 'password';
      RAISE NOTICE 'Created user "user_manager" via init script';
   ELSE
      RAISE NOTICE 'User "user_manager" already exists (created by POSTGRES_USER)';
   END IF;
END
$$;

-- Create the application database if it doesn't exist
-- (This is redundant with POSTGRES_DB but ensures consistency)
SELECT 'CREATE DATABASE user_management OWNER "user_manager"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user_management')\gexec

-- Grant all privileges on the database to the application user
-- (This is safe to run even if already granted)
GRANT ALL PRIVILEGES ON DATABASE user_management TO "user_manager";

-- Create additional databases if needed for future features
-- (Uncomment and modify as needed)
-- SELECT 'CREATE DATABASE user_management_test OWNER "user_manager"'
-- WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user_management_test')\gexec
-- GRANT ALL PRIVILEGES ON DATABASE user_management_test TO "user_manager";

-- ========================================================================
-- Additional database setup can be added here
-- ========================================================================
--
-- Examples:
-- - Create schemas: CREATE SCHEMA IF NOT EXISTS app_schema;
-- - Create roles: CREATE ROLE readonly_user LOGIN PASSWORD 'readonly_pass';
-- - Grant permissions: GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
--
-- ========================================================================
