-- BIMigrator Licensing - Table Creation Script
-- This script creates the necessary table for license management

-- Create licenses table
CREATE TABLE IF NOT EXISTS licenses (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(255) UNIQUE,
    activated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    max_migrations INTEGER NOT NULL,
    migrations_used INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    client_name VARCHAR(255),
    license_type VARCHAR(50)
);

-- Add comments to table and columns for documentation
COMMENT ON TABLE licenses IS 'Stores license information for the BIMigrator application';
COMMENT ON COLUMN licenses.id IS 'Primary key for the license record';
COMMENT ON COLUMN licenses.license_key IS 'Unique identifier for the license';
COMMENT ON COLUMN licenses.activated_at IS 'Timestamp when the license became active';
COMMENT ON COLUMN licenses.expires_at IS 'Timestamp when the license expires';
COMMENT ON COLUMN licenses.max_migrations IS 'Maximum number of migrations allowed under this license';
COMMENT ON COLUMN licenses.migrations_used IS 'Counter for migrations performed under this license';
COMMENT ON COLUMN licenses.created_at IS 'Timestamp when the license record was created';
COMMENT ON COLUMN licenses.updated_at IS 'Timestamp when the license record was last updated';
COMMENT ON COLUMN licenses.client_name IS 'Name of the client this license belongs to';
COMMENT ON COLUMN licenses.license_type IS 'Type of license (e.g., trial, standard, enterprise)';

-- Create index on license_key for faster lookups
CREATE INDEX IF NOT EXISTS idx_licenses_license_key ON licenses(license_key);
