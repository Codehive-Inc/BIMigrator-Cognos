-- BIMigrator Licensing - Initial License Provisioning Script
-- This script inserts an initial license record for testing or initial setup

-- Insert a sample license record
-- Note: In a production environment, these values should be configured appropriately
INSERT INTO licenses (
    license_key,
    activated_at,
    expires_at,
    max_migrations,
    migrations_used,
    client_name,
    license_type
) VALUES (
    'BIMIG-INIT-LICENSE-2025',                -- license_key: Replace with actual license key
    NOW(),                                     -- activated_at: Current timestamp
    NOW() + INTERVAL '1 year',                -- expires_at: 1 year from now
    100,                                       -- max_migrations: 100 migrations allowed
    0,                                         -- migrations_used: Starting with 0
    'Initial Client',                          -- client_name: Replace with actual client name
    'standard'                                 -- license_type: standard license
)
ON CONFLICT (license_key) DO NOTHING;         -- Skip if license key already exists

-- Output the inserted license
SELECT 
    id,
    license_key,
    activated_at,
    expires_at,
    max_migrations,
    migrations_used,
    client_name,
    license_type
FROM licenses 
WHERE license_key = 'BIMIG-INIT-LICENSE-2025';
