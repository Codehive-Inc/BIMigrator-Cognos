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
import shutil

from cognos_migrator.config import MigrationConfig, CognosConfig
from cognos_migrator.common.logging import configure_logging, log_info, log_warning, log_error, log_debug
from cognos_migrator.client import CognosClient, CognosAPIError
from cognos_migrator.common.websocket_client import logging_helper, set_task_info
from cognos_migrator.extractors.packages import PackageExtractor, ConsolidatedPackageExtractor
from ..models import PowerBIProject, DataModel, Report, ReportPage
from ..generators import PowerBIProjectGenerator
from ..extractors.packages import ConsolidatedPackageExtractor
from .report import migrate_single_report_with_explicit_session
from ..consolidation import consolidate_model_tables
from .report import migrate_single_report


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
        
        # Use the package-specific M-query converter for package migrations
        from cognos_migrator.converters import PackageMQueryConverter
        from cognos_migrator.generators.module_generators import ModuleModelFileGenerator
        from cognos_migrator.generators.template_engine import TemplateEngine
        
        # Initialize template engine and package M-query converter
        template_engine = TemplateEngine(template_directory=config.template_directory)
        package_mquery_converter = PackageMQueryConverter(output_path=str(output_dir))
        
        # Set up the model file generator with the package-specific converter
        if hasattr(generator, 'model_file_generator'):
            module_model_file_generator = ModuleModelFileGenerator(
                template_engine, 
                mquery_converter=package_mquery_converter
            )
            generator.model_file_generator = module_model_file_generator
        
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
                    name='CentralDateTable',
                    description='Centralized date dimension table',
                    columns=[
                        Column(name='Date', data_type='datetime', source_column='Date'),
                        Column(name='Year', data_type='int64', source_column='Year'),
                        Column(name='Month', data_type='int64', source_column='Month'),
                        Column(name='Day', data_type='int64', source_column='Day')
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


def _migrate_shared_model(
    package_file: str,
    report_files: List[str],
    output_path: str,
    cognos_url: str,
    session_key: str,
    llm_service: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> bool:
    """Helper function to orchestrate the shared model migration."""
    # --- Step 1: Intermediate migration for each report ---
    intermediate_dir = Path(output_path) / "intermediate_reports"
    shutil.rmtree(intermediate_dir, ignore_errors=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    successful_migrations_paths = []
    for report_file in report_files:
        report_name = Path(report_file).stem
        report_output_path = intermediate_dir / report_name
        
        success = migrate_single_report(
            output_path=str(report_output_path),
            cognos_url=cognos_url,
            session_key=session_key,
            report_file_path=report_file
        )
        if success:
            successful_migrations_paths.append(report_output_path)
    
    # --- Step 2: Analyze intermediate files and consolidate table schemas ---
    consolidated_tables: Dict[str, Table] = {}
    required_tables = set()
    
    # First, extract tables directly from report files to ensure we capture all references
    for report_path in successful_migrations_paths:
        try:
            # Extract tables from the report's extracted data
            report_tables = extract_tables_from_report(str(report_path))
            required_tables.update(report_tables)
            log_info(f"Extracted {len(report_tables)} tables from report {report_path.name}: {report_tables}")
        except Exception as e:
            log_error(f"Error extracting tables from report {report_path}: {e}")
    
    # Then process intermediate models to consolidate schemas
    for report_path in successful_migrations_paths:
        try:
            migrator = CognosModuleMigratorExplicit(
                cognos_url, session_key, output_path=str(report_path), llm_service=llm_service
            )
            intermediate_model = migrator._create_data_model_from_report(report_path / "extracted")
            
            for table in intermediate_model.tables:
                if table.name not in consolidated_tables:
                    consolidated_tables[table.name] = table
                else:
                    existing_table = consolidated_tables[table.name]
                    existing_column_names = {c.name for c in existing_table.columns}
                    for new_column in table.columns:
                        if new_column.name not in existing_column_names:
                            existing_table.columns.append(new_column)
                
                # Make sure we include this table in required_tables
                required_tables.add(table.name)
                
        except Exception as e:
            log_error(f"Error processing intermediate model for {report_path}: {e}")

    # Add any always_include tables from config
    if config and 'always_include' in config:
        required_tables.update(config['always_include'])
        
    log_info(f"Found {len(required_tables)} unique source tables to consolidate: {required_tables}")

    # --- Step 3: Filtered Package Extraction ---
    logging.info(f"FILTERING DEBUG: Table filtering config = {config}")
    logging.info(f"FILTERING DEBUG: Required tables before extraction = {required_tables}")
    
    # Ensure we have required tables - if empty, log warning and use a fallback approach
    if not required_tables and config and config.get('mode') == 'direct':
        logging.warning("No required tables found for filtering but mode is 'direct'. This would result in all tables being included.")
        # As a fallback, we could try to extract tables from report files again or use a different approach
        # For now, just log the warning so it's clear why filtering might not work as expected
    
    package_extractor = ConsolidatedPackageExtractor(
        config=config,
        logger=logging.getLogger(__name__)
    )
    package_info = package_extractor.extract_package(
        package_file,
        os.path.join(output_path, "extracted"),
        required_tables=required_tables
    )
    
    # Log the query subjects that were returned after filtering
    query_subject_names = [qs.get('name', 'Unknown') for qs in package_info.get('query_subjects', [])]
    logging.info(f"FILTERING DEBUG: Extractor returned package_info with {len(package_info.get('query_subjects', []))} tables.")
    logging.info(f"FILTERING DEBUG: Filtered query subject names: {query_subject_names}")

    # Step 4: Data Model Conversion from FILTERED package info
    data_model = package_extractor.convert_to_data_model(package_info)
    
    # Log the table names in the data model after conversion
    table_names = [table.name for table in data_model.tables]
    logging.info(f"FILTERING DEBUG: After conversion, data_model has {len(data_model.tables)} tables.")
    logging.info(f"FILTERING DEBUG: Data model table names: {table_names}")

    # Step 5: Merge report-specific data into the package-based model
    for table_name, consolidated_table in consolidated_tables.items():
        # Find table in data_model, case-insensitively
        target_table = next((t for t in data_model.tables if t.name.lower() == table_name.lower()), None)

        if target_table:
            existing_column_names = {c.name.lower() for c in target_table.columns}
            for new_column in consolidated_table.columns:
                if new_column.name.lower() not in existing_column_names:
                    target_table.columns.append(new_column)
                    logging.info(f"Added column '{new_column.name}' to table '{target_table.name}'.")
        else:
            logging.warning(f"Table '{table_name}' from reports not found in the filtered package model. It will not be added.")

    logging.info(f"Data model has {len(data_model.tables)} tables before generation: {[t.name for t in data_model.tables]}")

    # --- Step 6: Final Generation ---
    from cognos_migrator.config import MigrationConfig
    migration_config = MigrationConfig(output_directory=Path(output_path), template_directory=str(Path(__file__).parent.parent / "templates"))
    generator = PowerBIProjectGenerator(migration_config)

    # Force creation of a new PBI project with the filtered data model
    final_pbi_project = PowerBIProject(
        name=data_model.name,
        data_model=data_model,
        report=Report(id=f"report_{data_model.name}", name=data_model.name)
    )
    logging.info(f"Explicitly creating final PBI project with {len(final_pbi_project.data_model.tables)} tables.")

    pbit_dir = Path(output_path) / "pbit"
    pbit_dir.mkdir(parents=True, exist_ok=True)
    generator.generate_project(final_pbi_project, str(pbit_dir))

    return True, str(output_path)

def migrate_package_with_local_reports(package_file_path: str,
                                       output_path: str,
                                       report_file_paths: List[str],
                                       cognos_url: str,
                                       session_key: str,
                                       task_id: Optional[str] = None) -> bool:
    """Orchestrates shared model creation for a package and local report files."""
    config = load_table_filtering_settings()
    logging.info(f"FILTERING DEBUG: In migrate_package_with_local_reports, loaded table filtering settings: {config}")
    return _migrate_shared_model(
        package_file=package_file_path,
        report_files=report_file_paths,
        output_path=output_path,
        cognos_url=cognos_url,
        session_key=session_key,
        config=config
    )

def migrate_package_with_reports_explicit_session(package_file_path: str,
                                       output_path: str,
                                       cognos_url: str, session_key: str,
                                       report_ids: List[str] = None,
                                       cpf_file_path: str = None,
                                       task_id: Optional[str] = None,
                                       auth_key: str = "IBM-BA-Authorization",
                                       dry_run: bool = False) -> bool:
    """Orchestrates shared model creation for a package and live report IDs."""
    return _migrate_shared_model(
        package_file=package_file_path,
        report_files=report_ids,
        output_path=output_path,
        cognos_url=cognos_url,
        session_key=session_key
    )
