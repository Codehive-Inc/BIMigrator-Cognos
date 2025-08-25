"""
Explicit session-based migration orchestrator for Cognos to Power BI migration

This module provides migration functionality that works with explicit credentials
without requiring environment variables or .env files.
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
from cognos_migrator.consolidation import consolidate_model_tables
from cognos_migrator.migrator import CognosModuleMigratorExplicit

__all__ = [
    'test_cognos_connection',
    'post_process_module_with_explicit_session',
    'consolidate_model_tables'
]


def test_cognos_connection(cognos_url: str, session_key: str) -> bool:
    """Test connection to Cognos using URL and session key
    
    Args:
        cognos_url: The Cognos base URL
        session_key: The session key to test
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    return CognosClient.test_connection_with_session(cognos_url, session_key)


def post_process_module_with_explicit_session(module_id: str, output_path: str,
                                             cognos_url: str, session_key: str,
                                             successful_report_ids: List[str] = None,
                                             auth_key: str = "IBM-BA-Authorization",
                                             settings: Optional[Dict[str, Any]] = None) -> bool:
    """Post-process a module with explicit session credentials
    
    This function does not use environment variables and will raise an exception
    if the session key is expired.
    
    Args:
        module_id: ID of the Cognos module
        output_path: Path where migration output is stored
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        successful_report_ids: List of successfully migrated report IDs
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        settings: Optional settings dictionary to override default settings.json
        
    Returns:
        bool: True if post-processing was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    # First verify the session is valid
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        raise CognosAPIError("Session key is expired or invalid")
    
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Post-processing module {module_id} at {output_path}")
        
        logging_helper(
            message=f"Starting post-processing for module: {module_id}",
            progress=0,
            message_type="info"
        )
        
        # Create migration config with explicit values
        migration_config = MigrationConfig(
            output_directory=output_path,
            preserve_structure=True,
            include_metadata=True,
            generate_documentation=True,
            template_directory=str(Path(__file__).parent / "templates"),
            llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),
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
        migrator = CognosModuleMigratorExplicit(
            migration_config=migration_config,
            cognos_config=cognos_config,
            cognos_url=cognos_url,
            session_key=session_key,
            logger=logger,
            settings=settings
        )
        
        # Consolidate model tables
        logger.info("Consolidating tables into model.tmdl")
        logging_helper(
            message="Consolidating tables into model.tmdl",
            progress=50,
            message_type="info"
        )
        
        consolidate_result = consolidate_model_tables(output_path)
        if not consolidate_result:
            logger.warning("Table consolidation failed")
            logging_helper(
                message="Table consolidation failed",
                progress=60,
                message_type="warning"
            )
            return False
        
        logger.info("Successfully consolidated all tables into model.tmdl")
        logging_helper(
            message="Successfully consolidated all tables into model.tmdl",
            progress=100,
            message_type="info"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error during post-processing: {e}")
        logging_helper(
            message=f"Error during post-processing: {str(e)}",
            progress=100,
            message_type="error"
        )
        return False
