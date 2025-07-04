"""
Report migration orchestrators for Cognos to Power BI migration.

This module contains functions for migrating Cognos reports to Power BI.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from cognos_migrator.config import MigrationConfig, CognosConfig
from cognos_migrator.common.logging import configure_logging, log_info, log_warning, log_error, log_debug
from cognos_migrator.client import CognosClient, CognosAPIError
from cognos_migrator.common.websocket_client import logging_helper, set_task_info


def migrate_single_report_with_explicit_session(report_id: str,
                                                output_path: str,
                                                cognos_url: str, session_key: str,
                                                task_id: Optional[str] = None,
                                                auth_key: str = "IBM-BA-Authorization") -> bool:
    """Migrate a single Cognos report with explicit session credentials
    
    This function does not use environment variables and will raise an exception
    if the session key is expired. Adapted from main.py migrate_single_report_with_session_key.
    
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
    # Configure logging for this module
    configure_logging("cognos_report_migration")
    
    # Generate task_id if not provided
    if task_id is None:
        task_id = f"report_migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with task ID and total steps (8 steps in the report migration process)
    set_task_info(task_id, total_steps=8)
    
    # First verify the session is valid
    log_info(f"Testing connection to Cognos at {cognos_url}")
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        log_error("Session key is expired or invalid")
        raise CognosAPIError("Session key is expired or invalid")
    
    # Create migration config with explicit values
    migration_config = MigrationConfig(
        output_directory=output_path,
        preserve_structure=True,
        include_metadata=True,
        generate_documentation=True,
        template_directory=str(Path(__file__).parent.parent / "templates"),  # Use existing templates directory
        llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),  # Enable DAX service
        llm_service_enabled=True
    )
    
    # Create Cognos config with explicit values
    cognos_config = CognosConfig(
        base_url=cognos_url,
        auth_key=auth_key,
        auth_value=session_key,
        session_timeout=3600,
        max_retries=3,
        request_timeout=30
    )
    
    # Create a minimal migrator without using environment variables
    logger = logging.getLogger(__name__)
    
    log_info(f"Starting explicit session migration for report: {report_id}")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message=f"Starting explicit session migration for report: {report_id}",
        progress=0,
        message_type="info"
    )
    
    from ..migrator import CognosModuleMigratorExplicit
    
    migrator = CognosModuleMigratorExplicit(
        migration_config=migration_config,
        cognos_config=cognos_config,
        cognos_url=cognos_url,
        session_key=session_key,
        logger=logger
    )
    
    log_info("Migrator initialized successfully")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message="Migrator initialized successfully",
        progress=10,
        message_type="info"
    )
    
    # Perform the migration
    try:
        result = migrator.migrate_report(report_id, output_path)
        
        if result:
            log_info(f"Report migration completed successfully: {report_id}")
            
            # Also send to WebSocket for frontend updates
            logging_helper(
                message=f"Report migration completed successfully: {report_id}",
                progress=100,
                message_type="info"
            )
        else:
            log_error(f"Report migration failed: {report_id}")
            
            # Also send to WebSocket for frontend updates
            logging_helper(
                message=f"Report migration failed: {report_id}",
                progress=100,
                message_type="error"
            )
        
        return result
    
    except Exception as e:
        log_error(f"Error during report migration: {str(e)}", exception=e)
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Error during report migration: {str(e)}",
            progress=100,
            message_type="error"
        )
        
        return False
