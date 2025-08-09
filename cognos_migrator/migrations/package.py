"""
Package migration orchestrator for Cognos Framework Manager packages.

This module contains functions for migrating Cognos Framework Manager packages to Power BI.
"""

import json
import logging
import os
import uuid
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from cognos_migrator.config import MigrationConfig, CognosConfig
from cognos_migrator.common.logging import configure_logging, log_info, log_warning, log_error, log_debug
from cognos_migrator.client import CognosClient, CognosAPIError
from cognos_migrator.common.websocket_client import logging_helper, set_task_info
from cognos_migrator.extractors.packages import PackageExtractor, ConsolidatedPackageExtractor
from ..models import PowerBIProject, DataModel
from ..generators import PowerBIProjectGenerator
from ..extractors.packages import ConsolidatedPackageExtractor
from .report import migrate_single_report_with_explicit_session
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
        # Create output directory structure using the exact path provided by the user
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Log the output directory being used
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
        
        # Create a basic Report object to ensure report files are generated
        from ..models import Report, ReportPage
        
        # Create a default report with the package name
        report = Report(
            id=f"report_{package_info['name'].lower().replace(' ', '_')}",
            name=package_info['name'],
            sections=[
                ReportPage(
                    name="page1",
                    display_name="Dashboard",
                    visuals=[]
                )
            ]
        )
        
        # Create Power BI project with report
        pbi_project = PowerBIProject(
            name=package_info['name'],
            data_model=data_model,
            report=report
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
        
        # Log completion
        logging_helper(
            message=f"Package migration completed successfully: {package_info['name']}",
            progress=100,
            message_type="success"
        )
        
        return True
        
    except Exception as e:
        log_error(f"Error during package migration: {str(e)}")
        
        # Also send to WebSocket for frontend updates
        logging_helper(
            message=f"Error during package migration: {str(e)}",
            progress=100,
            message_type="error"
        )
        
        return False


def extract_tables_from_report(report_output_path: str) -> Set[str]:
    """Extract table references from a migrated report
    
    This function analyzes the extracted report data to identify which tables
    are referenced by the report.
    
    Args:
        report_output_path: Path to the migrated report output directory
        
    Returns:
        Set of table names referenced by the report
    """
    table_references = set()
    report_path = Path(report_output_path)
    
    # Check for extracted directory
    extracted_dir = report_path / "extracted"
    if not extracted_dir.exists():
        return table_references
    
    # Check for report_data_items.json which contains column references
    data_items_file = extracted_dir / "report_data_items.json"
    if data_items_file.exists():
        try:
            with open(data_items_file, 'r', encoding='utf-8') as f:
                data_items = json.load(f)
                
            # Extract table names from data items
            for item in data_items:
                # Look for table references in expressions
                if "expression" in item and item["expression"]:
                    tables = extract_tables_from_expression(item["expression"])
                    table_references.update(tables)
                
                # Look for direct table references
                if "tableName" in item and item["tableName"]:
                    table_references.add(item["tableName"])
        except Exception as e:
            logging.error(f"Error extracting tables from report data items: {e}")
    
    # Check for report_queries.json which contains query references
    queries_file = extracted_dir / "report_queries.json"
    if queries_file.exists():
        try:
            with open(queries_file, 'r', encoding='utf-8') as f:
                queries = json.load(f)
                
            # Extract table names from queries
            for query in queries:
                if "source" in query and query["source"]:
                    # Extract table names from query source
                    tables = extract_tables_from_expression(query["source"])
                    table_references.update(tables)
                    
                if "tables" in query and isinstance(query["tables"], list):
                    for table in query["tables"]:
                        if isinstance(table, str):
                            table_references.add(table)
                        elif isinstance(table, dict) and "name" in table:
                            table_references.add(table["name"])
        except Exception as e:
            logging.error(f"Error extracting tables from report queries: {e}")
    
    return table_references


def extract_tables_from_expression(expression: str) -> Set[str]:
    """Extract table names from a Cognos expression
    
    Args:
        expression: Cognos expression string
        
    Returns:
        Set of table names found in the expression
    """
    tables = set()
    
    if not expression or not isinstance(expression, str):
        return tables
    
    # Pattern to match [namespace].[package].[table].[column] or [table].[column]
    patterns = [
        r'\[\w+\]\.\[\w+\]\.\[(\w+)\]',  # [namespace].[package].[table]
        r'\[(\w+)\]\.\[\w+\]'             # [table].[column]
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, expression)
        tables.update(matches)
    
    return tables


def load_table_filtering_settings() -> Dict[str, Any]:
    """Load table filtering settings from settings.json
    
    Returns:
        Dictionary containing table filtering settings
    """
    settings = {}
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        logging.warning("settings.json not found. Using default settings.")
    
    # Get table filtering settings with defaults
    table_filtering = settings.get('table_filtering', {})
    filtering_mode = table_filtering.get('mode', 'include-all')  # Default to include all tables
    always_include = table_filtering.get('always_include', [])
    
    return {
        'mode': filtering_mode,
        'always_include': always_include
    }


def filter_data_model_tables(data_model: DataModel, table_references: Set[str]) -> DataModel:
    """Filter the data model to include only tables referenced by reports
    
    Args:
        data_model: The original data model with all tables
        table_references: Set of table names referenced by reports
        
    Returns:
        Filtered data model with only referenced tables
    """
    # Load table filtering settings
    filtering_settings = load_table_filtering_settings()
    filtering_mode = filtering_settings['mode']
    always_include = filtering_settings['always_include']
    
    # If mode is not 'filter-reports', return the original model
    if filtering_mode != 'filter-reports':
        logging.info(f"Table filtering mode is '{filtering_mode}', not filtering tables")
        return data_model
    
    # If no table references and no always_include tables, return the original model
    if not table_references and not always_include:
        logging.warning("No table references or always_include tables found, returning original model")
        return data_model
    
    # Add always_include tables to the references
    if always_include:
        logging.info(f"Adding {len(always_include)} always_include tables to references: {always_include}")
        table_references.update(always_include)
    
    # Create a new data model with only the referenced tables
    filtered_tables = []
    
    # Check if CentralDateTable is in always_include and add it from date_tables if present
    if 'CentralDateTable' in always_include and hasattr(data_model, 'date_tables'):
        central_date_table_found = False
        for date_table in data_model.date_tables:
            if date_table['name'] == 'CentralDateTable':
                # Create a Table object from the date table info
                from ..models import Table, Column
                
                central_date_table = Table(
                    id=date_table['id'],
                    name='CentralDateTable',
                    display_name='Central Date Table',
                    description='Centralized date dimension table',
                    columns=[
                        Column(name='Date', data_type='datetime'),
                        Column(name='Year', data_type='int64'),
                        Column(name='Month', data_type='int64'),
                        Column(name='Day', data_type='int64')
                    ]
                )
                filtered_tables.append(central_date_table)
                central_date_table_found = True
                logging.info("Added CentralDateTable from date_tables to filtered tables")
                break
                
        if not central_date_table_found:
            logging.warning("CentralDateTable was in always_include but not found in date_tables")
    
    # Process regular tables
    for table in data_model.tables:
        # Check if table name is in references or always_include
        if table.name in table_references:
            filtered_tables.append(table)
            continue
            
        # Also check source_name if available
        if hasattr(table, 'source_name') and table.source_name in table_references:
            filtered_tables.append(table)
            continue
            
        # Check for partial matches (table names might have prefixes/suffixes)
        for ref in table_references:
            if ref in table.name or (hasattr(table, 'source_name') and ref in table.source_name):
                filtered_tables.append(table)
                break
    
    # Create a new data model with the filtered tables
    filtered_model_args = {
        'name': data_model.name,
        'tables': filtered_tables,
        'relationships': data_model.relationships,  # Keep all relationships for now
        'measures': data_model.measures
    }
    
    # Add perspectives if available in the data model
    if hasattr(data_model, 'perspectives'):
        filtered_model_args['perspectives'] = data_model.perspectives
        
    # Add date_tables if available in the data model
    if hasattr(data_model, 'date_tables'):
        filtered_model_args['date_tables'] = data_model.date_tables
        
    filtered_model = DataModel(**filtered_model_args)
    
    # Filter relationships to include only those between remaining tables
    filtered_table_names = {table.name for table in filtered_tables}
    filtered_relationships = []
    
    for rel in filtered_model.relationships:
        if (rel.from_table in filtered_table_names and 
            rel.to_table in filtered_table_names):
            filtered_relationships.append(rel)
    
    filtered_model.relationships = filtered_relationships
    
    return filtered_model


def migrate_package_with_reports_explicit_session(package_file_path: str,
                                       output_path: str,
                                       cognos_url: str, session_key: str,
                                       report_ids: List[str] = None,
                                       cpf_file_path: str = None,
                                       task_id: Optional[str] = None,
                                       auth_key: str = "IBM-BA-Authorization",
                                       dry_run: bool = False) -> bool:
    """Migrate a Cognos Framework Manager package file to Power BI with explicit session credentials
    and include specific reports
    
    This function does not use environment variables and will raise an exception
    if the session key is expired.
    
    Args:
        package_file_path: Path to the FM package file
        output_path: Path where migration output will be saved
        cognos_url: The Cognos base URL
        session_key: The session key for authentication
        report_ids: List of specific report IDs to migrate and associate with the package
        cpf_file_path: Optional path to CPF file for enhanced metadata
        task_id: Optional task ID for tracking (default: auto-generated)
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        dry_run: If True, skips actual Cognos API calls and uses dummy data for testing (default: False)
        
    Returns:
        bool: True if migration was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid (not in dry_run mode)
    """
    # Generate task ID if not provided
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    # Configure logging
    configure_logging()
    
    # Set task info for WebSocket updates
    set_task_info(task_id, total_steps=10)
    
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
        # Create output directory structure using the exact path provided by the user
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Log the output directory being used
        log_info(f"Using output directory: {output_dir}")
        
        # Create subdirectories
        extracted_dir = output_dir / "extracted"
        extracted_dir.mkdir(exist_ok=True)
        
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        pbit_dir = output_dir / "pbit"
        pbit_dir.mkdir(exist_ok=True)
        
        # Step 1: Migrate associated reports if provided
        successful_report_ids = []
        report_table_references = set()  # Set to track tables referenced by reports
        
        if report_ids and len(report_ids) > 0:
            logging_helper(
                message=f"Migrating {len(report_ids)} associated reports",
                progress=10,
                message_type="info"
            )
            
            if dry_run:
                # In dry run mode, skip actual report migration and use dummy table references
                log_info("Dry run mode: Skipping actual report migration and using dummy table references")
                
                # Create dummy report directories
                for i, report_id in enumerate(report_ids):
                    report_output_path = reports_dir / report_id
                    report_output_path.mkdir(exist_ok=True)
                    successful_report_ids.append(report_id)
                    
                    # Generate some dummy table references for testing
                    dummy_tables = [f"TABLE_{i}_{j}" for j in range(3)]
                    report_table_references.update(dummy_tables)
                    log_info(f"Added dummy table references for report {report_id}: {dummy_tables}")
                    
                    # Progress update
                    logging_helper(
                        message=f"Dry run: Processed report {i+1}/{len(report_ids)}: {report_id}",
                        progress=10 + int((i / len(report_ids)) * 20),
                        message_type="info"
                    )
            else:
                # Normal mode: Actually migrate reports via Cognos API
                for i, report_id in enumerate(report_ids):
                    log_info(f"Migrating report {i+1}/{len(report_ids)}: {report_id}")
                    
                    logging_helper(
                        message=f"Migrating report {i+1}/{len(report_ids)}: {report_id}",
                        progress=10 + int((i / len(report_ids)) * 20),
                        message_type="info"
                    )
                    
                    # Use the report migration function with explicit session
                    report_output_path = str(reports_dir / report_id)
                    report_success = migrate_single_report_with_explicit_session(
                        report_id=report_id,
                        output_path=report_output_path,
                        cognos_url=cognos_url,
                        session_key=session_key,
                        task_id=f"{task_id}_report_{i}",
                        auth_key=auth_key
                    )
                    
                    if report_success:
                        log_info(f"Report migration successful: {report_id}")
                        successful_report_ids.append(report_id)
                        
                        # Extract table references from the migrated report
                        report_tables = extract_tables_from_report(report_output_path)
                        if report_tables:
                            report_table_references.update(report_tables)
                            log_info(f"Extracted {len(report_tables)} table references from report {report_id}")
                    else:
                        log_warning(f"Report migration failed: {report_id}")
        
        # Step 2: Extract package information
        logging_helper(
            message="Extracting package information",
            progress=30,
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
        
        # Step 4: Filter tables based on report references
        if report_ids and len(report_ids) > 0 and report_table_references:
            logging_helper(
                message=f"Filtering data model to include only tables referenced by reports",
                progress=60,
                message_type="info"
            )
            
            # Filter the data model to include only tables referenced by reports
            data_model = filter_data_model_tables(data_model, report_table_references)
            
            log_info(f"Filtered data model now has {len(data_model.tables)} tables")
        
        # Step 5: Create Power BI project
        logging_helper(
            message="Creating Power BI project",
            progress=70,
            message_type="info"
        )
        
        # Create a basic Report object to ensure report files are generated
        from ..models import Report, ReportPage
        
        # Create a default report with the package name
        report = Report(
            id=f"report_{package_info['name'].lower().replace(' ', '_')}",
            name=package_info['name'],
            sections=[
                ReportPage(
                    name="page1",
                    display_name="Dashboard",
                    visuals=[]
                )
            ]
        )
        
        # Create Power BI project with report
        pbi_project = PowerBIProject(
            name=package_info['name'],
            data_model=data_model,
            report=report
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
