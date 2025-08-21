"""
Cognos Migrator implementation with explicit session credentials

This module provides the CognosModuleMigratorExplicit class that handles
migration of Cognos modules and reports to Power BI without requiring
environment variables or .env files.
"""

import os
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

from cognos_migrator.summary import MigrationSummaryGenerator

from cognos_migrator.config import MigrationConfig, CognosConfig
from cognos_migrator.common.logging import configure_logging, log_info, log_warning, log_error, log_debug
from cognos_migrator.client import CognosClient, CognosAPIError
from cognos_migrator.common.websocket_client import logging_helper, set_task_info
from cognos_migrator.extractors.modules import (
    ModuleStructureExtractor, ModuleQueryExtractor, ModuleDataItemExtractor, 
    ModuleExpressionExtractor, ModuleRelationshipExtractor, ModuleHierarchyExtractor
)
from cognos_migrator.extractors.modules.module_source_extractor import ModuleSourceExtractor
from cognos_migrator.enhancers import CPFMetadataEnhancer
from cognos_migrator.converters import ExpressionConverter, ReportMQueryConverter, PackageMQueryConverter
from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.generators import PowerBIProjectGenerator, DocumentationGenerator
from cognos_migrator.generators.module_generators import ModuleModelFileGenerator
from cognos_migrator.models import (
    PowerBIProject, DataModel, Report, Table, Column, Relationship, 
    Measure, ReportPage
)
from cognos_migrator.cpf_extractor import CPFExtractor
from cognos_migrator.processors.report_model_processor import ReportModelProcessor


class CognosModuleMigratorExplicit:
    """Migration orchestrator that works with explicit credentials without .env dependencies"""
    
    def __init__(self, migration_config: MigrationConfig, cognos_config: CognosConfig,
                 cognos_url: str, session_key: str, logger=None, cpf_file_path: str = None,
                 settings: Optional[Dict[str, Any]] = None):
        self.config = migration_config
        self.logger = logger or logging.getLogger(__name__)
        self.settings = settings  # Store frontend settings
        
        # Initialize client with explicit credentials
        self.cognos_client = CognosClient(cognos_config, base_url=cognos_url, session_key=session_key)
        self.module_parser = CognosModuleParser(client=self.cognos_client)
        
        # Initialize generators with LLM service enabled
        from cognos_migrator.generators.template_engine import TemplateEngine
        from cognos_migrator.llm_service import LLMServiceClient
        from cognos_migrator.converters import ReportMQueryConverter, PackageMQueryConverter
        
        template_engine = TemplateEngine(template_directory=migration_config.template_directory)
        
        # Initialize M-query converters for different migration types
        report_mquery_converter = ReportMQueryConverter()
        package_mquery_converter = PackageMQueryConverter()

        # Initialize LLM service client
        llm_service_client = None
        
        if migration_config.llm_service_enabled and migration_config.llm_service_url:
            try:
                llm_service_client = LLMServiceClient(
                    base_url=migration_config.llm_service_url,
                    api_key=migration_config.llm_service_api_key
                )
                self.logger.info(f"LLM service client initialized with URL: {migration_config.llm_service_url}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM service: {e}")
        
        # Create project generator
        self.project_generator = PowerBIProjectGenerator(migration_config)
        
        # Initialize module-specific model file generator with appropriate M-query converter
        if hasattr(self.project_generator, 'model_file_generator'):
            # We'll set the appropriate converter when we know the migration type
            # Default to report converter for backward compatibility
            module_model_file_generator = ModuleModelFileGenerator(
                template_engine, 
                mquery_converter=report_mquery_converter
            )
            self.project_generator.model_file_generator = module_model_file_generator
            
            # Store both converters for later use based on migration type
            self.report_mquery_converter = report_mquery_converter
            self.package_mquery_converter = package_mquery_converter
            
        self.doc_generator = DocumentationGenerator(migration_config)
        
        # Initialize expression converter with LLM if available
        self.expression_converter = ExpressionConverter(llm_service_client=llm_service_client, logger=self.logger)
        
        # Initialize module extractors
        self.module_structure_extractor = ModuleStructureExtractor(logger=self.logger)
        self.module_query_extractor = ModuleQueryExtractor(logger=self.logger)
        self.module_data_item_extractor = ModuleDataItemExtractor(logger=self.logger)
        self.module_expression_extractor = ModuleExpressionExtractor(llm_client=llm_service_client, logger=self.logger)
        self.module_source_extractor = ModuleSourceExtractor(logger=self.logger)
        self.module_relationship_extractor = ModuleRelationshipExtractor(logger=self.logger)
        self.module_hierarchy_extractor = ModuleHierarchyExtractor(logger=self.logger)
        
        # Initialize CPF extractor if provided
        self.cpf_extractor = None
        self.cpf_metadata_enhancer = None
        if cpf_file_path:
            try:
                self.cpf_extractor = CPFExtractor(cpf_file_path)
                if hasattr(self.cpf_extractor, 'metadata') and self.cpf_extractor.metadata:
                    self.cpf_metadata_enhancer = CPFMetadataEnhancer(self.cpf_extractor, logger=self.logger)
            except Exception as e:
                self.logger.warning(f"Failed to initialize CPF extractor: {e}")
                self.cpf_extractor = None
                
        # Initialize summary generator
        self.summary_generator = MigrationSummaryGenerator(logger=self.logger)
    
    def migrate_module(self, module_id: str, output_path: str, folder_id: str = None, cpf_file_path: str = None) -> bool:
        """Migrate module - uses the same logic as CognosModuleMigrator.migrate_module"""
        # Copy the entire migrate_module method from CognosModuleMigrator
        # This ensures no dependency on environment variables
        try:
            self.logger.info(f"Starting migration of module: {module_id}")
            
            logging_helper(
                message=f"Initializing migration for module: {module_id}",
                progress=15,
                message_type="info"
            )
            
            # Create output directory structure
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            reports_dir = output_dir / "reports"
            reports_dir.mkdir(exist_ok=True)

            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            

            # Migrate reports from folder if folder_id is provided
            successful_report_ids = []
            if folder_id:
                self.logger.info(f"Step 2: Migrating reports from folder {folder_id}")
                folder_results = self.migrate_folder(folder_id, str(reports_dir))
                # Extract report IDs that were successfully migrated
                successful_report_ids = [report_id for report_id, success in folder_results.items() if success]
                self.logger.info(f"Successfully migrated {len(successful_report_ids)} reports: {successful_report_ids}")
            else:
                self.logger.info("No folder ID provided, skipping report migration")


            # Fetch module information
            logging_helper(
                message="Fetching module information from Cognos",
                progress=20,
                message_type="info"
            )
            
            module_info = self.cognos_client.get_module(module_id)
            if not module_info:
                self.logger.error(f"Failed to fetch Cognos module info: {module_id}")
                logging_helper(
                    message=f"Failed to fetch Cognos module info: {module_id}",
                    progress=20,
                    message_type="error"
                )
                return False
                
            # Fetch module metadata
            logging_helper(
                message="Fetching module metadata from Cognos",
                progress=30,
                message_type="info"
            )
            
            module_metadata = self.cognos_client.get_module_metadata(module_id)
            if not module_metadata:
                self.logger.error(f"Failed to fetch Cognos module metadata: {module_id}")
                logging_helper(
                    message=f"Failed to fetch Cognos module metadata: {module_id}",
                    progress=30,
                    message_type="error"
                )
                return False
            
            # Save module information
            with open(extracted_dir / "module_info.json", 'w', encoding='utf-8') as f:
                json.dump(module_info, f, indent=2)
                
            with open(extracted_dir / "module_metadata.json", 'w', encoding='utf-8') as f:
                json.dump(module_metadata, f, indent=2)
                
            if successful_report_ids:
                with open(extracted_dir / "associated_reports.json", 'w', encoding='utf-8') as f:
                    json.dump({"report_ids": successful_report_ids}, f, indent=2)
            
            # Step 3: Extract module components using specialized extractors
            # Each extractor will save its output to JSON files in the extracted directory
            # Convert module_metadata to JSON string for extractors
            logging_helper(
                message="Starting module component extraction",
                progress=40,
                message_type="info"
            )
            
            module_metadata_json = json.dumps(module_metadata)
            
            self.logger.info("Extracting module structure")
            logging_helper(
                message="Extracting module structure",
                progress=45,
                message_type="info"
            )
            try:
                module_structure = self.module_structure_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting module structure: {e}")
                module_structure = {}
            
            self.logger.info("Extracting query subjects and items")
            logging_helper(
                message="Extracting query subjects and items",
                progress=50,
                message_type="info"
            )
            try:
                query_data = self.module_query_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting query subjects: {e}")
                query_data = {}
            
            self.logger.info("Extracting data items and calculated items")
            logging_helper(
                message="Extracting data items and calculated items",
                progress=55,
                message_type="info"
            )
            try:
                data_items = self.module_data_item_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting data items: {e}")
                data_items = {}
            
            self.logger.info("Extracting relationships")
            logging_helper(
                message="Extracting relationships",
                progress=60,
                message_type="info"
            )
            try:
                relationships = self.module_relationship_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting relationships: {e}")
                relationships = {}
            
            self.logger.info("Extracting hierarchies")
            logging_helper(
                message="Extracting hierarchies",
                progress=65,
                message_type="info"
            )
            try:
                hierarchies = self.module_hierarchy_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting hierarchies: {e}")
                hierarchies = {}
                
            self.logger.info("Extracting source data information")
            logging_helper(
                message="Extracting source data information",
                progress=68,
                message_type="info"
            )
            try:
                source_data = self.module_source_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting source data: {e}")
                source_data = {}
            
            self.logger.info("Collecting calculations from reports")
            logging_helper(
                message="Collecting calculations from reports",
                progress=70,
                message_type="info"
            )
            try:
                if successful_report_ids:
                    # Use the new method to collect calculations from reports
                    calculations = self.module_expression_extractor.collect_report_calculations(
                        successful_report_ids, output_path, extracted_dir
                    )
                else:
                    self.logger.warning("No report IDs provided, skipping calculation collection")
                    calculations = {"calculations": []}
            except Exception as e:
                self.logger.error(f"Error collecting calculations from reports: {e}")
                calculations = {"calculations": []}
            
            # Combine all extracted data into a parsed module structure
            logging_helper(
                message="Combining extracted data into parsed module structure",
                progress=75,
                message_type="info"
            )
            parsed_module = {
                'metadata': module_structure,
                'query_subjects': query_data.get('query_subjects', []),
                'query_items': query_data.get('query_items', {}),
                'data_items': data_items.get('data_items', {}),
                'calculated_items': data_items.get('calculated_items', {}),
                'relationships': relationships.get('cognos_relationships', []),
                'powerbi_relationships': relationships.get('powerbi_relationships', []),
                'hierarchies': hierarchies.get('cognos_hierarchies', []),
                'powerbi_hierarchies': hierarchies.get('powerbi_hierarchies', {}),
                'calculations': calculations.get('calculations', []),
                'source_data': source_data.get('sources', []),
                'raw_module': module_info,
                'associated_reports': successful_report_ids or []
            }
            
            # Save the combined parsed module
            parsed_module_path = extracted_dir / "parsed_module.json"
            with open(parsed_module_path, 'w', encoding='utf-8') as f:
                # Remove raw_module from the saved JSON to avoid duplication
                parsed_module_to_save = {k: v for k, v in parsed_module.items() if k != 'raw_module'}
                json.dump(parsed_module_to_save, f, indent=2)
            
            # Step 3: Convert to Power BI structures
            logging_helper(
                message="Converting Cognos module to Power BI structures",
                progress=78,
                message_type="info"
            )
            powerbi_project = self._convert_cognos_to_powerbi(parsed_module)
            if not powerbi_project:
                self.logger.error(f"Failed to convert module: {module_id}")
                logging_helper(
                    message=f"Failed to convert module: {module_id}",
                    progress=78,
                    message_type="error"
                )
                return False
            
            # If CPF metadata is available, enhance the Power BI project with it
            if self.cpf_extractor and self.cpf_metadata_enhancer:
                logging_helper(
                    message="Enhancing project with CPF metadata",
                    progress=82,
                    message_type="info"
                )
                self.cpf_metadata_enhancer.enhance_project(powerbi_project)
            
            # Step 4: Generate Power BI project files
            self.logger.info("Generating Power BI project files")
            logging_helper(
                message="Generating Power BI project files",
                progress=85,
                message_type="info"
            )
            
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                logging_helper(
                    message="Failed to generate Power BI project files",
                    progress=85,
                    message_type="error"
                )
                return False
            
            # Step 5: Generate documentation
            logging_helper(
                message="Generating migration documentation",
                progress=92,
                message_type="info"
            )
            self.doc_generator.generate_migration_report(powerbi_project, extracted_dir)
            
            # If CPF metadata is available, save it to the extracted folder
            if self.cpf_extractor:
                logging_helper(
                    message="Saving CPF metadata",
                    progress=95,
                    message_type="info"
                )
                cpf_metadata_path = extracted_dir / "cpf_metadata.json"
                self.cpf_extractor.parser.save_metadata_to_json(str(cpf_metadata_path))
                self.logger.info(f"Saved CPF metadata to: {cpf_metadata_path}")
            
            self.logger.info(f"Successfully migrated module {module_id} to {output_path}")
            logging_helper(
                message=f"Successfully migrated module {module_id}",
                progress=100,
                message_type="info"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error during module migration: {e}")
            logging_helper(
                message=f"Module migration failed: {str(e)}",
                progress=100,
                message_type="error"
            )
            return False

    def _convert_cognos_to_powerbi(self, parsed_module: Dict[str, Any]) -> PowerBIProject:
        """Convert parsed Cognos module to Power BI project
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI project
        """
        try:
            self.logger.info("Starting conversion to Power BI project")
            
            # Extract module name from raw module
            raw_module = parsed_module.get('raw_module', {})
            module_name = raw_module.get('name', 'CognosModule')
            module_id = raw_module.get('id', '')
            
            self.logger.info(f"Module name: {module_name}, Module ID: {module_id}")
            
            # Create Power BI project
            self.logger.info("Creating Power BI project")
            powerbi_project = PowerBIProject(
                name=module_name
            )
            
            # Create data model
            self.logger.info("Creating data model")
            data_model = self._create_data_model(parsed_module)
            powerbi_project.data_model = data_model
            
            # Create report structure (empty report with tables)
            self.logger.info("Creating report structure")
            report = self._create_report_structure(parsed_module, module_name)
            powerbi_project.report = report
            
            # Add migration metadata
            self.logger.info("Adding migration metadata")
            powerbi_project.migration_metadata = {
                'source_type': 'cognos_module',
                'source_id': module_id,
                'source_name': module_name,
                'migration_date': datetime.now().isoformat(),
                'migrator_version': '1.0.0',
                'associated_reports': parsed_module.get('associated_reports', [])
            }
            
            self.logger.info("Power BI project conversion completed successfully")
            return powerbi_project
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error converting module to Power BI: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            logging_helper(
                message=f"Error in _convert_cognos_to_powerbi: {str(e)}",
                progress=78,
                message_type="error"
            )
            return None
    
    def _create_data_model(self, parsed_module: Dict[str, Any]) -> DataModel:
        """Create Power BI data model from parsed module
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI data model
        """
        try:
            self.logger.info("Starting data model creation")
            
            # Extract module name from raw module
            raw_module = parsed_module.get('raw_module', {})
            module_name = raw_module.get('name', 'CognosModule')
            
            self.logger.info(f"Creating data model for module: {module_name}")
            
            # Initialize DataModel with required parameters
            data_model = DataModel(
                name=f"{module_name} Data Model",
                tables=[]
            )
            
            # Add tables
            query_subjects = parsed_module.get('query_subjects', [])
            data_items_by_subject = parsed_module.get('data_items', {})
            
            self.logger.info(f"Found {len(query_subjects)} query subjects")
            
            for query_subject in query_subjects:
                subject_id = query_subject.get('identifier', '')
                if not subject_id:
                    continue
                    
                # Create table
                table_name = query_subject.get('identifier', subject_id) or subject_id
                table = Table(
                    name=table_name,
                    columns=[]
                )
                
                # Store source ID in annotations
                table.annotations['source_id'] = subject_id
                
                # Add columns
                data_items = data_items_by_subject.get(subject_id, [])
                for data_item in data_items:
                    # Skip hidden items if configured to do so
                    skip_hidden = getattr(self.config, 'skip_hidden_columns', False)
                    if data_item.get('hidden', False) and skip_hidden:
                        continue
                        
                    # Use identifier field for column name
                    column_name = data_item.get('identifier', '') or data_item.get('label', '')
                    source_column = data_item.get('identifier', '')
                    data_type = data_item.get('powerbi_datatype', 'String')
                    
                    column = Column(
                        name=column_name,
                        data_type=data_type,
                        source_column=source_column,
                        description=data_item.get('description', '')
                    )
                    
                    # Store additional metadata in annotations
                    column.annotations['format'] = data_item.get('powerbi_format', '')
                    column.annotations['is_hidden'] = data_item.get('hidden', False)
                    table.columns.append(column)
                
                # Add measures from calculated items
                calculated_items_by_subject = parsed_module.get('calculated_items', {})
                calculated_items = calculated_items_by_subject.get(subject_id, [])
                
                for calc_item in calculated_items:
                    item_id = calc_item.get('identifier', '')
                    if not item_id:
                        continue
                        
                    # Get DAX expression from the calculated item
                    dax_expression = calc_item.get('expression', '')
                    
                    measure = Measure(
                        name=calc_item.get('label', '') or item_id,
                        expression=dax_expression,
                        description=calc_item.get('description', ''),
                        format_string=self._determine_measure_format(calc_item)
                    )
                    table.measures.append(measure)
                
                # Add hierarchies
                powerbi_hierarchies_by_table = parsed_module.get('powerbi_hierarchies', {})
                table_hierarchies = powerbi_hierarchies_by_table.get(subject_id, [])
                
                # Check if table has hierarchies attribute, otherwise store in annotations
                if hasattr(table, 'hierarchies'):
                    for hierarchy in table_hierarchies:
                        table.hierarchies.append(hierarchy)
                else:
                    # Store hierarchies in annotations if attribute is missing
                    if 'hierarchies' not in table.annotations:
                        table.annotations['hierarchies'] = []
                    for hierarchy in table_hierarchies:
                        table.annotations['hierarchies'].append(hierarchy)
                
                data_model.tables.append(table)
            
            # Add relationships
            powerbi_relationships = parsed_module.get('powerbi_relationships', [])
            relationship_objects = []
            
            for rel_dict in powerbi_relationships:
                # Create Relationship object from dictionary
                relationship = Relationship(
                    from_table=rel_dict.get('from_table', ''),
                    from_column=rel_dict.get('from_column', ''),
                    to_table=rel_dict.get('to_table', ''),
                    to_column=rel_dict.get('to_column', ''),
                    id=rel_dict.get('id', str(uuid.uuid4())),
                    from_cardinality=rel_dict.get('cardinality', 'many'),
                    cross_filtering_behavior=rel_dict.get('cross_filter_behavior', 'OneDirection'),
                    is_active=rel_dict.get('is_active', True)
                )
                relationship_objects.append(relationship)
                
            data_model.relationships = relationship_objects
            self.logger.info("Data model creation completed successfully")
            return data_model
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error creating data model: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _create_report_structure(self, parsed_module: Dict[str, Any], module_name: str) -> Report:
        """Create Power BI report structure from parsed module
        
        Args:
            parsed_module: Parsed module structure
            module_name: Name of the module
            
        Returns:
            Power BI report structure
        """
        # Create a basic report structure
        report = Report(
            id=f"report_{module_name.lower().replace(' ', '_')}",
            name=f"{module_name} Report"
        )
        
        # Create a basic page showing the tables
        page = ReportPage(
            name="module_overview",
            display_name="Module Overview",
            visuals=[]
        )
        
        report.sections.append(page)
        return report
    
    def migrate_folder(self, folder_id: str, output_path: str, recursive: bool = True) -> Dict[str, bool]:
        """Migrate all reports in a Cognos folder without using environment variables
        
        Args:
            folder_id: ID of the Cognos folder to migrate
            output_path: Path where migration output will be saved
            recursive: Whether to include reports in subfolders (default: True)
            
        Returns:
            Dict[str, bool]: Dictionary mapping report IDs to migration success status
            
        Raises:
            CognosAPIError: If session is expired or invalid
        """
        results = {}
        
        try:
            self.logger.info(f"Starting migration of folder: {folder_id}")
            
            logging_helper(
                message=f"Fetching reports from folder: {folder_id}",
                progress=70,
                message_type="info"
            )
            
            # Get all reports in folder using the client with explicit session
            reports = self.cognos_client.list_reports_in_folder(folder_id, recursive)
            self.logger.info(f"Found {len(reports)} reports in folder")
            
            if not reports:
                self.logger.warning(f"No reports found in folder: {folder_id}")
                logging_helper(
                    message=f"No reports found in folder: {folder_id}",
                    progress=75,
                    message_type="warning"
                )
                return {}
            
            logging_helper(
                message=f"Starting migration of {len(reports)} reports",
                progress=75,
                message_type="info"
            )
            
            # Calculate progress increment per report
            progress_per_report = 20 / len(reports) if reports else 0
            current_progress = 75
            
            # Migrate each report using the explicit session
            for i, report in enumerate(reports):
                report_output_path = Path(output_path) / f"report_{report.id}"
                self.logger.info(f"Migrating report {i+1}/{len(reports)}: {report.name}")
                
                logging_helper(
                    message=f"Migrating report {i+1}/{len(reports)}: {report.name}",
                    progress=int(current_progress),
                    message_type="info"
                )
                
                try:
                    # Migrate report directly without using CognosMigrator
                    success = self.migrate_report(report.id, str(report_output_path))
                    results[report.id] = success
                    
                    if success:
                        self.logger.info(f"Successfully migrated: {report.name}")
                    else:
                        self.logger.error(f"Failed to migrate: {report.name}")
                        
                except CognosAPIError as e:
                    # Re-raise API errors to propagate session expiry
                    raise e
                except Exception as e:
                    self.logger.error(f"Error migrating report {report.id}: {e}")
                    results[report.id] = False
                
                current_progress += progress_per_report
            
            # Generate migration summary
            self.summary_generator.generate_migration_summary(results, output_path)
            
            logging_helper(
                message=f"Folder migration completed: {sum(1 for s in results.values() if s)}/{len(results)} successful",
                progress=95,
                message_type="info"
            )
            
            return results
            
        except CognosAPIError as e:
            # Re-raise API errors (including session expiry)
            raise e
        except Exception as e:
            self.logger.error(f"Error during folder migration: {e}")
            logging_helper(
                message=f"Error during folder migration: {e}",
                progress=95,
                message_type="error"
            )
            return results
    

    
    def migrate_single_report_with_session_key(self, report_id: str, output_path: str) -> bool:
        """Migrate a single Cognos report using explicit session credentials
        
        This is adapted from migrate_single_report_with_session_key in main.py
        but works without environment variable dependencies.
        
        Args:
            report_id: ID of the Cognos report to migrate
            output_path: Path where migration output will be saved
            
        Returns:
            bool: True if migration was successful, False otherwise
            
        Raises:
            CognosAPIError: If session is expired or invalid
        """
        try:
            self.logger.info(f"Starting migration of report with session key: {report_id}")
            
            # Create output directory structure
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create extracted directory for raw extracted data
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            # Create pbit directory for pbitools files
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Step 1: Fetch Cognos report
            cognos_report = self.cognos_client.get_report(report_id)
            if not cognos_report:
                self.logger.error(f"Failed to fetch Cognos report: {report_id}")
                return False
            
            # Save raw Cognos report data to extracted folder
            self._save_extracted_report_data(cognos_report, extracted_dir)
            
            # Step 2: Convert to Power BI structures
            powerbi_project = self._convert_cognos_report_to_powerbi(cognos_report, extracted_dir)
            if not powerbi_project:
                self.logger.error(f"Failed to convert report: {report_id}")
                return False
            
            # If CPF metadata is available, enhance the Power BI project with it
            if self.cpf_extractor and self.cpf_metadata_enhancer:
                self.cpf_metadata_enhancer.enhance_project(powerbi_project)
            
            # Step 3: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 4: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, extracted_dir)
            
            # If CPF metadata is available, save it to the extracted folder
            if self.cpf_extractor:
                cpf_metadata_path = extracted_dir / "cpf_metadata.json"
                self.cpf_extractor.parser.save_metadata_to_json(str(cpf_metadata_path))
                self.logger.info(f"Saved CPF metadata to: {cpf_metadata_path}")
            
            self.logger.info(f"Successfully migrated report {report_id} to {output_path}")
            return True
            
        except CognosAPIError as e:
            # Re-raise API errors (including session expiry)
            raise e
        except Exception as e:
            self.logger.error(f"Migration failed for report {report_id}: {e}")
            return False

    def migrate_report(self, report_id: str, output_path: str) -> bool:
        """Migrate a single Cognos report to Power BI without using environment variables
        
        Args:
            report_id: ID of the Cognos report to migrate
            output_path: Path where migration output will be saved
            
        Returns:
            bool: True if migration was successful, False otherwise
            
        Raises:
            CognosAPIError: If session is expired or invalid
        """
        try:
            self.logger.info(f"Starting migration of report: {report_id}")
            
            # Create output directory structure
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create extracted directory for raw extracted data
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            # Create pbit directory for pbitools files
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Step 1: Fetch Cognos report
            cognos_report = self.cognos_client.get_report(report_id)
            if not cognos_report:
                self.logger.error(f"Failed to fetch Cognos report: {report_id}")
                return False
            
            # Re-initialize M-query converter with the correct output path using the report-specific converter
            if self.project_generator.model_file_generator:
                # Use the report-specific M-query converter for report migrations
                self.report_mquery_converter = ReportMQueryConverter(output_path=str(output_dir))
                self.project_generator.model_file_generator.mquery_converter = self.report_mquery_converter
                
            # Save raw Cognos report data to extracted folder
            self._save_extracted_report_data(cognos_report, extracted_dir)

            # Step 2: Convert to Power BI structures
            powerbi_project = self._convert_cognos_report_to_powerbi(cognos_report, extracted_dir)
            if not powerbi_project:
                self.logger.error(f"Failed to convert report: {report_id}")
                return False

            # If CPF metadata is available, enhance the Power BI project with it
            if self.cpf_extractor and self.cpf_metadata_enhancer:
                self.cpf_metadata_enhancer.enhance_project(powerbi_project)
            
            # Step 3: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 4: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, extracted_dir)
            
            # If CPF metadata is available, save it to the extracted folder
            if self.cpf_extractor:
                cpf_metadata_path = extracted_dir / "cpf_metadata.json"
                self.cpf_extractor.parser.save_metadata_to_json(str(cpf_metadata_path))
                self.logger.info(f"Saved CPF metadata to: {cpf_metadata_path}")
            
            self.logger.info(f"Successfully migrated report {report_id} to {output_path}")
            return True
            
        except CognosAPIError as e:
            # Re-raise API errors (including session expiry)
            raise e
        except Exception as e:
            self.logger.error(f"Migration failed for report {report_id}: {e}")
            return False
    
    def migrate_report_from_file(self, report_file_path: str, output_path: str) -> bool:
        """Migrate a single Cognos report from a local XML file
        
        Args:
            report_file_path: Path to the local report XML file
            output_path: Path where migration output will be saved
            
        Returns:
            bool: True if migration was successful, False otherwise
        """
        try:
            self.logger.info(f"Starting migration of report from file: {report_file_path}")
            
            # Create output directory structure
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Step 1: Read report specification from the local file
            with open(report_file_path, 'r', encoding='utf-8') as f:
                report_spec = f.read()
            
            # Create a CognosReport object from the file content
            from cognos_migrator.models import CognosReport
            report_name = Path(report_file_path).stem
            cognos_report = CognosReport(
                id=report_name,
                name=report_name,
                specification=report_spec,
                metadata={'name': report_name}
            )
            
            # Re-initialize M-query converter with the correct output path using the report-specific converter
            if self.project_generator.model_file_generator:
                # Use the report-specific M-query converter for report migrations
                self.report_mquery_converter = ReportMQueryConverter(output_path=str(output_dir))
                self.project_generator.model_file_generator.mquery_converter = self.report_mquery_converter
            # Save raw Cognos report data to extracted folder
            self._save_extracted_report_data(cognos_report, extracted_dir)
            
            # Step 2: Convert to Power BI structures
            powerbi_project = self._convert_cognos_report_to_powerbi(cognos_report, extracted_dir)
            if not powerbi_project:
                self.logger.error(f"Failed to convert report from file: {report_file_path}")
                return False
            
            # If CPF metadata is available, enhance the Power BI project with it
            if self.cpf_extractor and self.cpf_metadata_enhancer:
                self.cpf_metadata_enhancer.enhance_project(powerbi_project)
            
            # Step 3: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 4: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, extracted_dir)
            
            self.logger.info(f"Successfully migrated report from file {report_file_path} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed for report file {report_file_path}: {e}")
            return False
    
    def _save_extracted_report_data(self, cognos_report, extracted_dir):
        """Save extracted report data to files for investigation
        
        This is copied from CognosMigrator._save_extracted_data but adapted
        to work without dependencies on environment variables.
        """
        try:
            # Import here to avoid circular imports
            from cognos_migrator.extractors import (
                BaseExtractor, QueryExtractor, DataItemExtractor, 
                ExpressionExtractor, ParameterExtractor, FilterExtractor, 
                LayoutExtractor
            )
            
            # Initialize extractors locally without LLM dependencies
            base_extractor = BaseExtractor(logger=self.logger)
            query_extractor = QueryExtractor(logger=self.logger)
            data_item_extractor = DataItemExtractor(logger=self.logger)
            expression_extractor = ExpressionExtractor(expression_converter=self.expression_converter, logger=self.logger)
            parameter_extractor = ParameterExtractor(logger=self.logger)
            filter_extractor = FilterExtractor(logger=self.logger)
            layout_extractor = LayoutExtractor(logger=self.logger)
            
            # Save raw report specification XML
            spec_path = extracted_dir / "report_specification.xml"
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(cognos_report.specification)
                
            # Save formatted report specification XML for better readability
            try:
                import xml.dom.minidom as minidom
                formatted_spec_path = extracted_dir / "report_specification_formatted.xml"
                # Parse the XML string
                dom = minidom.parseString(cognos_report.specification)
                # Pretty print with 2-space indentation
                formatted_xml = dom.toprettyxml(indent='  ')
                with open(formatted_spec_path, "w", encoding="utf-8") as f:
                    f.write(formatted_xml)
                self.logger.info(f"Saved formatted XML to {formatted_spec_path}")
                
                # Split report specification into layout and query components
                from cognos_migrator.generators.utils import save_split_report_specification
                save_split_report_specification(formatted_spec_path, extracted_dir)
                self.logger.info(f"Split report specification into layout and query components")
            except Exception as e:
                self.logger.warning(f"Failed to save formatted XML: {e}")
            
            # Save report metadata as JSON
            metadata_path = extracted_dir / "report_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(cognos_report.metadata, f, indent=2)
            
            # Save report details as JSON
            details_path = extracted_dir / "report_details.json"
            with open(details_path, "w", encoding="utf-8") as f:
                details = {
                    "id": cognos_report.id,
                    "name": cognos_report.name,
                    "extractionTime": str(datetime.now())
                }
                
                # Add optional attributes if they exist
                if hasattr(cognos_report, 'path'):
                    details["path"] = cognos_report.path
                if hasattr(cognos_report, 'type'):
                    details["type"] = cognos_report.type
                    
                json.dump(details, f, indent=2)
            
            # Save serialized CognosReport object
            report_obj_path = extracted_dir / "cognos_report.json"
            with open(report_obj_path, "w", encoding="utf-8") as f:
                report_dict = {
                    "id": cognos_report.id,
                    "name": cognos_report.name,
                    "data_sources": [ds.__dict__ if hasattr(ds, '__dict__') else str(ds) for ds in cognos_report.data_sources]
                }
                
                # Add optional attributes if they exist
                if hasattr(cognos_report, 'path'):
                    report_dict["path"] = cognos_report.path
                if hasattr(cognos_report, 'type'):
                    report_dict["type"] = cognos_report.type
                    
                json.dump(report_dict, f, indent=2)
            
            # Extract and save additional intermediate files for detailed investigation
            try:
                import xml.etree.ElementTree as ET
                import re
                # Parse the XML for additional extractions
                root = ET.fromstring(cognos_report.specification)
                
                # Register the namespace - Cognos XML uses namespaces
                ns = {}
                if root.tag.startswith('{'):
                    ns_uri = root.tag.split('}')[0].strip('{')
                    ns['ns'] = ns_uri
                    self.logger.info(f"Detected XML namespace: {ns_uri}")
                
                # Extract and save queries
                queries = query_extractor.extract_queries(root, ns)
                queries_path = extracted_dir / "report_queries.json"
                with open(queries_path, "w", encoding="utf-8") as f:
                    json.dump(queries, f, indent=2)
                
                # Extract and save data items/columns
                data_items = data_item_extractor.extract_data_items(root, ns)
                data_items_path = extracted_dir / "report_data_items.json"
                with open(data_items_path, "w", encoding="utf-8") as f:
                    json.dump(data_items, f, indent=2)
                
                # Extract and save expressions
                expressions = expression_extractor.extract_expressions(root, ns)
                
                # Convert expressions to DAX if expression converter is available
                if self.expression_converter:
                    self.logger.info("Converting Cognos expressions to DAX")
                    
                    # Create table mappings from data items for context
                    table_mappings = {}
                    for item in data_items:
                        name = item.get('name')
                        table_name = item.get('table_name')
                        query_name = item.get('queryName')
                        if name and table_name:
                            table_mappings[name] = table_name
                        if query_name and table_name:
                            table_mappings[query_name] = table_name
                    
                    # Add a mapping for the default 'Data' table to use the report name
                    if cognos_report.name:
                        # Create a safe report name
                        safe_table_name = re.sub(r'[^\w\s]', '', cognos_report.name).replace(' ', '_')
                        self.logger.info(f"Adding table mapping: Data -> {safe_table_name}")
                        table_mappings['Data'] = safe_table_name
                    
                    calculations = expression_extractor.convert_to_dax(expressions, table_mappings)
                    self.logger.info(f"Converted {len(calculations['calculations'])} expressions to DAX")
                else:
                    # Create empty calculations structure if no converter is available
                    calculations = {"calculations": []}
                
                # Save calculations in the Cognos format
                calculations_path = extracted_dir / "calculations.json"
                with open(calculations_path, "w", encoding="utf-8") as f:
                    json.dump(calculations, f, indent=2, ensure_ascii=False)
                
                # Extract and save parameters
                parameters = parameter_extractor.extract_parameters(root, ns)
                parameters_path = extracted_dir / "report_parameters.json"
                with open(parameters_path, "w", encoding="utf-8") as f:
                    json.dump(parameters, f, indent=2)
                
                # Extract and save filters
                filters = filter_extractor.extract_filters(root, ns)
                filters_path = extracted_dir / "report_filters.json"
                with open(filters_path, "w", encoding="utf-8") as f:
                    json.dump(filters, f, indent=2)
                
                # Extract and save layout
                layout = layout_extractor.extract_layout(root, ns)
                layout_path = extracted_dir / "report_layout.json"
                with open(layout_path, "w", encoding="utf-8") as f:
                    json.dump(layout, f, indent=2)
                
                self.logger.info(f"Saved additional extracted data files to {extracted_dir}")
                
            except Exception as e:
                self.logger.warning(f"Could not extract additional data from XML: {e}")
            
            self.logger.info(f"Saved extracted Cognos report data to {extracted_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to save extracted data: {e}")
    
    def _create_data_model_from_report(self, extracted_dir: Path) -> Optional[DataModel]:
        """Create a DataModel from the extracted report queries."""
        try:
            self.logger.info(f"Creating DataModel from report queries in {extracted_dir}")
            processor = ReportModelProcessor(extracted_dir)
            data_model = processor.process()
            self.logger.info(f"Successfully created DataModel with {len(data_model.tables)} tables.")
            return data_model
        except Exception as e:
            self.logger.error(f"Failed to create DataModel from report: {e}")
            return None

    def _convert_cognos_report_to_powerbi(self, cognos_report, extracted_dir: Path) -> Optional[PowerBIProject]:
        """Convert Cognos report to Power BI project structure
        
        This is adapted from CognosMigrator._convert_cognos_to_powerbi but
        works without environment variable dependencies.
        """
        try:
            from cognos_migrator.report_parser import CognosReportSpecificationParser
            from cognos_migrator.models import ReportPage
            from typing import Optional
            import re
            
            # Initialize report parser
            report_parser = CognosReportSpecificationParser()
            
            # Parse report specification
            parsed_structure = report_parser.parse_report_specification(
                cognos_report.specification, 
                cognos_report.metadata
            )
            
            # Prepare safe table name once - replace spaces with underscores and remove special characters
            safe_table_name = re.sub(r'[^\w\s]', '', cognos_report.name).replace(' ', '_')
            self.logger.info(f"Using report name '{cognos_report.name}' (sanitized as '{safe_table_name}') for table name")
            
            # Convert parsed structure to migration data
            converted_data = self._convert_parsed_structure(parsed_structure, safe_table_name)
            
            # Create data model from report queries
            data_model = self._create_data_model_from_report(extracted_dir)
            if not data_model:
                self.logger.error("Failed to create data model from report, aborting conversion.")
                return None
            
            # Create report structure
            report = self._create_report_structure_from_cognos(cognos_report, converted_data, data_model)
            
            # Create Power BI project
            project = PowerBIProject(
                name=cognos_report.name,
                version="1.0",  # Match the version format in example files
                created=datetime.now(),
                last_modified=datetime.now(),
                data_model=data_model,
                report=report
            )
            
            # Final check to ensure all tables in the project have deduplicated columns
            self.logger.info("Performing final project-level deduplication check on all tables")
            for table in project.data_model.tables:
                self.logger.info(f"Project-level deduplication check for table: {table.name}")
                # Count columns before deduplication
                before_count = len(table.columns)
                # Apply deduplication again
                self._deduplicate_columns(table)
                # Count columns after deduplication
                after_count = len(table.columns)
                if before_count != after_count:
                    self.logger.warning(f"Project-level deduplication removed {before_count - after_count} columns from {table.name} that were missed in earlier deduplication")
            
            return project
            
        except Exception as e:
            self.logger.error(f"Failed to convert Cognos report to Power BI: {e}")
            return None
    
    def _convert_parsed_structure(self, parsed_structure, safe_table_name: str) -> Dict[str, Any]:
        """Convert parsed Cognos structure to migration data format
        
        Copied from CognosMigrator._convert_parsed_structure
        """
        try:
            # Extract basic information
            converted_data = {
                'tables': [],
                'relationships': [],
                'measures': [],
                'filters': [],
                'visuals': [],
                'pages': []
            }
            
            # Convert pages if available
            if hasattr(parsed_structure, 'pages') and parsed_structure.pages:
                for page in parsed_structure.pages:
                    page_data = {
                        'name': page.name,
                        'visuals': []
                    }
                    
                    # Convert visuals if available
                    if hasattr(page, 'visuals') and page.visuals:
                        for visual in page.visuals:
                            visual_data = {
                                'name': visual.name,
                                'type': visual.cognos_type,
                                'powerbi_type': visual.power_bi_type.value if visual.power_bi_type else 'textbox',
                                'position': visual.position,
                                'fields': []
                            }
                            
                            # Convert fields if available
                            if hasattr(visual, 'fields') and visual.fields:
                                for field in visual.fields:
                                    field_data = {
                                        'name': field.name,
                                        'source_table': field.source_table,
                                        'data_role': field.data_role,
                                        'aggregation': field.aggregation
                                    }
                                    visual_data['fields'].append(field_data)
                            
                            page_data['visuals'].append(visual_data)
                    
                    converted_data['pages'].append(page_data)
            
            # Convert data sources to tables
            if hasattr(parsed_structure, 'data_sources') and parsed_structure.data_sources:
                for ds in parsed_structure.data_sources:
                    # Track column names to prevent duplicates at the source
                    column_names_set = set()
                    
                    table_data = {
                        'name': ds.name,
                        'columns': [],
                        'source_type': ds.source_type if hasattr(ds, 'source_type') else 'Unknown'
                    }
                    
                    # If the data source has columns, process them with deduplication
                    if hasattr(ds, 'columns') and ds.columns:
                        self.logger.info(f"Processing columns for data source {ds.name}")
                        for col in ds.columns:
                            col_name = col.name if hasattr(col, 'name') else 'Column'
                            col_name_lower = col_name.lower()
                            
                            # Only add the column if its name (case-insensitive) hasn't been seen before
                            if col_name_lower not in column_names_set:
                                column_names_set.add(col_name_lower)
                                col_data = {
                                    'name': col_name,
                                    'type': col.data_type if hasattr(col, 'data_type') else 'Text'
                                }
                                table_data['columns'].append(col_data)
                            else:
                                self.logger.info(f"Skipping duplicate column {col_name} in data source {ds.name}")
                    
                    converted_data['tables'].append(table_data)
            
            # If no specific structure, create basic defaults
            if not converted_data['tables']:
                # Use the safe_table_name that was passed in
                self.logger.info(f"Using safe table name '{safe_table_name}' for default table")
                
                converted_data['tables'].append({
                    'name': safe_table_name,
                    'columns': [
                        {'name': 'ID', 'type': 'Int64'},
                        {'name': 'Name', 'type': 'Text'},
                        {'name': 'Value', 'type': 'Decimal'}
                    ],
                    'source_type': 'Cognos'
                })
            
            # Add the parsed structure so it can be used by _create_report_structure_from_cognos
            converted_data['parsed_structure'] = parsed_structure
            
            return converted_data
            
        except Exception as e:
            self.logger.warning(f"Error converting parsed structure: {e}")
            # Return minimal structure as fallback
            # Use the safe_table_name that was passed in
            self.logger.warning(f"Using safe table name '{safe_table_name}' for fallback table")
            
            return {
                'tables': [{
                    'name': safe_table_name,
                    'columns': [
                        {'name': 'ID', 'type': 'Int64'},
                        {'name': 'Value', 'type': 'Decimal'}
                    ],
                    'source_type': 'Cognos'
                }],
                'relationships': [],
                'measures': [],
                'filters': [],
                'visuals': [],
                'pages': []
            }
    
    def _create_report_data_model(self, converted_data: Dict[str, Any], model_name: str) -> DataModel:
        """Create Power BI data model from converted data
        
        Adapted from CognosMigrator._create_data_model
        """
        from cognos_migrator.models import Table, Column, Relationship, Measure, DataType
        
        # Create tables from converted data
        tables = []
        for table_data in converted_data.get('tables', []):
            # Create columns
            columns = []
            for col_data in table_data.get('columns', []):
                column = Column(
                    name=col_data.get('name', 'Column'),
                    data_type=DataType.STRING if col_data.get('type') == 'Text' else DataType.INTEGER,
                    source_column=col_data.get('name', 'Column'),
                    format_string=col_data.get('format_string')
                )
                columns.append(column)
            
            # Create table
            table = Table(
                name=table_data.get('name', 'Table'),
                columns=columns,
                source_query=""  # Empty source query - no placeholder needed
            )
            
            # Deduplicate columns in the table by name
            self._deduplicate_columns(table)
            
            tables.append(table)
        
        # Create relationships (basic implementation)
        relationships = []
        for rel_data in converted_data.get('relationships', []):
            relationship = Relationship(
                from_table=rel_data.get('from_table', ''),
                from_column=rel_data.get('from_column', ''),
                to_table=rel_data.get('to_table', ''),
                to_column=rel_data.get('to_column', ''),
                from_cardinality=rel_data.get('cardinality', 'OneToMany')
            )
            relationships.append(relationship)
        
        # Create measures
        measures = []
        for measure_data in converted_data.get('measures', []):
            measure = Measure(
                name=measure_data.get('name', 'Measure'),
                expression=measure_data.get('expression', 'SUM(Table[Column])'),
                format_string=measure_data.get('format_string'),
                description=measure_data.get('description')
            )
            measures.append(measure)
        
        data_model = DataModel(
            name=model_name,
            compatibility_level=1567,  # Match example file compatibility level
            culture="en-US",
            tables=tables,
            relationships=relationships,
            measures=measures,
            annotations={
                "PBI_QueryOrder": "[\"Query1\"]",
                "PBIDesktopVersion": "2.142.928.0 (25.04)+de52df9f0bb74ad93a80d89c52d63fe6d07e0e1b",
                "__PBI_TimeIntelligenceEnabled": "0"
            }
        )
        
        # Final check to ensure all tables have deduplicated columns
        self.logger.info("Performing final deduplication check on all tables")
        for table in data_model.tables:
            self.logger.info(f"Final deduplication check for table: {table.name}")
            # Count columns before deduplication
            before_count = len(table.columns)
            # Apply deduplication again
            self._deduplicate_columns(table)
            # Count columns after deduplication
            after_count = len(table.columns)
            if before_count != after_count:
                self.logger.warning(f"Final deduplication removed {before_count - after_count} columns from {table.name} that were missed in earlier deduplication")
        
        return data_model
    
    def _create_report_structure_from_cognos(self, cognos_report, converted_data: Dict[str, Any], data_model: DataModel) -> Report:
        """Create Power BI report structure
        
        Adapted from CognosMigrator._create_report_structure but enhanced to use parsed report structure
        """
        # Get parsed report structure if available
        parsed_structure = converted_data.get('parsed_structure')
        pages_list = []
        
        if parsed_structure and hasattr(parsed_structure, 'pages') and parsed_structure.pages:
            # Use parsed pages from enhanced parser
            for page in parsed_structure.pages:
                page_dict = {
                    'name': page.name,
                    'display_name': page.display_name,
                    'width': page.width,
                    'height': page.height,
                    'visuals': page.visuals or [],
                    'filters': page.filters or [],
                    'config': getattr(page, 'config', {}),
                    'header': getattr(page, 'header', None)
                }
                pages_list.append(page_dict)
        else:
            # Fallback: Create basic report page
            page = ReportPage(
                name="Page1",
                display_name=f"{cognos_report.name} - Page1",
                width=1280,
                height=720,
                visuals=[],  # Would be populated with actual visuals
                filters=converted_data.get('filters', []),
                config={}
            )
            
            # Convert ReportPage to dictionary to make it JSON serializable
            page_dict = {
                'name': page.name,
                'display_name': page.display_name,
                'width': page.width,
                'height': page.height,
                'visuals': page.visuals,
                'filters': page.filters,
                'config': page.config
            }
            pages_list.append(page_dict)
        
        report = Report(
            id=getattr(cognos_report, 'id', f"report_{cognos_report.name.lower().replace(' ', '_')}"),
            name=cognos_report.name,
            sections=pages_list,
            data_model=data_model,
            config={
                "theme": "CorporateTheme",
                "settings": {}
            },
            settings={}
        )
        
        return report
    
    def _deduplicate_columns(self, table: Table) -> None:
        """Deduplicate columns in a table by name
        
        Args:
            table: Table to deduplicate columns in
        """
        # Log all column names before deduplication
        self.logger.info(f"Before deduplication - Table {table.name} has {len(table.columns)} columns")
        column_names = [col.name for col in table.columns]
        self.logger.info(f"Column names: {column_names}")
        
        # Create a dictionary to track unique columns by name (case-insensitive)
        unique_columns = {}
        duplicates = []
        
        # Identify unique columns (keeping the first occurrence)
        for col in table.columns:
            col_name_lower = col.name.lower()
            if col_name_lower not in unique_columns:
                unique_columns[col_name_lower] = col
            else:
                duplicates.append(col.name)
        
        duplicate_count = len(duplicates)
        
        if duplicate_count > 0:
            self.logger.info(f"Deduplicating columns in table {table.name}: found {duplicate_count} duplicate columns")
            self.logger.info(f"Duplicate column names: {duplicates}")
            # Replace the columns list with the deduplicated list
            table.columns = list(unique_columns.values())
            
            # Log the column names after deduplication
            after_column_names = [col.name for col in table.columns]
            self.logger.info(f"After deduplication - Table {table.name} has {len(table.columns)} columns")
            self.logger.info(f"Column names after deduplication: {after_column_names}")
        else:
            self.logger.info(f"No duplicate columns found in table {table.name}")
    
    def _determine_measure_format(self, calc_item: Dict[str, Any]) -> str:
        """Determine format string for a measure
        
        Args:
            calc_item: Calculated item data
            
        Returns:
            Format string for the measure
        """
        # Basic format determination logic
        format_hint = calc_item.get('powerbi_format', '')
        if format_hint:
            return format_hint
            
        # Default to general format
        return "0"