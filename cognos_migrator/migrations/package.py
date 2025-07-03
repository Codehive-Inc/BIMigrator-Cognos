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
from cognos_migrator.extractors.packages import PackageExtractor, ConsolidatedPackageExtractor
from cognos_migrator.generators import PowerBIProjectGenerator
from cognos_migrator.models import PowerBIProject
from cognos_migrator.migrations.report import migrate_single_report_with_explicit_session
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
    # Generate task ID if not provided
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    # Configure logging
    configure_logging()
    
    # Set task info for WebSocket updates
    set_task_info(task_id, total_steps=8)
    
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
        
        # Create package extractor using the new modular architecture
        package_extractor = ConsolidatedPackageExtractor(logger=logging.getLogger(__name__))
        
        # Extract package information
        package_info = package_extractor.extract_package(package_file_path, str(extracted_dir))
        
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
        
        # Convert to data model
        data_model = package_extractor.convert_to_data_model(package_info)
        
        # Consolidate tables if needed
        consolidate_model_tables(str(extracted_dir))
        
        log_info(f"Converted to data model with {len(data_model.tables)} tables")
        
        # Step 3: Create Power BI project
        logging_helper(
            message="Creating Power BI project",
            progress=60,
            message_type="info"
        )
        
        # Create Power BI project
        pbi_project = PowerBIProject(
            name=package_info['name'],
            data_model=data_model
        )
        
        # Step 4: Generate Power BI files
        logging_helper(
            message="Generating Power BI files",
            progress=80,
            message_type="info"
        )
        
        # Create generator
        # Initialize with config instead of logger
        config = MigrationConfig(
            template_directory=str(Path(__file__).parent.parent / 'templates'),
            llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),  # Enable DAX service
            llm_service_enabled=True
        )
        generator = PowerBIProjectGenerator(config=config)
        
        # Generate Power BI project files
        success = generator.generate_project(pbi_project, pbit_dir)
        pbit_path = pbit_dir if success else None
        
        log_info(f"Generated PBIT file: {pbit_path}")
        
        # Step 5: Complete migration
        logging_helper(
            message="Migration completed successfully",
            progress=100,
            message_type="success"
        )
        
        return True
        
    except Exception as e:
        log_error(f"Migration failed: {e}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Migration failed: {e}",
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
    # Generate task ID if not provided
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    # Configure logging
    configure_logging()
    
    # Set task info for WebSocket updates
    set_task_info(task_id, total_steps=12)
    
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
    log_info(f"Starting explicit session migration for package with reports: {package_file_path}")
    
    # Also send to WebSocket for frontend updates
    logging_helper(
        message=f"Starting explicit session migration for package with reports: {package_file_path}",
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
        
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        pbit_dir = output_dir / "pbit"
        pbit_dir.mkdir(exist_ok=True)
        
        # Step 1: Extract package information
        logging_helper(
            message="Extracting package information",
            progress=10,
            message_type="info"
        )
        
        # Create package extractor using the new modular architecture
        package_extractor = ConsolidatedPackageExtractor(logger=logging.getLogger(__name__))
        
        # Extract package information
        package_info = package_extractor.extract_package(package_file_path, str(extracted_dir))
        
        # Save extracted information
        with open(extracted_dir / "package_info.json", 'w', encoding='utf-8') as f:
            json.dump(package_info, f, indent=2)
        
        log_info(f"Extracted package information: {package_info['name']}")
        
        # Step 2: Download report specifications
        logging_helper(
            message="Downloading report specifications",
            progress=30,
            message_type="info"
        )
        
        # Create Cognos client
        client = CognosClient(cognos_config)
        
        # Download report specifications for each report ID
        report_specs = []
        
        if report_ids:
            for report_id in report_ids:
                try:
                    # Get report spec
                    report_spec = client.get_report_spec(report_id)
                    
                    # Save report spec
                    report_specs.append(report_spec)
                    
                    # Save to file
                    with open(reports_dir / f"report_{report_id}.xml", 'w', encoding='utf-8') as f:
                        f.write(report_spec)
                    
                    log_info(f"Downloaded report spec for report ID: {report_id}")
                    
                except Exception as e:
                    log_warning(f"Failed to download report spec for report ID {report_id}: {e}")
        
        # Step 3: Convert to Power BI data model
        logging_helper(
            message="Converting to Power BI data model",
            progress=50,
            message_type="info"
        )
        
        # Convert to data model
        data_model = package_extractor.convert_to_data_model(package_info)
        
        # Consolidate tables if needed
        consolidate_model_tables(str(extracted_dir))
        
        log_info(f"Converted to data model with {len(data_model.tables)} tables")
        
        # Step 4: Create Power BI project
        logging_helper(
            message="Creating Power BI project",
            progress=70,
            message_type="info"
        )
        
        # Create Power BI project
        pbi_project = PowerBIProject(
            name=package_info['name'],
            data_model=data_model
        )
        
        # Step 5: Generate Power BI files
        logging_helper(
            message="Generating Power BI files",
            progress=90,
            message_type="info"
        )
        
        # Create generator
        # Initialize with config instead of logger
        config = MigrationConfig(
            template_directory=str(Path(__file__).parent.parent / 'templates'),
            llm_service_url=os.environ.get('DAX_API_URL', 'http://localhost:8080'),  # Enable DAX service
            llm_service_enabled=True
        )
        generator = PowerBIProjectGenerator(config=config)
        
        # Generate Power BI project files
        success = generator.generate_project(pbi_project, pbit_dir)
        pbit_path = pbit_dir if success else None
        
        log_info(f"Generated PBIT file: {pbit_path}")
        
        # Step 6: Complete migration
        logging_helper(
            message="Migration completed successfully",
            progress=100,
            message_type="success"
        )
        
        return True
        
    except Exception as e:
        log_error(f"Migration failed: {e}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Migration failed: {e}",
            progress=100,
            message_type="error"
        )
        
        return False
