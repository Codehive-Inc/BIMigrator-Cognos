"""
Report migration orchestrators for Cognos to Power BI migration.

This module contains functions for migrating Cognos reports to Power BI.
"""

import os
import json
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from cognos_migrator.config import MigrationConfig, CognosConfig
from cognos_migrator.common.logging import configure_logging, log_info, log_warning, log_error, log_debug
from cognos_migrator.client import CognosClient, CognosAPIError
from cognos_migrator.common.websocket_client import logging_helper, set_task_info


def migrate_single_report(
    output_path: str,
    cognos_url: str,
    session_key: str,
    report_id: Optional[str] = None,
    report_file_path: Optional[str] = None,
    task_id: Optional[str] = None,
    auth_key: str = "IBM-BA-Authorization",
    settings: Optional[Dict[str, Any]] = None
) -> bool:
    """Orchestrates the migration of a single Cognos report, supporting both report ID and local file.
    
    Args:
        output_path (str): Path where migration output will be saved.
        cognos_url (str): The Cognos base URL.
        session_key (str): The session key for authentication.
        report_id (Optional[str]): The ID of the Cognos report to migrate.
        report_file_path (Optional[str]): The file path of the local report XML to migrate.
        task_id (Optional[str]): Optional task ID for tracking.
        auth_key (str): The authentication header key.
        
    Returns:
        bool: True if migration was successful, False otherwise.
        
    Raises:
        ValueError: If neither report_id nor report_file_path is provided.
        CognosAPIError: If the session is expired or invalid.
    """
    if not report_id and not report_file_path:
        raise ValueError("Either report_id or report_file_path must be provided.")

    configure_logging("cognos_report_migration")
    
    if task_id is None:
        task_id = str(uuid.uuid4())

    set_task_info(task_id, total_steps=8)
    
    if report_id:
        log_info(f"Testing connection to Cognos at {cognos_url}")
        if not CognosClient.test_connection_with_session(cognos_url, session_key):
            log_error("Session key is expired or invalid")
            raise CognosAPIError("Session key is expired or invalid")

    migration_config = MigrationConfig(
        output_directory=output_path,
        preserve_structure=True,
        include_metadata=True,
        generate_documentation=True,
        template_directory=str(Path(__file__).parent.parent / "templates"),
        llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
        llm_service_enabled=True
    )
    
    cognos_config = CognosConfig(
        base_url=cognos_url,
        auth_key=auth_key,
        auth_value=session_key,
        session_timeout=3600,
        max_retries=3,
        request_timeout=30
    )
    
    from ..migrator import CognosModuleMigratorExplicit
    
    migrator = CognosModuleMigratorExplicit(
        migration_config=migration_config,
        cognos_config=cognos_config,
        cognos_url=cognos_url,
        session_key=session_key,
        logger=logging.getLogger(__name__),
        settings=settings
    )
    
    log_info("Migrator initialized successfully")
    logging_helper(
        message="Migrator initialized successfully",
        progress=10,
        message_type="info"
    )
    
    try:
        if report_id:
            result = migrator.migrate_report(report_id, output_path)
        else:
            result = migrator.migrate_report_from_file(report_file_path, output_path)
        
        if result:
            log_info(f"Report migration completed successfully for: {report_id or report_file_path}")
            logging_helper(
                message=f"Report migration completed successfully for: {report_id or report_file_path}",
                progress=100,
                message_type="info"
            )
        else:
            log_error(f"Report migration failed for: {report_id or report_file_path}")
            logging_helper(
                message=f"Report migration failed for: {report_id or report_file_path}",
                progress=100,
                message_type="error"
            )
        return result
        
    except Exception as e:
        log_error(f"Error during report migration: {str(e)}", exception=e)
        logging_helper(
            message=f"Error during report migration: {str(e)}",
            progress=100,
            message_type="error"
        )
        return False


def migrate_single_report_with_explicit_session(report_id: str,
                                                output_path: str,
                                                cognos_url: str, session_key: str,
                                                task_id: Optional[str] = None,
                                                auth_key: str = "IBM-BA-Authorization",
                                                settings: Optional[Dict[str, Any]] = None) -> bool:
    """DEPRECATED: Use migrate_single_report instead.
    Migrate a single Cognos report with explicit session credentials.
    
    This function is kept for backward compatibility and will be removed in a future version.
    
    Args:
        report_id: ID of the Cognos report to migrate
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        
    Returns:
        bool: True if migration was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    log_warning("The function 'migrate_single_report_with_explicit_session' is deprecated. Use 'migrate_single_report' instead.")
    return migrate_single_report(
        output_path=output_path,
        cognos_url=cognos_url,
        session_key=session_key,
        report_id=report_id,
        task_id=task_id,
        auth_key=auth_key,
        settings=settings
    )
