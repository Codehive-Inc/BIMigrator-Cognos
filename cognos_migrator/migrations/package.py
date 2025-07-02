"""
Package migration orchestrator for Cognos Framework Manager packages.

This module contains functions for migrating Cognos Framework Manager packages to Power BI.
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
from cognos_migrator.extractors.packages import PackageExtractor
from cognos_migrator.generators import PowerBIProjectGenerator
from cognos_migrator.models import PowerBIProject
from ..consolidation import consolidate_model_tables


def migrate_package_with_explicit_session(package_file_path: str,
                                       output_path: str,
                                       cognos_url: str, session_key: str,
                                       folder_id: str = None,
                                       cpf_file_path: str = None,
                                       task_id: Optional[str] = None,
                                       auth_key: str = "IBM-BA-Authorization") -> bool:
    """Migrate a Cognos Framework Manager package file to Power BI with explicit session credentials
    
    This function does not use environment variables and will raise an exception
    if the session key is expired.
    
    Args:
        package_file_path: Path to the FM package file
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
    configure_logging("cognos_package_migration")
    
    # Generate task_id if not provided
    if task_id is None:
        task_id = f"migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with task ID and total steps (8 steps in the migration process)
    set_task_info(task_id, total_steps=8)
    
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
    
    # Log the start of migration
    log_info(f"Starting explicit session migration for package: {package_file_path}")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message=f"Starting explicit session migration for package: {package_file_path}",
        progress=0,
        message_type="info"
    )
    
    try:
        # Ensure output path is within the standard output directory
        base_output_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "output"
        base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # If output_path is an absolute path, extract just the directory name
        if os.path.isabs(output_path):
            output_name = os.path.basename(output_path)
        else:
            output_name = output_path
        
        # Remove any path separators to get a clean directory name
        output_name = output_name.replace('/', '_').replace('\\', '_')
        
        # Create the final output directory within the standard output directory
        output_dir = base_output_dir / output_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Log the actual output directory being used
        log_info(f"Using output directory: {output_dir}")
        
        # Create subdirectories
        extracted_dir = output_dir / "extracted"
        extracted_dir.mkdir(exist_ok=True)
        
        pbit_dir = output_dir / "pbit"
        pbit_dir.mkdir(exist_ok=True)
        
        # Step 1: Extract package information
        logging_helper(
            message="Extracting package information",
            progress=20,
            message_type="info"
        )
        
        # Create package extractor
        package_extractor = PackageExtractor(logger=logging.getLogger(__name__))
        
        # Extract package information
        package_info = package_extractor.extract_package(package_file_path)
        
        # Save extracted information
        with open(extracted_dir / "package_info.json", 'w', encoding='utf-8') as f:
            json.dump(package_info, f, indent=2)
        
        log_info(f"Extracted package information: {package_info['name']}")
        
        # Step 2: Convert to Power BI data model
        logging_helper(
            message="Converting to Power BI data model",
            progress=40,
            message_type="info"
        )
        
        # Convert package info to data model
        data_model = package_extractor.convert_to_data_model(package_info)
        
        log_info(f"Converted package to data model with {len(data_model.tables)} tables and {len(data_model.relationships)} relationships")
        
        # Step 3: Create Power BI project
        logging_helper(
            message="Creating Power BI project",
            progress=60,
            message_type="info"
        )
        
        # Migration config was already created above
        
        # Create a Power BI project
        project = PowerBIProject(
            name=package_info['name'],
            data_model=data_model,
            report=None  # No report for package migration
        )
        
        # Create project generator
        project_generator = PowerBIProjectGenerator(migration_config)
        
        # Generate Power BI project
        project_generator.generate_project(project, str(pbit_dir))
        
        log_info(f"Generated Power BI project at: {pbit_dir}")
        
        # Step 4: Consolidate model tables
        logging_helper(
            message="Consolidating model tables",
            progress=80,
            message_type="info"
        )
        
        consolidate_model_tables(output_path)
        
        # Log successful completion
        log_info(f"Package migration completed successfully: {package_file_path}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Package migration completed successfully",
            progress=100,
            message_type="info"
        )
        
        return True
        
    except Exception as e:
        log_error(f"Package migration failed: {str(e)}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Package migration failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        
        return False


def migrate_package_with_reports_explicit_session(package_file_path: str,
                                       output_path: str,
                                       cognos_url: str, session_key: str,
                                       report_ids: List[str] = None,
                                       cpf_file_path: str = None,
                                       task_id: Optional[str] = None,
                                       auth_key: str = "IBM-BA-Authorization") -> bool:
    """Migrate a Cognos Framework Manager package file with explicit session credentials and specific reports
    
    This function allows migrating a package with specific reports.
    It does not use environment variables and will raise an exception if the session key is expired.
    
    Args:
        package_file_path: Path to the FM package file
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        report_ids: List of specific report IDs to migrate and associate with the package
        cpf_file_path: Optional path to CPF file for enhanced metadata
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        
    Returns:
        bool: True if migration was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """
    # Configure logging for this module
    configure_logging("cognos_package_reports_migration")
    
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
    
    # Create Cognos client for API operations
    cognos_client = CognosClient(cognos_config, base_url=cognos_url, session_key=session_key)
    
    # Log the start of migration
    log_info(f"Starting package with reports migration for: {package_file_path}")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message=f"Starting package with reports migration for: {package_file_path}",
        progress=0,
        message_type="info"
    )
    
    try:
        # Create output directory structure
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        extracted_dir = output_dir / "extracted"
        extracted_dir.mkdir(exist_ok=True)
        
        pbit_dir = output_dir / "pbit"
        pbit_dir.mkdir(exist_ok=True)
        
        # Step 1: Migrate reports if report_ids are provided
        successful_report_ids = []
        if report_ids:
            logging_helper(
                message=f"Migrating {len(report_ids)} reports",
                progress=10,
                message_type="info"
            )
            
            # Import the report migration function
            from cognos_migrator.migrations.report import migrate_report_with_explicit_session
            
            # Migrate each report
            for i, report_id in enumerate(report_ids):
                report_output_path = str(reports_dir / f"report_{i}")
                success = migrate_report_with_explicit_session(
                    report_id=report_id,
                    output_path=report_output_path,
                    cognos_url=cognos_url,
                    session_key=session_key,
                    auth_key=auth_key
                )
                
                if success:
                    successful_report_ids.append(report_id)
                    log_info(f"Successfully migrated report: {report_id}")
                else:
                    log_warning(f"Failed to migrate report: {report_id}")
            
            # Save successful report IDs
            with open(extracted_dir / "associated_reports.json", 'w', encoding='utf-8') as f:
                json.dump({"report_ids": successful_report_ids}, f, indent=2)
                
            log_info(f"Successfully migrated {len(successful_report_ids)} out of {len(report_ids)} reports")
        
        # Step 2: Extract package information
        logging_helper(
            message="Extracting package information",
            progress=30,
            message_type="info"
        )
        
        # Create package extractor
        package_extractor = PackageExtractor(logger=logging.getLogger(__name__))
        
        # Extract package information
        package_info = package_extractor.extract_package(package_file_path)
        
        # Save extracted information
        with open(extracted_dir / "package_info.json", 'w', encoding='utf-8') as f:
            json.dump(package_info, f, indent=2)
        
        log_info(f"Extracted package information: {package_info['name']}")
        
        # Step 3: Convert to Power BI data model
        logging_helper(
            message="Converting to Power BI data model",
            progress=50,
            message_type="info"
        )
        
        # Convert package info to data model
        data_model = package_extractor.convert_to_data_model(package_info)
        
        log_info(f"Converted package to data model with {len(data_model.tables)} tables and {len(data_model.relationships)} relationships")
        
        # Step 4: Create Power BI project
        logging_helper(
            message="Creating Power BI project",
            progress=70,
            message_type="info"
        )
        
        # Create a Power BI project
        project = PowerBIProject(
            name=package_info['name'],
            data_model=data_model,
            report=None  # No report for package migration
        )
        
        # Create project generator
        project_generator = PowerBIProjectGenerator(migration_config)
        
        # Generate Power BI project
        project_generator.generate_project(project, str(pbit_dir))
        
        log_info(f"Generated Power BI project at: {pbit_dir}")
        
        # Step 5: Consolidate model tables
        logging_helper(
            message="Consolidating model tables",
            progress=90,
            message_type="info"
        )
        
        consolidate_model_tables(output_path)
        
        # Log successful completion
        log_info(f"Package with reports migration completed successfully: {package_file_path}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Package with reports migration completed successfully",
            progress=100,
            message_type="info"
        )
        
        return True
        
    except Exception as e:
        log_error(f"Package with reports migration failed: {str(e)}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Package with reports migration failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        
        return False
