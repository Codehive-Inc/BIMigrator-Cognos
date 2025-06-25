"""Cognos to BI Migrator

A Python package for migrating Cognos Analytics reports to Power BI format.
Provides .env-independent migration functions with explicit session management.

Main Functions:
    test_cognos_connection: Test Cognos connectivity with session key
    migrate_module_with_explicit_session: Migrate a complete Cognos module
    migrate_single_report_with_explicit_session: Migrate a single report
    post_process_module_with_explicit_session: Post-process migrated modules

Example:
    import cognos_migrator
    
    # Test connection
    is_connected = cognos_migrator.test_cognos_connection(
        cognos_url="http://your-cognos-server:9300/api/v1",
        session_key="your_session_key"
    )
    
    # Migrate module
    success = cognos_migrator.migrate_module_with_explicit_session(
        module_id="your_module_id",
        output_path="./output",
        cognos_url="http://your-cognos-server:9300/api/v1",
        session_key="your_session_key",
        folder_id="reports_folder_id"
    )
"""

__version__ = "1.0.0"
__author__ = "Cognos Migration Team"

# Import only essential functions for external integration
from .explicit_session_migrator import (
    test_cognos_connection,
    migrate_module_with_explicit_session,
    migrate_single_report_with_explicit_session,
    post_process_module_with_explicit_session
)

# Import key exception classes for error handling
from .client import CognosAPIError

# Clean public API - only expose what integrators need
__all__ = [
    # Version info
    '__version__',
    
    # Core migration functions
    'test_cognos_connection',
    'migrate_module_with_explicit_session', 
    'migrate_single_report_with_explicit_session',
    'post_process_module_with_explicit_session',
    
    # Exception handling
    'CognosAPIError'
]