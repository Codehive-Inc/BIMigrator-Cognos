# BIMigrator Licensing Database Scripts

This directory contains SQL scripts for setting up the PostgreSQL database components required for the BIMigrator licensing system.

## Overview

The licensing system uses PostgreSQL to:
- Store license state (migrations used, expiry date)
- Enforce license constraints through stored procedures
- Provide secure access with restricted permissions

## Script Files

- **00_setup_all.sql**: Master script that runs all other scripts in the correct order
- **01_create_tables.sql**: Creates the `licenses` table to store license information
- **02_create_functions.sql**: Creates stored functions for license validation and status checking
- **03_create_users.sql**: Sets up database users with appropriate permissions
- **04_initial_license.sql**: Inserts an initial license record for testing/setup

## Usage Instructions

### Prerequisites

- PostgreSQL 12+ installed and running
- Database superuser access (for initial setup)

### Setup Options

#### Option 1: Run All Scripts at Once

```bash
# Connect to PostgreSQL and run the master script
psql -U postgres -d bimigrator_db -f 00_setup_all.sql
```

#### Option 2: Run Scripts Individually

```bash
# Create the database (if it doesn't exist)
psql -U postgres -c "CREATE DATABASE bimigrator_db;"

# Run each script in order
psql -U postgres -d bimigrator_db -f 01_create_tables.sql
psql -U postgres -d bimigrator_db -f 02_create_functions.sql
psql -U postgres -d bimigrator_db -f 03_create_users.sql
psql -U postgres -d bimigrator_db -f 04_initial_license.sql
```

### Important Notes

1. **Security**: 
   - Change the default passwords in `03_create_users.sql` before running in production
   - Consider using environment variables for passwords instead of hardcoding them

2. **License Management**:
   - The initial license is set to expire 1 year from creation with 100 migrations
   - Use the `license_admin` user to manage licenses (add, modify, delete)
   - The application should connect using the `app_user` credentials

3. **Database Connection**:
   - The application should use the following connection parameters:
     - User: `app_user`
     - Password: (as set in the script)
     - Database: `bimigrator_db`
     - Host: (your PostgreSQL server)
     - Port: (your PostgreSQL port, typically 5432)

4. **Testing License Functionality**:
   - You can test the license validation function with:
     ```sql
     SELECT increment_migration_count(1);  -- Should return TRUE if license is valid
     ```
   - You can check license status with:
     ```sql
     SELECT * FROM get_license_status(1);  -- Returns license status information
     ```

## License Schema

The `licenses` table has the following structure:

| Column           | Type                     | Description                                |
|------------------|---------------------------|--------------------------------------------|
| id               | SERIAL PRIMARY KEY        | Unique identifier for the license          |
| license_key      | VARCHAR(255) UNIQUE      | Unique license key string                  |
| activated_at     | TIMESTAMP WITH TIME ZONE | When the license became active             |
| expires_at       | TIMESTAMP WITH TIME ZONE | When the license expires                   |
| max_migrations   | INTEGER                  | Maximum allowed migrations                 |
| migrations_used  | INTEGER                  | Counter for migrations performed           |
| created_at       | TIMESTAMP WITH TIME ZONE | When the license record was created        |
| updated_at       | TIMESTAMP WITH TIME ZONE | When the license record was last updated   |
| client_name      | VARCHAR(255)             | Name of the client                         |
| license_type     | VARCHAR(50)              | Type of license (trial, standard, etc.)    |
