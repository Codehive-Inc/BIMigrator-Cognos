"""
Package migration orchestrator for Cognos Framework Manager packages.

This module contains functions for migrating Cognos Framework Manager packages to Power BI.
"""

import json
import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
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
from ..migrator import CognosModuleMigratorExplicit
from ..converters.consolidated_mquery_converter import ConsolidatedMQueryConverter


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
        
        # Use the package-specific M-query converter and generator for package migrations
        from cognos_migrator.converters import PackageMQueryConverter
        from cognos_migrator.generators.package_model_file_generator import PackageModelFileGenerator
        from cognos_migrator.generators.template_engine import TemplateEngine
        
        # Initialize template engine and package M-query converter
        template_engine = TemplateEngine(template_directory=config.template_directory)
        package_mquery_converter = PackageMQueryConverter(output_path=str(output_dir))
        
        # Set up the package-specific model file generator
        if hasattr(generator, 'model_file_generator'):
            package_model_file_generator = PackageModelFileGenerator(
                template_engine, 
                mquery_converter=package_mquery_converter
            )
            generator.model_file_generator = package_model_file_generator
        
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
    
    # Pattern to match '[Namespace].[Table].[Column]' or '[Table].[Column]'
    # Handles spaces and other characters in names by matching anything inside the brackets.
    patterns = [
        r'\[[^\]]+\]\.\[([^\]]+)\]\.\[[^\]]+\]',  # Captures the middle part of a 3-part expression
        r'\[([^\]]+)\]\.\[[^\]]+\]'              # Captures the first part of a 2-part expression
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
    reports: List[str],
    output_path: str,
    cognos_url: str,
    session_key: str,
    reports_are_ids: bool = False,
    llm_service: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Helper function to orchestrate the shared model migration."""
    # --- Step 1: Intermediate migration for each report ---
    intermediate_dir = Path(output_path) / "intermediate_reports"
    shutil.rmtree(intermediate_dir, ignore_errors=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    successful_migrations_paths = []
    for report_item in reports:
        if reports_are_ids:
            # Sanitize report ID for use as a directory name
            report_name = re.sub(r'[\\/*?:"<>|]', "_", report_item)
        else:
            report_name = Path(report_item).stem
        
        report_output_path = intermediate_dir / report_name

        migration_args = {
            "output_path": str(report_output_path),
            "cognos_url": cognos_url,
            "session_key": session_key,
        }
        if reports_are_ids:
            migration_args["report_id"] = report_item
        else:
            migration_args["report_file_path"] = report_item
            
        success = migrate_single_report(**migration_args)
        
        if success:
            successful_migrations_paths.append(report_output_path)
    
    # --- Step 2: Analyze intermediate files and consolidate table schemas ---
    consolidated_tables: Dict[str, Table] = {}
    required_tables = set()

    # Initialize the CognosModuleMigratorExplicit once
    from cognos_migrator.config import MigrationConfig, CognosConfig
    migration_config = MigrationConfig(output_directory=Path(output_path), template_directory=str(Path(__file__).parent.parent / "templates"))
    cognos_config = CognosConfig(base_url=cognos_url, auth_key="session_key", auth_value=session_key)
    migrator = CognosModuleMigratorExplicit(
        migration_config=migration_config,
        cognos_config=cognos_config,
        cognos_url=cognos_url,
        session_key=session_key
    )

    for report_path in successful_migrations_paths:
        intermediate_model_path = report_path / "extracted"
        if not intermediate_model_path.exists():
            logging.warning(f"Intermediate model path does not exist, skipping: {intermediate_model_path}")
            continue

        intermediate_model = migrator._create_data_model_from_report(intermediate_model_path)
        if not intermediate_model:
            logging.warning(f"Could not create intermediate data model from {report_path.name}, skipping.")
            continue

        for table in intermediate_model.tables:
            # This is now the single source for collecting required tables
            required_tables.add(table.name)

            if table.name not in consolidated_tables:
                consolidated_tables[table.name] = table
            else:
                # Merge columns from the same source table used in different reports
                existing_table = consolidated_tables[table.name]
                existing_column_names = {c.name.lower() for c in existing_table.columns}
                for new_column in table.columns:
                    if new_column.name.lower() not in existing_column_names:
                        existing_table.columns.append(new_column)

    # Add any "always_include" tables from the configuration
    if config:
        always_include = config.get("table_filtering", {}).get("always_include", [])
        if always_include:
            required_tables.update(always_include)
            logging.info(f"Adding {len(always_include)} 'always_include' tables: {always_include}")

    # Safety check for direct mode
    if not required_tables and config and config.get("table_filtering", {}).get("mode") == "direct":
        logging.warning("No required tables were found and mode is 'direct'. This will result in an empty model.")

    logging.info(f"Consolidated a final list of {len(required_tables)} required tables: {required_tables}")
    
    # --- Step 2.5: Merge calculations from intermediate reports ---
    logging.info("Merging calculations from intermediate reports")
    # Get the paths to the intermediate reports directory
    intermediate_reports_dir = Path(output_path) / "intermediate_reports"
    if intermediate_reports_dir.exists() and intermediate_reports_dir.is_dir():
        # Get all subdirectories in the intermediate_reports directory
        intermediate_report_paths = [p for p in intermediate_reports_dir.iterdir() if p.is_dir()]
        logging.info(f"Found {len(intermediate_report_paths)} intermediate report directories")
        _merge_calculations_from_intermediate_reports(intermediate_report_paths, Path(output_path))
    else:
        logging.warning(f"Intermediate reports directory not found at {intermediate_reports_dir}")
        # Fall back to using successful_migrations_paths
        logging.info(f"Falling back to using successful_migrations_paths with {len(successful_migrations_paths)} paths")
        _merge_calculations_from_intermediate_reports(successful_migrations_paths, Path(output_path))
    
    # --- Step 3: Package Extraction based on REQUIRED tables ---
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

    # Now, we need to generate the M-queries for this consolidated model
    # We will use our new, specialized converter for this.
    consolidated_converter = ConsolidatedMQueryConverter(output_path=output_path)
    for table in data_model.tables:
        table.m_query = consolidated_converter.convert_to_m_query(table)

    logging.info(f"Data model has {len(data_model.tables)} tables before generation: {[t.name for t in data_model.tables]}")

    # --- Step 6: Final Generation ---
    from cognos_migrator.config import MigrationConfig
    from ..processors.tmdl_post_processor import TMDLPostProcessor
    migration_config = MigrationConfig(output_directory=Path(output_path), template_directory=str(Path(__file__).parent.parent / "templates"))
    generator = PowerBIProjectGenerator(migration_config)
    
    # Use the package-specific M-query converter and generator for shared model migrations
    from cognos_migrator.converters import PackageMQueryConverter
    from cognos_migrator.generators.package_model_file_generator import PackageModelFileGenerator
    from cognos_migrator.generators.template_engine import TemplateEngine
    
    # Initialize template engine and package M-query converter for shared models
    template_engine = TemplateEngine(template_directory=migration_config.template_directory)
    package_mquery_converter = PackageMQueryConverter(output_path=str(Path(output_path)))
    
    # Set up the package-specific model file generator for shared models
    if hasattr(generator, 'model_file_generator'):
        package_model_file_generator = PackageModelFileGenerator(
            template_engine, 
            mquery_converter=package_mquery_converter
        )
        generator.model_file_generator = package_model_file_generator

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
    
    # --- Step 5.5: Merge calculations into table JSON files ---
    logging.info("Merging calculations into table JSON files")
    _merge_calculations_into_table_json(Path(output_path))
    
    # --- Step 6.5: Consolidate intermediate report pages and slicers into final report ---
    logging.info("Consolidating intermediate report pages and slicers into final unified report")
    _consolidate_intermediate_reports_into_final(output_path, successful_migrations_paths)
    
    # --- Step 7: Post-process the generated TMDL to fix relationships ---
    tmdl_relationships_file = pbit_dir / "Model" / "relationships.tmdl"
    if tmdl_relationships_file.exists():
        post_processor = TMDLPostProcessor(logger=logging.getLogger(__name__))
        post_processor.fix_relationships(str(tmdl_relationships_file))
    else:
        logging.warning(f"Could not find relationships file to post-process: {tmdl_relationships_file}")
        
    # --- Step 7.5: Calculations are handled through the table JSON files ---
    logging.info("Calculations are handled through the table JSON files")

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
        reports=report_file_paths,
        output_path=output_path,
        cognos_url=cognos_url,
        session_key=session_key,
        config=config,
        reports_are_ids=False,
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
    config = load_table_filtering_settings()
    logging.info(f"FILTERING DEBUG: In migrate_package_with_reports_explicit_session, loaded table filtering settings: {config}")
    return _migrate_shared_model(
        package_file=package_file_path,
        reports=report_ids,
        output_path=output_path,
        cognos_url=cognos_url,
        session_key=session_key,
        config=config,
        reports_are_ids=True,
    )

def _merge_calculations_from_intermediate_reports(
    intermediate_report_paths: List[Path],
    output_path: Path
) -> None:
    """
    Merge calculations from all intermediate report migrations into the consolidated calculations.json file.
    
    Args:
        intermediate_report_paths: List of paths to intermediate report migrations
        output_path: Path to the output directory for the consolidated migration
    """
    logger = logging.getLogger(__name__)
    consolidated_calculations = {"calculations": []}
    
    # Ensure the extracted directory exists in the output path
    extracted_dir = output_path / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    
    consolidated_path = extracted_dir / "calculations.json"
    
    # Load existing consolidated calculations if they exist
    if consolidated_path.exists():
        try:
            with open(consolidated_path, 'r', encoding='utf-8') as f:
                consolidated_calculations = json.load(f)
                logger.info(f"Loaded existing consolidated calculations with {len(consolidated_calculations.get('calculations', []))} entries")
        except Exception as e:
            logger.error(f"Error loading existing consolidated calculations: {e}")
            consolidated_calculations = {"calculations": []}
    
    # Track calculations by table name and column name, with DAX comparison
    # Key format: f"{table_name}|{column_name}"
    calculation_map = {}
    
    # First, add any existing calculations to the map
    for calc in consolidated_calculations.get("calculations", []):
        table_name = calc.get("TableName")
        column_name = calc.get("CognosName")
        dax_expression = calc.get("DAXExpression", "")
        
        if table_name and column_name:
            key = f"{table_name}|{column_name}"
            if key not in calculation_map:
                calculation_map[key] = []
            
            # Check if this exact DAX expression already exists
            dax_exists = any(existing_calc.get("DAXExpression", "") == dax_expression 
                            for existing_calc in calculation_map[key])
            
            if not dax_exists:
                calculation_map[key].append(calc)
    
    # Log the paths we're checking
    logger.info(f"Looking for calculations in {len(intermediate_report_paths)} intermediate report paths")
    for i, path in enumerate(intermediate_report_paths):
        logger.info(f"Intermediate report path {i+1}: {path}")
    
    # Process each intermediate report
    for report_path in intermediate_report_paths:
        # Check if this is a directory path to an intermediate report
        if not report_path.is_dir():
            logger.warning(f"Path is not a directory, skipping: {report_path}")
            continue
            
        # Look for the extracted directory within the intermediate report path
        intermediate_extracted = report_path / "extracted"
        if not intermediate_extracted.exists():
            logger.warning(f"No extracted directory found in {report_path}, skipping")
            continue
            
        # Look for calculations.json in the extracted directory
        calc_file = intermediate_extracted / "calculations.json"
        if not calc_file.exists():
            logger.warning(f"No calculations.json found in {intermediate_extracted}, skipping")
            continue
            
        try:
            with open(calc_file, 'r', encoding='utf-8') as f:
                report_calcs = json.load(f)
                
            if not report_calcs or "calculations" not in report_calcs:
                logger.warning(f"No calculations found in {calc_file}, skipping")
                continue
                
            logger.info(f"Found {len(report_calcs.get('calculations', []))} calculations in {report_path.name}")
            
            # Process each calculation
            for calc in report_calcs.get("calculations", []):
                table_name = calc.get("TableName")
                column_name = calc.get("CognosName")
                dax_expression = calc.get("DAXExpression", "")
                
                if not table_name or not column_name:
                    logger.warning(f"Skipping calculation with missing table or column name: {calc}")
                    continue
                
                key = f"{table_name}|{column_name}"
                if key not in calculation_map:
                    calculation_map[key] = []
                    calculation_map[key].append(calc)
                    logger.info(f"Added new calculation for {table_name}.{column_name}")
                else:
                    # Check if this exact DAX expression already exists
                    dax_exists = any(existing_calc.get("DAXExpression", "") == dax_expression 
                                    for existing_calc in calculation_map[key])
                    
                    if not dax_exists:
                        calculation_map[key].append(calc)
                        logger.info(f"Added variant calculation for {table_name}.{column_name} with different DAX")
                    else:
                        logger.info(f"Skipped duplicate calculation for {table_name}.{column_name} with same DAX")
                
        except Exception as e:
            logger.error(f"Error processing calculations from {calc_file}: {e}")
    
    # Convert the map back to a list
    all_calculations = []
    for calc_list in calculation_map.values():
        all_calculations.extend(calc_list)
    
    consolidated_calculations["calculations"] = all_calculations
    
    # Save the consolidated calculations
    try:
        with open(consolidated_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated_calculations, f, indent=2)
        logger.info(f"Saved {len(consolidated_calculations['calculations'])} consolidated calculations to {consolidated_path}")
    except Exception as e:
        logger.error(f"Error saving consolidated calculations to {consolidated_path}: {e}")
        
    # Verify the file was created
    if consolidated_path.exists():
        logger.info(f"Verified consolidated calculations file exists at {consolidated_path}")
    else:
        logger.error(f"Failed to create consolidated calculations file at {consolidated_path}")


def _merge_calculations_into_table_json(
    output_path: Path
) -> None:
    """
    Merge calculations from calculations.json into table JSON files.
    
    This function ensures that all calculations in calculations.json are properly
    added as calculated columns in their respective table JSON files.
    
    Args:
        output_path: Path to the output directory for the migration
    """
    import json
    import glob
    import os
    import re
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    extracted_dir = output_path / "extracted"
    calculations_file = extracted_dir / "calculations.json"
    
    # Check if calculations.json exists
    if not calculations_file.exists():
        logger.warning(f"Calculations file not found at {calculations_file}, skipping calculation merge")
        return
    
    # Load calculations from calculations.json
    try:
        with open(calculations_file, 'r', encoding='utf-8') as f:
            calculations_data = json.load(f)
        
        # Group calculations by table name
        table_calculations = {}
        for calc in calculations_data.get('calculations', []):
            table_name = calc.get('TableName')
            if table_name:
                if table_name not in table_calculations:
                    table_calculations[table_name] = []
                table_calculations[table_name].append(calc)
        
        logger.info(f"Loaded {len(calculations_data.get('calculations', []))} calculations for {len(table_calculations)} tables")
    except Exception as e:
        logger.error(f"Error loading calculations from {calculations_file}: {e}")
        return
    
    # Find all table JSON files
    table_files = list(extracted_dir.glob("table_*.json"))
    logger.info(f"Found {len(table_files)} table JSON files")
    
    # Process each table file
    for table_file in table_files:
        # Extract table name from filename (remove 'table_' prefix and '.json' suffix)
        table_name = table_file.stem.replace('table_', '')
        
        # Check if we have calculations for this table
        if table_name not in table_calculations:
            logger.info(f"No calculations found for table {table_name}, skipping")
            continue
        
        # Load table JSON
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                table_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading table data from {table_file}: {e}")
            continue
        
        # Get calculations for this table
        table_calcs = table_calculations[table_name]
        logger.info(f"Processing {len(table_calcs)} calculations for table {table_name}")
        
        # Ensure columns list exists
        if 'columns' not in table_data:
            table_data['columns'] = []
        
        # Get existing column names to avoid duplicates
        existing_columns = {col.get('source_name', col.get('name')).lower() for col in table_data['columns'] if col.get('source_name') or col.get('name')}
        
        # Add calculations as columns
        added_count = 0
        for calc in table_calcs:
            column_name = calc.get('CognosName')
            dax_formula = calc.get('FormulaDax')
            
            if not column_name or not dax_formula:
                logger.warning(f"Skipping calculation with missing name or formula: {calc}")
                continue
            
            # Check if column already exists
            if column_name.lower() in existing_columns:
                # Update existing column to ensure it's marked as calculated
                for col in table_data['columns']:
                    if col.get('source_name', col.get('name', '')).lower() == column_name.lower():
                        # Update with full report migration format
                        col['source_name'] = column_name
                        col['datatype'] = 'string'  # Default to string, could be improved based on formula
                        col['format_string'] = None
                        col['lineage_tag'] = None
                        col['source_column'] = dax_formula
                        col['description'] = None
                        col['is_hidden'] = False
                        col['summarize_by'] = 'none'
                        col['data_category'] = None
                        col['is_calculated'] = True
                        col['is_data_type_inferred'] = True
                        col['annotations'] = {'SummarizationSetBy': 'Automatic'}
                        logger.info(f"Updated existing column {column_name} as calculated column")
                        break
            else:
                # Add new calculated column with full report migration format
                new_column = {
                    'source_name': column_name,
                    'datatype': 'string',  # Default to string, could be improved based on formula
                    'format_string': None,
                    'lineage_tag': None,
                    'source_column': dax_formula,
                    'description': None,
                    'is_hidden': False,
                    'summarize_by': 'none',
                    'data_category': None,
                    'is_calculated': True,
                    'is_data_type_inferred': True,
                    'annotations': {'SummarizationSetBy': 'Automatic'}
                }
                table_data['columns'].append(new_column)
                existing_columns.add(column_name.lower())
                added_count += 1
        
        # Save updated table JSON
        try:
            with open(table_file, 'w', encoding='utf-8') as f:
                json.dump(table_data, f, indent=2)
            logger.info(f"Added {added_count} calculated columns to {table_file}")
        except Exception as e:
            logger.error(f"Error saving updated table data to {table_file}: {e}")


def _consolidate_intermediate_reports_into_final(
    output_path: str,
    successful_migrations_paths: List[Path]
) -> None:
    """
    Consolidate intermediate report pages and slicers into the final unified report.
    This preserves all the enhanced slicer generation from individual reports.
    """
    import json
    import shutil
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    final_pbit_path = Path(output_path) / "pbit"
    final_sections_path = final_pbit_path / "Report" / "sections"
    
    # Clear the default basic section
    if final_sections_path.exists():
        shutil.rmtree(final_sections_path)
    final_sections_path.mkdir(parents=True, exist_ok=True)
    
    section_ordinal = 0
    
    for report_path in successful_migrations_paths:
        intermediate_sections_path = report_path / "pbit" / "Report" / "sections"
        
        if not intermediate_sections_path.exists():
            logger.warning(f"No sections found in intermediate report: {report_path.name}")
            continue
            
        # Copy each section from intermediate report to final report
        for section_dir in intermediate_sections_path.iterdir():
            if section_dir.is_dir():
                # Create new section name with ordinal to ensure uniqueness
                new_section_name = f"{section_ordinal:03d}_{section_dir.name.split('_', 1)[-1] if '_' in section_dir.name else section_dir.name}"
                new_section_path = final_sections_path / new_section_name
                
                # Copy the entire section directory
                shutil.copytree(section_dir, new_section_path)
                
                # Update section.json with new ordinal
                section_json_path = new_section_path / "section.json"
                if section_json_path.exists():
                    try:
                        with open(section_json_path, 'r', encoding='utf-8') as f:
                            section_data = json.load(f)
                        
                        section_data['ordinal'] = section_ordinal
                        
                        with open(section_json_path, 'w', encoding='utf-8') as f:
                            json.dump(section_data, f, indent=2)
                            
                        logger.info(f"Consolidated section from {report_path.name}: {new_section_name}")
                    except Exception as e:
                        logger.warning(f"Could not update section.json for {new_section_name}: {e}")
                
                section_ordinal += 1
    
    logger.info(f"Successfully consolidated {section_ordinal} report sections with slicers into final report")
