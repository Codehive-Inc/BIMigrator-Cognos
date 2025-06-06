Okay, let's prepare a detailed requirements document focused specifically on implementing the PostgreSQL database-based licensing mechanism and its integration with the Backend SDK, Backend Django, and Frontend components within your chosen Option 1 containerized deployment architecture.

This document assumes the core application logic (TWB parsing, M-code generation, basic Django views/APIs, basic Frontend structure) is already in place.

---

**Project: [Your Product Name] - Licensing Feature Implementation Requirements**

**Document Version:** 1.0
**Date:** 2023-10-27

**1. Overview**

This document specifies the requirements for implementing a license enforcement mechanism within the [Your Product Name] application suite. The licensing will be based on two primary constraints: a maximum number of migrations allowed and an expiry date. The license state will be stored securely in the PostgreSQL database, and the application will enforce these limits during the migration process and provide visibility into the license status via the user interface.

**2. Scope**

The scope of this document includes:
*   Designing and implementing the necessary database schema and logic in PostgreSQL.
*   Modifying the Backend Python SDK to perform license checks and update the license state by interacting with the database.
*   Modifying the Backend Django application to handle license-related errors from the SDK and expose license status via an API endpoint.
*   Developing or modifying the Frontend (Typescript/Vite) to display license status and handle license-related errors.
*   Defining the necessary database user permissions.
*   Outlining the process for initial license provisioning.

This document assumes the containerized deployment infrastructure (Dockerfiles, `docker-compose.yml`, basic environment variable handling for DB connection) specified in the previous deployment requirements is the target environment. It also assumes the core migration functionality within the SDK is functional.

**3. Goals**

*   Implement a secure and reliable method for storing and updating license state (migrations used, expiry date).
*   Enforce the license constraints (migration count limit, expiry date) during every migration attempt.
*   Prevent unauthorized modification of the license state via direct database access using the application's credentials.
*   Provide clear feedback to the user via the Frontend when a migration is blocked due to licensing.
*   Provide visibility into the current license status (migrations used/remaining, expiry date) via the Frontend.
*   Ensure license updates are atomic and safe under potential concurrent conditions (if applicable).

**4. Key Concepts**

*   **License State:** Stored in a dedicated table (`licenses`) in the PostgreSQL database.
*   **License Logic:** Encapsulated within a PostgreSQL stored function (`increment_migration_count`).
*   **Restricted Database User:** The application connects to the database using a user (`app_user`) with limited permissions, specifically preventing direct write access to the `licenses` table.
*   **SDK Enforcement:** The Backend SDK calls the stored function before proceeding with a migration.
*   **API Visibility:** Django provides an API endpoint for the Frontend to read the license status.
*   **Frontend Display:** The Frontend polls the API and displays the license status to the user.

**5. Detailed Requirements**

**5.1. Database (PostgreSQL) Implementation**

*   **Database Initialization Script:** Modify the existing database initialization script(s) (SQL files run during installation) to include the following:
    *   **Licenses Table Creation:** Create a table named `licenses`. Recommended columns:
        *   `id` SERIAL PRIMARY KEY (or UUID)
        *   `license_key` VARCHAR(255) UNIQUE (Optional, if you use license keys)
        *   `activated_at` TIMESTAMP WITH TIME ZONE NOT NULL (Timestamp when license became active)
        *   `expires_at` TIMESTAMP WITH TIME ZONE NOT NULL (Timestamp when license expires)
        *   `max_migrations` INTEGER NOT NULL (Maximum allowed migration count)
        *   `migrations_used` INTEGER NOT NULL DEFAULT 0 (Counter for migrations performed)
        *   `created_at` TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        *   `updated_at` TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        *   *(Add other fields like client name, license type, etc., as needed)*
    *   **Application Database User:** Ensure the script creates a dedicated PostgreSQL user (e.g., `app_user`) that your application services (SDK, Django) will use to connect.
    *   **Permission Grants:**
        *   Grant `CONNECT` on the database to `app_user`.
        *   Grant `SELECT` permission on the `licenses` table to `app_user`.
        *   **CRITICAL:** Explicitly `REVOKE` or do not grant `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` permissions on the `licenses` table to `app_user`.
        *   Grant necessary permissions on other tables (e.g., logs, user accounts) to `app_user`.
    *   **Stored Function Creation:** Create a PostgreSQL stored function named `increment_migration_count`.
        *   Signature: `increment_migration_count(p_license_id INTEGER) RETURNS BOOLEAN` (assuming `id` is an INTEGER; adjust type if using UUID).
        *   Logic:
            1.  Start a transaction (`BEGIN;`).
            2.  Select the license row for `p_license_id`, locking it for update (`SELECT activated_at, expires_at, max_migrations, migrations_used FROM licenses WHERE id = p_license_id FOR UPDATE;`). Handle cases where `p_license_id` doesn't exist (return FALSE or raise error).
            3.  Check license validity:
                *   Is `current_timestamp` less than or equal to `expires_at`?
                *   Is `migrations_used` strictly less than `max_migrations`?
            4.  If **both** checks are true:
                *   Increment the `migrations_used` count: `UPDATE licenses SET migrations_used = migrations_used + 1, updated_at = NOW() WHERE id = p_license_id;`.
                *   Commit the transaction (`COMMIT;`).
                *   Return `TRUE`.
            5.  If **either** check is false:
                *   Rollback the transaction (`ROLLBACK;`).
                *   Return `FALSE`.
        *   Function Properties: Define as `SECURITY DEFINER` if the user executing the function needs higher privileges than `app_user` to perform the update (common practice), and ensure the function owner has the necessary `UPDATE` permission on `licenses`.
    *   **Execute Permission:** Grant `EXECUTE` permission on the `increment_migration_count` function ONLY to the `app_user`.

**5.2. Backend Python SDK Implementation**

*   **Database Connection:** Ensure the SDK component can connect to the PostgreSQL database using the `app_user` credentials provided via environment variables (like `DATABASE_URL` or separate `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). Use a robust library like `psycopg2`.
*   **License Check and Increment:**
    *   Identify the function or method in the SDK that is the entry point for processing a single TWB file migration.
    *   At the **very beginning** of this function, *before* any resource-intensive work or external calls (like `pbi-tools` or LLM), add the license check logic.
    *   Call the `increment_migration_count` stored function in the database. Assume a single license row for now (e.g., hardcode `p_license_id = 1`, or make the license ID configurable).
    *   Example Python code snippet (conceptual):
        ```python
        import psycopg2
        # ... db connection setup ...

        def perform_migration(twb_file_path, license_id=1):
            db_conn = get_db_connection() # Your function to get a DB connection
            cursor = db_conn.cursor()

            try:
                # Call the stored function
                cursor.execute("SELECT increment_migration_count(%s);", (license_id,))
                can_proceed = cursor.fetchone()[0] # Get the boolean result

                if not can_proceed:
                    # License check failed (limit reached or expired)
                    db_conn.rollback() # Ensure any implicit transaction is rolled back
                    # Raise a specific exception that Django can catch
                    raise LicenseError("Migration failed: License limit reached or expired.")

                # If we are here, the check passed and count was incremented in DB
                db_conn.commit() # Commit the successful increment

                # --- Proceed with the actual migration logic ---
                print(f"License check passed. Starting migration for {twb_file_path}")
                # ... TWB parsing, pbi-tools calls, LLM calls, etc. ...
                print(f"Migration for {twb_file_path} completed successfully.")
                # --- End of actual migration logic ---

            except LicenseError as e:
                print(f"Migration aborted due to licensing: {e}")
                raise e # Re-raise the exception for Django to catch
            except Exception as e:
                # Handle other potential errors (DB connection, migration errors)
                print(f"Migration failed due to an unexpected error: {e}")
                db_conn.rollback() # Ensure transaction is rolled back on *any* error
                raise e # Re-raise for Django
            finally:
                cursor.close()
                db_conn.close()

        class LicenseError(Exception):
             """Custom exception for licensing failures."""
             pass
        ```
*   **Error Handling:** Define a custom exception class (e.g., `LicenseError`) specifically for licensing failures. The SDK function should raise this exception if `increment_migration_count` returns FALSE. This allows Django to specifically catch licensing issues.

**5.3. Backend Django Implementation**

*   **License Status API Endpoint:** Create a new API endpoint (e.g., `GET /api/license/status/`) that:
    *   Connects to the PostgreSQL database using the `app_user` credentials.
    *   Queries the `licenses` table to retrieve the current state (`activated_at`, `expires_at`, `max_migrations`, `migrations_used`). Assume license ID 1 or make it configurable.
    *   Calculates remaining migrations (`max_migrations - migrations_used`).
    *   Calculates days remaining until expiry.
    *   Returns the license status data as a JSON response. Example structure:
        ```json
        {
            "isActive": true, // Based on expiry_at
            "expiresAt": "YYYY-MM-DDTHH:MM:SSZ",
            "maxMigrations": 100,
            "migrationsUsed": 42,
            "migrationsRemaining": 58,
            "statusMessage": "License is active." // or "License expired", "Migration limit reached"
        }
        ```
        *Note: The `isActive` and `statusMessage` can be determined server-side based on the fetched data.*
    *   Requires `SELECT` permission on the `licenses` table for the `app_user`. This endpoint does *not* need to call the stored function.
*   **Migration Trigger API Endpoint:** Modify the existing API endpoint(s) that initiate a migration (the ones that call the Backend SDK logic) to:
    *   Call the SDK function (`perform_migration`).
    *   Include a `try...except` block to catch the specific `LicenseError` raised by the SDK.
    *   If `LicenseError` is caught:
        *   Return an appropriate HTTP response status code (e.g., `402 Payment Required` or `403 Forbidden`).
        *   Include a JSON error payload in the response body containing a user-friendly message (e.g., `"error": "License limit reached or expired."`).
    *   If other exceptions occur, handle them as existing API error handling does (e.g., 500 Internal Server Error).
    *   If the SDK function completes successfully, return a success response (e.g., 200 OK).

**5.4. Frontend (Typescript/Vite) Implementation**

*   **License Status Display:**
    *   Create a dedicated UI component (e.g., a dashboard widget, a "Settings" or "About" page section) to display the license status.
    *   This component should call the new Django API endpoint (`GET /api/license/status/`).
    *   Display the data received in the JSON response: "Migrations Used", "Migrations Remaining", "Expiry Date", "Status".
    *   Implement logic to handle API call errors or loading states.
    *   Consider implementing polling (e.g., every 5-10 minutes) or manual refresh to keep the status display updated.
*   **Migration Error Handling:**
    *   Modify the UI workflow for initiating a migration (e.g., the button click handler, the form submission).
    *   After calling the Django API to start a migration, check the HTTP response status code.
    *   If a `402` or `403` (or whatever code is chosen) is received, read the error message from the JSON response body.
    *   Display this error message to the user in a clear and prominent way (e.g., an alert box, a dedicated error message area).

**5.5. Initial License Provisioning**

*   **Requirement:** Define and implement a method for the client/administrator to insert the initial license row(s) into the `licenses` table. The options are:
    *   **Option A (Recommended):** Create an administrative page or tool (potentially within Django Admin if using it) that allows inputting the license details (`activated_at`, `expires_at`, `max_migrations`) and inserting the row using a database connection with sufficient privileges (NOT the `app_user`).
    *   **Option B:** Provide a separate, simple command-line Python script (or PowerShell script) that connects to the database (requiring higher privileges temporarily) and inserts the initial license row. This script should be run once after installation.
    *   **Option C:** Provide SQL `INSERT` statements as part of the installation documentation for client IT to run manually using a privileged database user.
*   The chosen method must securely handle the initial privileged database credentials required to bypass the `app_user` restrictions for this one-time setup.

**5.6. Error Handling & Logging**

*   Ensure appropriate logging is added in the SDK and Django code for successful license checks, failed license checks (including the reason - limit/expiry), and license status API calls.
*   Ensure the database logging (configured in the deployment) captures calls to the `increment_migration_count` function and any failed attempts to directly update the `licenses` table.

**6. Implementation Details / Considerations**

*   Use database transactions correctly in the SDK when calling the stored function. The logic is designed such that the stored function handles the transaction internally, so the SDK primarily needs to call the function and then commit/rollback its *own* transaction if it was already in one, or just handle connection/cursor management.
*   Ensure time zones are handled correctly when comparing `current_timestamp` with `expires_at`. Use `TIMESTAMP WITH TIME ZONE` in PostgreSQL and ensure your application/database connection is configured correctly for time zones.
*   Make license limits and expiry duration configurable (via `.env` variables) rather than hardcoded in application logic (though limits can be hardcoded *into the specific license row* in the database).

**7. Testing Requirements**

*   Verify database setup script runs correctly, creating the table, function, user, and permissions.
*   Test inserting the initial license row using the chosen provisioning method.
*   Test `GET /api/license/status/` endpoint and verify it returns correct license data.
*   Test migration initiation:
    *   With no license row present (should fail).
    *   With a valid license (should succeed and increment count).
    *   After reaching `max_migrations` (should fail with license error).
    *   After the `expires_at` date has passed (should fail with license error).
    *   Test concurrent migration attempts if applicable (verify licensing prevents exceeding the limit correctly due to the stored function's transaction/locking).
*   Verify that licensing errors from the SDK are caught and propagated correctly to the Frontend via the Django API.
*   Verify the Frontend displays license status accurately and shows licensing errors correctly.
*   Test updating license data (e.g., increasing limit or extending expiry) via the provisioning method and verify changes are reflected.
*   Attempt to update the `licenses` table directly using the `app_user` credentials via a separate DB tool – this should be denied.
*   Attempt to call the `increment_migration_count` function using the `app_user` credentials – this should succeed if checks pass.

**8. Deliverables**

*   Updated database initialization script(s) (SQL files) including table, function, user, and permissions.
*   SQL file(s) containing the source code for the `increment_migration_count` stored function.
*   Code modifications in the Backend Python SDK (`.py` files) for license checking and calling the stored function.
*   Code modifications in the Backend Django app (`.py` files) for the status API endpoint and error handling in the migration trigger endpoint.
*   New/modified code in the Frontend (Typescript/Vite) for the license status UI component and error handling.
*   Implementation of the chosen initial license provisioning method (admin code, separate script, documented SQL).
*   Updates to `.env.template` for any new configuration related to licensing (e.g., initial license details if using script method).
*   Updated documentation covering license provisioning, license status display, and error messages.

**9. Assumptions**

*   Core application components (SDK, Django, Frontend) are developed and their basic interaction flow for triggering migrations is established.
*   A working PostgreSQL instance is available (via Docker container).
*   Basic database connectivity is configured for the application containers (via environment variables).
*   Error handling and logging mechanisms are already partially in place in the application.

**10. Open Questions / Dependencies**

*   What specific error code/payload should Django return for licensing failures?
*   What is the desired refresh rate for the license status display in the Frontend?
*   Confirm the preferred method for initial license provisioning (Admin UI, script, manual SQL).
*   Confirm if any other license constraints are needed (e.g., licensed features, specific client identifiers).

---

This document provides a detailed plan for the developer to implement the requested licensing feature, covering all necessary layers from the database to the user interface.