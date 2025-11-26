-- ============================================================================
-- MP4toText Backend - Database Initialization Script
-- ============================================================================
-- This script runs automatically when PostgreSQL container starts
-- It creates the database and user if they don't exist
-- ============================================================================

-- Create database (if not exists)
SELECT 'CREATE DATABASE mp4totext'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mp4totext')\gexec

-- Connect to mp4totext database
\c mp4totext

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types if needed
DO $$ BEGIN
    CREATE TYPE transcription_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE mp4totext TO postgres;

-- Log success
\echo '✅ Database initialization completed'
\echo '📝 Extensions installed: uuid-ossp, pg_trgm'
\echo '🎯 Custom types created: transcription_status'
