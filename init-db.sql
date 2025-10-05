-- Initialize database for greenhouse monitoring
-- This script runs automatically when the TimescaleDB container first starts

-- Create the greenhouse schema
CREATE SCHEMA IF NOT EXISTS greenhouse;

-- Grant permissions to the user
GRANT ALL PRIVILEGES ON SCHEMA greenhouse TO CURRENT_USER;
