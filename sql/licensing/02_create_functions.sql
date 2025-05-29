-- BIMigrator Licensing - Function Creation Script
-- This script creates the stored function for license validation and migration counting

-- Create function to increment migration count and validate license
CREATE OR REPLACE FUNCTION increment_migration_count(p_license_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_activated_at TIMESTAMP WITH TIME ZONE;
    v_expires_at TIMESTAMP WITH TIME ZONE;
    v_max_migrations INTEGER;
    v_migrations_used INTEGER;
    v_license_valid BOOLEAN;
BEGIN
    -- Start a transaction
    BEGIN
        -- Select the license row for the given ID, locking it for update
        -- This prevents concurrent modifications during the check and update
        SELECT 
            activated_at, 
            expires_at, 
            max_migrations, 
            migrations_used 
        INTO 
            v_activated_at,
            v_expires_at,
            v_max_migrations,
            v_migrations_used
        FROM licenses 
        WHERE id = p_license_id 
        FOR UPDATE;
        
        -- Check if license record exists
        IF NOT FOUND THEN
            RAISE NOTICE 'License with ID % not found', p_license_id;
            RETURN FALSE;
        END IF;
        
        -- Check license validity:
        -- 1. Is current timestamp less than or equal to expires_at?
        -- 2. Is migrations_used strictly less than max_migrations?
        v_license_valid := (
            current_timestamp <= v_expires_at AND 
            v_migrations_used < v_max_migrations
        );
        
        IF v_license_valid THEN
            -- License is valid, increment the migrations_used count
            UPDATE licenses 
            SET 
                migrations_used = migrations_used + 1, 
                updated_at = NOW() 
            WHERE id = p_license_id;
            
            RAISE NOTICE 'License check passed. Migration count incremented to %', v_migrations_used + 1;
            RETURN TRUE;
        ELSE
            -- License is invalid (expired or limit reached)
            IF current_timestamp > v_expires_at THEN
                RAISE NOTICE 'License with ID % has expired (Expiry: %)', p_license_id, v_expires_at;
            ELSE
                RAISE NOTICE 'License with ID % has reached migration limit (Used: %, Max: %)', 
                    p_license_id, v_migrations_used, v_max_migrations;
            END IF;
            
            RETURN FALSE;
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Error in increment_migration_count: %', SQLERRM;
            RETURN FALSE;
    END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comment to function for documentation
COMMENT ON FUNCTION increment_migration_count(INTEGER) IS 'Validates license and increments migration count if license is valid. Returns TRUE if successful, FALSE otherwise.';

-- Create a function to get license status
CREATE OR REPLACE FUNCTION get_license_status(p_license_id INTEGER)
RETURNS TABLE (
    is_active BOOLEAN,
    expires_at TIMESTAMP WITH TIME ZONE,
    max_migrations INTEGER,
    migrations_used INTEGER,
    migrations_remaining INTEGER,
    status_message TEXT
) AS $$
DECLARE
    v_license licenses%ROWTYPE;
BEGIN
    -- Get the license record
    SELECT * INTO v_license FROM licenses WHERE id = p_license_id;
    
    -- Check if license record exists
    IF NOT FOUND THEN
        is_active := FALSE;
        expires_at := NULL;
        max_migrations := 0;
        migrations_used := 0;
        migrations_remaining := 0;
        status_message := 'License not found';
        RETURN NEXT;
        RETURN;
    END IF;
    
    -- Calculate license status
    is_active := current_timestamp <= v_license.expires_at;
    expires_at := v_license.expires_at;
    max_migrations := v_license.max_migrations;
    migrations_used := v_license.migrations_used;
    migrations_remaining := GREATEST(0, v_license.max_migrations - v_license.migrations_used);
    
    -- Determine status message
    IF NOT is_active THEN
        status_message := 'License expired';
    ELSIF migrations_remaining = 0 THEN
        status_message := 'Migration limit reached';
    ELSE
        status_message := 'License is active';
    END IF;
    
    RETURN NEXT;
    RETURN;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comment to function for documentation
COMMENT ON FUNCTION get_license_status(INTEGER) IS 'Returns the current status of a license including activity state, expiry, and migration counts.';
