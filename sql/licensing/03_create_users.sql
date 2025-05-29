-- BIMigrator Licensing - User Creation and Permissions Script
-- This script creates the application database user with restricted permissions

-- Create application user
-- Note: In a production environment, you would use a secure password
-- The password should be replaced with a secure value or configured via environment variables
DO $$
BEGIN
    -- Check if the user already exists
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE USER app_user WITH PASSWORD 'change_me_in_production';
        RAISE NOTICE 'User app_user created';
    ELSE
        RAISE NOTICE 'User app_user already exists';
    END IF;
END
$$;

-- Grant connect permission on the database
-- Note: Replace 'bimigrator_db' with your actual database name if different
GRANT CONNECT ON DATABASE bimigrator_db TO app_user;

-- Grant schema usage permission
GRANT USAGE ON SCHEMA public TO app_user;

-- Grant SELECT permission on the licenses table to app_user
GRANT SELECT ON TABLE licenses TO app_user;

-- CRITICAL: Explicitly REVOKE write permissions on the licenses table from app_user
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLE licenses FROM app_user;

-- Grant EXECUTE permission on the increment_migration_count function to app_user
GRANT EXECUTE ON FUNCTION increment_migration_count(INTEGER) TO app_user;

-- Grant EXECUTE permission on the get_license_status function to app_user
GRANT EXECUTE ON FUNCTION get_license_status(INTEGER) TO app_user;

-- Grant permissions on the licenses_id_seq sequence (needed for the SELECT on licenses)
GRANT USAGE, SELECT ON SEQUENCE licenses_id_seq TO app_user;

-- Add comments for documentation
COMMENT ON ROLE app_user IS 'Restricted database user for the BIMigrator application with limited permissions on license data';

-- Create an admin user for license management (optional)
-- This user will have full access to the licenses table for administration purposes
DO $$
BEGIN
    -- Check if the user already exists
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'license_admin') THEN
        CREATE USER license_admin WITH PASSWORD 'change_me_in_production';
        RAISE NOTICE 'User license_admin created';
    ELSE
        RAISE NOTICE 'User license_admin already exists';
    END IF;
END
$$;

-- Grant connect permission on the database to license_admin
GRANT CONNECT ON DATABASE bimigrator_db TO license_admin;

-- Grant schema usage permission to license_admin
GRANT USAGE ON SCHEMA public TO license_admin;

-- Grant full permissions on the licenses table to license_admin
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE licenses TO license_admin;

-- Grant usage on the sequence to license_admin
GRANT USAGE, SELECT ON SEQUENCE licenses_id_seq TO license_admin;

-- Add comments for documentation
COMMENT ON ROLE license_admin IS 'Administrative user for managing licenses in the BIMigrator application';
