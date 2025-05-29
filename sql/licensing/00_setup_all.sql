-- BIMigrator Licensing - Master Setup Script
-- This script runs all the necessary SQL scripts to set up the licensing system

-- Set the database name (modify as needed)
\set db_name 'bimigrator_db'

-- Connect to the database (or create it if it doesn't exist)
\c :db_name

-- Display information about the setup process
\echo 'Setting up BIMigrator licensing database components...'

-- Run the table creation script
\echo 'Creating licenses table...'
\i '01_create_tables.sql'

-- Run the function creation script
\echo 'Creating licensing functions...'
\i '02_create_functions.sql'

-- Run the user creation and permissions script
\echo 'Setting up database users and permissions...'
\i '03_create_users.sql'

-- Run the initial license provisioning script (optional)
\echo 'Creating initial license record...'
\i '04_initial_license.sql'

\echo 'BIMigrator licensing database setup completed successfully!'
