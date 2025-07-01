"""
Module migration orchestrators for Cognos to Power BI migration.

This module contains functions for migrating Cognos modules to Power BI.
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
from ..consolidation import consolidate_model_tables
from ..models import PowerBIProject


def migrate_module_with_explicit_session(module_id: str,
                                       output_path: str,
                                       cognos_url: str, session_key: str,
                                       folder_id: str = None,
                                       cpf_file_path: str = None,
                                       task_id: Optional[str] = None,
                                       auth_key: str = "IBM-BA-Authorization") -> bool:
    """Migrate a Cognos module with explicit session credentials
    
    This function does not use environment variables and will raise an exception
    if the session key is expired.
    
    Args:
        module_id: ID of the Cognos module to migrate
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        folder_id: Optional folder ID containing reports to migrate
        cpf_file_path: Optional path to CPF file for enhanced metadata
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        
    Returns:
        bool: True if migration was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    # Configure logging for this module
    configure_logging("cognos_module_migration")
    
    # Generate task_id if not provided
    if task_id is None:
        task_id = f"migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with task ID and total steps (12 steps in the migration process)
    set_task_info(task_id, total_steps=12)
    
    # First verify the session is valid
    log_info(f"Testing connection to Cognos at {cognos_url}")
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        log_error("Session key is expired or invalid")
        raise CognosAPIError("Session key is expired or invalid")
    
    # Create a minimal config without using environment variables
    
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
    
    # Log the start of migration
    log_info(f"Starting explicit session migration for module: {module_id}")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message=f"Starting explicit session migration for module: {module_id}",
        progress=0,
        message_type="info"
    )
    
    from ..migrator import CognosModuleMigratorExplicit
    
    migrator = CognosModuleMigratorExplicit(
        migration_config=migration_config,
        cognos_config=cognos_config,
        cognos_url=cognos_url,
        session_key=session_key,
        logger=logger,
        cpf_file_path=cpf_file_path
    )
    
    log_info("Migrator initialized successfully")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message="Migrator initialized successfully",
        progress=10,
        message_type="info"
    )
    
    # Perform the migration
    result = migrator.migrate_module(module_id, output_path, folder_id, cpf_file_path)
    
    if result:
        log_info(f"Module migration completed successfully: {module_id}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Module migration completed successfully: {module_id}",
            progress=100,
            message_type="info"
        )
    else:
        log_error(f"Module migration failed: {module_id}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Module migration failed: {module_id}",
            progress=100,
            message_type="error"
        )
    
    return result


def migrate_module_with_reports_explicit_session(module_id: str,
                                       output_path: str,
                                       cognos_url: str, session_key: str,
                                       report_ids: List[str] = None,
                                       cpf_file_path: str = None,
                                       task_id: Optional[str] = None,
                                       auth_key: str = "IBM-BA-Authorization") -> bool:
    """Migrate a Cognos module with explicit session credentials and specific reports
    
    This function allows migrating a module with specific reports instead of requiring a folder.
    It does not use environment variables and will raise an exception if the session key is expired.
    
    Args:
        module_id: ID of the Cognos module to migrate
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        report_ids: List of specific report IDs to migrate and associate with the module
        cpf_file_path: Optional path to CPF file for enhanced metadata
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        
    Returns:
        bool: True if migration was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    # Configure logging for this module
    configure_logging("cognos_module_reports_migration")
    
    # Generate task_id if not provided
    if task_id is None:
        task_id = f"migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with task ID and total steps (12 steps in the migration process)
    set_task_info(task_id, total_steps=12)
    
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
    
    log_info(f"Starting explicit session migration for module: {module_id} with specific reports")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message=f"Starting explicit session migration for module: {module_id} with specific reports",
        progress=0,
        message_type="info"
    )
    
    from ..migrator import CognosModuleMigratorExplicit
    
    migrator = CognosModuleMigratorExplicit(
        migration_config=migration_config,
        cognos_config=cognos_config,
        cognos_url=cognos_url,
        session_key=session_key,
        logger=logger,
        cpf_file_path=cpf_file_path
    )
    
    log_info("Migrator initialized successfully")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message="Migrator initialized successfully",
        progress=10,
        message_type="info"
    )
    
    # Perform the module migration first
    log_info(f"Migrating module: {module_id}")
    module_result = migrator.migrate_module(module_id, output_path, None, cpf_file_path)
    
    if not module_result:
        log_error(f"Module migration failed: {module_id}")
        logging_helper(
            message=f"Module migration failed: {module_id}",
            progress=100,
            message_type="error"
        )
        return False
    
    log_info(f"Module migration completed successfully: {module_id}")
    logging_helper(
        message=f"Module migration completed successfully: {module_id}",
        progress=50,
        message_type="info"
    )
    
    # If no report IDs provided, we're done
    if not report_ids or len(report_ids) == 0:
        log_info("No report IDs provided, module migration complete")
        logging_helper(
            message="No report IDs provided, module migration complete",
            progress=100,
            message_type="info"
        )
        return True
    
    # Now migrate each report
    log_info(f"Migrating {len(report_ids)} reports")
    logging_helper(
        message=f"Migrating {len(report_ids)} reports",
        progress=60,
        message_type="info"
    )
    
    successful_reports = []
    failed_reports = []
    
    for i, report_id in enumerate(report_ids):
        log_info(f"Migrating report {i+1}/{len(report_ids)}: {report_id}")
        logging_helper(
            message=f"Migrating report {i+1}/{len(report_ids)}: {report_id}",
            progress=60 + int((i / len(report_ids)) * 30),
            message_type="info"
        )
        
        try:
            report_result = migrator.migrate_report(report_id, output_path)
            if report_result:
                log_info(f"Report migration successful: {report_id}")
                successful_reports.append(report_id)
            else:
                log_warning(f"Report migration failed: {report_id}")
                failed_reports.append(report_id)
        except Exception as e:
            log_error(f"Error migrating report {report_id}: {str(e)}", exception=e)
            failed_reports.append(report_id)
    
    # Log summary
    if failed_reports:
        log_warning(f"Migration completed with {len(successful_reports)} successful and {len(failed_reports)} failed reports")
        logging_helper(
            message=f"Migration completed with {len(successful_reports)} successful and {len(failed_reports)} failed reports",
            progress=90,
            message_type="warning"
        )
    else:
        log_info(f"All {len(successful_reports)} reports migrated successfully")
        logging_helper(
            message=f"All {len(successful_reports)} reports migrated successfully",
            progress=90,
            message_type="info"
        )
    
    # Post-process the module with the successful reports
    if successful_reports:
        from ..main import post_process_module_with_explicit_session
        
        log_info("Post-processing module with successful reports")
        logging_helper(
            message="Post-processing module with successful reports",
            progress=95,
            message_type="info"
        )
        
        post_result = post_process_module_with_explicit_session(
            module_id, output_path, cognos_url, session_key, successful_reports, auth_key
        )
        
        if post_result:
            log_info("Post-processing completed successfully")
            logging_helper(
                message="Post-processing completed successfully",
                progress=100,
                message_type="info"
            )
        else:
            log_warning("Post-processing completed with warnings")
            logging_helper(
                message="Post-processing completed with warnings",
                progress=100,
                message_type="warning"
            )
    
    return len(failed_reports) == 0
