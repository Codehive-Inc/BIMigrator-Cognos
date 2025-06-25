"""
Module migration orchestrator for Cognos to Power BI migration
"""

import os
import sys
import json
import logging
import shutil
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from cognos_migrator.config import ConfigManager, MigrationConfig, CognosConfig
from cognos_migrator.extractors.modules import ModuleExtractor, ModuleStructureExtractor, ModuleQueryExtractor, ModuleDataItemExtractor, ModuleExpressionExtractor, ModuleRelationshipExtractor, ModuleHierarchyExtractor
from cognos_migrator.extractors.modules.module_source_extractor import ModuleSourceExtractor
from cognos_migrator.enhancers import CPFMetadataEnhancer
from cognos_migrator.converters import ExpressionConverter
from .client import CognosClient, CognosAPIError
from .module_parser import CognosModuleParser
from .generators import PowerBIProjectGenerator, DocumentationGenerator
from .generators.module_generators import ModuleModelFileGenerator
from .models import (
    CognosModule, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage
)
from .cpf_extractor import CPFExtractor
from .common.websocket_client import logging_helper, set_task_info


def test_cognos_connection(cognos_url: str, session_key: str) -> bool:
    """Test connection to Cognos using URL and session key
    
    Args:
        cognos_url: The Cognos base URL
        session_key: The session key to test
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    return CognosClient.test_connection_with_session(cognos_url, session_key)


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
        report_ids: List of report IDs that are associated with this module
        cpf_file_path: Optional path to CPF file for enhanced metadata
        auth_key: The authentication header key (default: IBM-BA-Authorization)
        
    Returns:
        bool: True if migration was successful, False otherwise
        
    Raises:
        CognosAPIError: If session is expired or invalid
    """

        # Generate task_id if not provided
    if task_id is None:
        task_id = f"migration_{uuid.uuid4().hex}"

    # Initialize WebSocket logging with task ID and total steps (12 steps in the migration process)
    set_task_info(task_id, total_steps=12)
    
    # First verify the session is valid
    if not CognosClient.test_connection_with_session(cognos_url, session_key):
        raise CognosAPIError("Session key is expired or invalid")
    
    # Create a minimal config without using environment variables
    from cognos_migrator.config import MigrationConfig, CognosConfig
    
    # Create migration config with explicit values
    migration_config = MigrationConfig(
        output_directory=output_path,
        preserve_structure=True,
        include_metadata=True,
        generate_documentation=True,
        template_directory=str(Path(__file__).parent / "templates"),  # Use relative path
        llm_service_url=None,  # Disable LLM service
        llm_service_enabled=False
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
    
    # Create a minimal migrator without ConfigManager
    logger = logging.getLogger(__name__)
    
    logging_helper(
        message=f"Starting explicit session migration for module: {module_id}",
        progress=0,
        message_type="info"
    )
    
    migrator = CognosModuleMigratorExplicit(
        migration_config=migration_config,
        cognos_config=cognos_config,
        cognos_url=cognos_url,
        session_key=session_key,
        logger=logger,
        cpf_file_path=cpf_file_path
    )
    
    logging_helper(
        message="Migrator initialized successfully",
        progress=10,
        message_type="info"
    )
    
    # Perform the migration
    result = migrator.migrate_module(module_id, output_path, folder_id, cpf_file_path)
    
    if result:
        logging_helper(
            message=f"Module migration completed successfully: {module_id}",
            progress=100,
            message_type="info"
        )
    else:
        logging_helper(
            message=f"Module migration failed: {module_id}",
            progress=100,
            message_type="error"
        )
    
    return result


def post_process_module_with_explicit_session(module_id: str, output_path: str,
                                             cognos_url: str, session_key: str,
                                             successful_report_ids: List[str] = None,
                                             auth_key: str = "IBM-BA-Authorization") -> bool:
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
        
        # Load module information from extracted directory
        output_path = Path(output_path)
        extracted_dir = output_path / "extracted"
        
        logging_helper(
            message="Loading module information from extracted directory",
            progress=20,
            message_type="info"
        )
        
        # Check if module information exists
        module_info_path = extracted_dir / "module_info.json"
        if not module_info_path.exists():
            logger.error(f"Module information not found at {module_info_path}")
            logging_helper(
                message=f"Module information not found at {module_info_path}",
                progress=20,
                message_type="error"
            )
            return False
            
        # Load module information
        with open(module_info_path, "r") as f:
            module_info = json.load(f)
        
        logging_helper(
            message="Module information loaded successfully",
            progress=40,
            message_type="info"
        )
            
        # Generate documentation
        logger.info("Generating module documentation")
        logging_helper(
            message="Generating module documentation",
            progress=60,
            message_type="info"
        )
        docs_dir = output_path / "documentation"
        docs_dir.mkdir(exist_ok=True)
        
        # Create a summary document
        summary_path = docs_dir / "module_summary.md"
        with open(summary_path, "w") as f:
            f.write(f"# Module Migration Summary\n\n")
            f.write(f"## Module Information\n\n")
            f.write(f"- Module ID: {module_id}\n")
            f.write(f"- Module Name: {module_info.get('name', 'Unknown')}\n")
            f.write(f"- Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Migration Results\n\n")
            f.write(f"- Reports Processed: {len(successful_report_ids) if successful_report_ids else 0}\n")
            if successful_report_ids:
                f.write(f"- Successfully Migrated Reports: {len(successful_report_ids)}\n")
                f.write(f"- Report IDs: {', '.join(successful_report_ids)}\n")
        
        logging_helper(
            message=f"Documentation generated successfully at {summary_path}",
            progress=80,
            message_type="info"
        )
                
        logger.info(f"Generated module summary at {summary_path}")
        
        logging_helper(
            message=f"Post-processing completed successfully for module: {module_id}",
            progress=100,
            message_type="info"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error during module post-processing: {e}")
        logging_helper(
            message=f"Post-processing failed: {str(e)}",
            progress=100,
            message_type="error"
        )
        return False


class CognosModuleMigratorExplicit:
    """Migration orchestrator that works with explicit credentials without .env dependencies"""
    
    def __init__(self, migration_config: MigrationConfig, cognos_config: CognosConfig,
                 cognos_url: str, session_key: str, logger=None, cpf_file_path: str = None):
        self.config = migration_config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize client with explicit credentials
        self.cognos_client = CognosClient(cognos_config, base_url=cognos_url, session_key=session_key)
        self.module_parser = CognosModuleParser(client=self.cognos_client)
        
        # Initialize generators without LLM service (since it requires env vars)
        from cognos_migrator.generators.template_engine import TemplateEngine
        template_engine = TemplateEngine(template_directory=migration_config.template_directory)
        
        # Create minimal project generator
        self.project_generator = PowerBIProjectGenerator(migration_config)
        
        # Initialize module-specific model file generator
        if hasattr(self.project_generator, 'model_file_generator'):
            module_model_file_generator = ModuleModelFileGenerator(
                template_engine, 
                mquery_converter=None  # Disable M-query conversion as it may need LLM
            )
            self.project_generator.model_file_generator = module_model_file_generator
            
        self.doc_generator = DocumentationGenerator(migration_config)
        
        # Initialize expression converter without LLM
        self.expression_converter = ExpressionConverter(llm_service_client=None, logger=self.logger)
        
        # Initialize module extractors
        self.module_structure_extractor = ModuleStructureExtractor(logger=self.logger)
        self.module_query_extractor = ModuleQueryExtractor(logger=self.logger)
        self.module_data_item_extractor = ModuleDataItemExtractor(logger=self.logger)
        self.module_expression_extractor = ModuleExpressionExtractor(llm_client=None, logger=self.logger)
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
            # Extract module name from raw module
            raw_module = parsed_module.get('raw_module', {})
            module_name = raw_module.get('name', 'CognosModule')
            module_id = raw_module.get('id', '')
            
            # Create Power BI project
            powerbi_project = PowerBIProject(
                name=module_name
            )
            
            # Create data model
            data_model = self._create_data_model(parsed_module)
            powerbi_project.data_model = data_model
            
            # Create report structure (empty report with tables)
            report = self._create_report_structure(parsed_module, module_name)
            powerbi_project.report = report
            
            # Add migration metadata
            powerbi_project.migration_metadata = {
                'source_type': 'cognos_module',
                'source_id': module_id,
                'source_name': module_name,
                'migration_date': datetime.now().isoformat(),
                'migrator_version': '1.0.0',
                'associated_reports': parsed_module.get('associated_reports', [])
            }
            
            return powerbi_project
            
        except Exception as e:
            self.logger.error(f"Error converting module to Power BI: {e}")
            return None
    
    def _create_data_model(self, parsed_module: Dict[str, Any]) -> DataModel:
        """Create Power BI data model from parsed module
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI data model
        """
        # Extract module name from raw module
        raw_module = parsed_module.get('raw_module', {})
        module_name = raw_module.get('name', 'CognosModule')
        
        # Initialize DataModel with required parameters
        data_model = DataModel(
            name=f"{module_name} Data Model",
            tables=[]
        )
        
        # Add tables
        query_subjects = parsed_module.get('query_subjects', [])
        data_items_by_subject = parsed_module.get('data_items', {})
        
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
                name=rel_dict.get('id', str(uuid.uuid4())),
                from_table=rel_dict.get('from_table', ''),
                from_column=rel_dict.get('from_column', ''),
                to_table=rel_dict.get('to_table', ''),
                to_column=rel_dict.get('to_column', ''),
                cardinality=rel_dict.get('cardinality', 'many'),
                cross_filter_direction=rel_dict.get('cross_filter_behavior', 'OneDirection'),
                is_active=rel_dict.get('is_active', True)
            )
            relationship_objects.append(relationship)
            
        data_model.relationships = relationship_objects
        return data_model
    
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
            name=f"{module_name} Report",
            pages=[]
        )
        
        # Create a basic page showing the tables
        page = ReportPage(
            name="Module Overview",
            visuals=[]
        )
        
        report.pages.append(page)
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
            self._generate_migration_summary(results, output_path)
            
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
    
    def _generate_migration_summary(self, results: Dict[str, bool], output_path: str):
        """Generate migration summary report
        
        Args:
            results: Dictionary mapping report IDs to success status
            output_path: Base output path for the migration
        """
        try:
            summary_path = Path(output_path) / "migration_summary.md"
            
            total_reports = len(results)
            successful_reports = sum(1 for success in results.values() if success)
            failed_reports = total_reports - successful_reports
            
            # Calculate success rate with check for division by zero
            success_rate = 0.0
            if total_reports > 0:
                success_rate = (successful_reports / total_reports) * 100
            
            summary_content = f"""# Migration Summary Report

## Overview
- **Total Reports**: {total_reports}
- **Successful Migrations**: {successful_reports}
- **Failed Migrations**: {failed_reports}
- **Success Rate**: {success_rate:.1f}%

## Migration Results

### Successful Migrations
"""
            
            for report_id, success in results.items():
                if success:
                    summary_content += f"- ✓ {report_id}\n"
            
            summary_content += "\n### Failed Migrations\n"
            
            for report_id, success in results.items():
                if not success:
                    summary_content += f"- ✗ {report_id}\n"
            
            summary_content += f"""
## Migration Details
- **Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Output Directory**: {output_path}

## Next Steps
1. Review failed migrations and check logs for error details
2. Validate successful migrations by opening in Power BI Desktop
3. Test data connections and refresh capabilities
4. Review and adjust visual layouts as needed
"""
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            self.logger.info(f"Generated migration summary: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration summary: {e}")
    
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
            
            # Save raw Cognos report data to extracted folder
            self._save_extracted_report_data(cognos_report, extracted_dir)
            
            # Step 2: Convert to Power BI structures
            powerbi_project = self._convert_cognos_report_to_powerbi(cognos_report)
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
                    # Create table mappings from queries for context
                    table_mappings = {query.get('name', ''): query.get('name', '') for query in queries}
                    
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
    
    def _convert_cognos_report_to_powerbi(self, cognos_report) -> Optional[PowerBIProject]:
        """Convert Cognos report to Power BI project structure
        
        This is adapted from CognosMigrator._convert_cognos_to_powerbi but
        works without environment variable dependencies.
        """
        try:
            from cognos_migrator.report_parser import CognosReportSpecificationParser
            from cognos_migrator.models import ReportPage
            from typing import Optional
            
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
            
            # Create data model
            data_model = self._create_report_data_model(converted_data, cognos_report.name)
            
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
                    table_data = {
                        'name': ds.name,
                        'columns': [],
                        'source_type': ds.source_type if hasattr(ds, 'source_type') else 'Unknown'
                    }
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
            tables.append(table)
        
        # Create relationships (basic implementation)
        relationships = []
        for rel_data in converted_data.get('relationships', []):
            relationship = Relationship(
                from_table=rel_data.get('from_table', ''),
                from_column=rel_data.get('from_column', ''),
                to_table=rel_data.get('to_table', ''),
                to_column=rel_data.get('to_column', ''),
                cardinality=rel_data.get('cardinality', 'OneToMany')
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
        
        return data_model
    
    def _create_report_structure_from_cognos(self, cognos_report, converted_data: Dict[str, Any], data_model: DataModel) -> Report:
        """Create Power BI report structure
        
        Adapted from CognosMigrator._create_report_structure
        """
        # Create basic report page
        page = ReportPage(
            name="Page1",
            display_name="Report Page",
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
        
        report = Report(
            id=getattr(cognos_report, 'id', f"report_{cognos_report.name.lower().replace(' ', '_')}"),
            name=cognos_report.name,
            sections=[page_dict],
            data_model=data_model,
            config={
                "theme": "CorporateTheme",
                "settings": {}
            },
            settings={}
        )
        
        return report
    
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


class CognosModuleMigrator:
    """Main migration orchestrator for Cognos module to Power BI migration"""
    
    def __init__(self, config: MigrationConfig, logger=None, base_url: str = None, session_key: str = None, cpf_file_path: str = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        self.cognos_client = CognosClient(cognos_config, base_url, session_key)
        self.module_parser = CognosModuleParser(client=self.cognos_client)
        
        # Initialize LLM service client for expression conversion and M-query generation
        from cognos_migrator.llm_service import LLMServiceClient
        self.llm_service_client = LLMServiceClient()
        
        # Create a standard PowerBIProjectGenerator
        self.project_generator = PowerBIProjectGenerator(config)
        
        # Replace the standard ModelFileGenerator with the ModuleModelFileGenerator
        # This ensures module-specific enhancements are applied during model file generation
        if hasattr(self.project_generator, 'model_file_generator'):
            # Initialize template engine from the project generator
            template_engine = self.project_generator.template_engine
            # Initialize the module-specific model file generator
            module_model_file_generator = ModuleModelFileGenerator(template_engine, self.project_generator.mquery_converter)
            # Replace the standard model file generator with the module-specific one
            self.project_generator.model_file_generator = module_model_file_generator
            self.logger.info("Using ModuleModelFileGenerator for module migration")
        
        self.doc_generator = DocumentationGenerator(config)
        
        # LLM service client already initialized above
        
        # Initialize expression converter with LLM service
        self.expression_converter = ExpressionConverter(llm_service_client=self.llm_service_client, logger=self.logger)
        
        # Initialize module extractors
        self.module_structure_extractor = ModuleStructureExtractor(logger=self.logger)
        self.module_query_extractor = ModuleQueryExtractor(logger=self.logger)
        self.module_data_item_extractor = ModuleDataItemExtractor(logger=self.logger)
        self.module_expression_extractor = ModuleExpressionExtractor(llm_client=self.llm_service_client, logger=self.logger)
        self.module_source_extractor = ModuleSourceExtractor(logger=self.logger)
        self.module_relationship_extractor = ModuleRelationshipExtractor(logger=self.logger)
        self.module_hierarchy_extractor = ModuleHierarchyExtractor(logger=self.logger)
        
        # Initialize CPF extractor if a CPF file path is provided
        self.cpf_extractor = None
        self.cpf_metadata_enhancer = None
        if cpf_file_path:
            self.cpf_extractor = CPFExtractor(cpf_file_path, logger=self.logger)
            if not self.cpf_extractor.metadata:
                self.logger.warning(f"Failed to load CPF file: {cpf_file_path}")
                self.cpf_extractor = None
            else:
                self.cpf_metadata_enhancer = CPFMetadataEnhancer(self.cpf_extractor, logger=self.logger)
                self.logger.info(f"Successfully loaded CPF file: {cpf_file_path}")
    
    def post_process_module_with_session(self, module_id: str, output_path: str, 
                                       cognos_url: str, session_key: str,
                                       successful_report_ids: List[str] = None) -> bool:
        """Post-process a migrated module with explicit session credentials
        
        Args:
            module_id: ID of the Cognos module to migrate
            output_path: Path where migration output is stored
            cognos_url: The Cognos base URL
            session_key: The session key for authentication
            successful_report_ids: List of successfully migrated report IDs
            
        Returns:
            bool: True if post-processing was successful, False otherwise
            
        Raises:
            CognosAPIError: If session is expired or invalid
        """
        # First verify the session is valid
        if not CognosClient.test_connection(cognos_url, session_key):
            raise CognosAPIError("Session key is expired or invalid")
            
        # Proceed with post-processing using the existing logic
        return self.post_process_module(module_id, output_path, successful_report_ids)
    
    def post_process_module(self, module_id: str, output_path: str, successful_report_ids: List[str] = None) -> bool:
        """Post-process a migrated module with additional information
        
        Args:
            module_id: ID of the Cognos module to migrate
            output_path: Path where migration output is stored
            successful_report_ids: List of successfully migrated report IDs
            
        Returns:
            bool: True if post-processing was successful, False otherwise
        """
        try:
            self.logger.info(f"Post-processing module {module_id} at {output_path}")
            
            # Load module information from extracted directory
            output_path = Path(output_path)
            extracted_dir = output_path / "extracted"
            
            # Check if module information exists
            module_info_path = extracted_dir / "module_info.json"
            if not module_info_path.exists():
                self.logger.error(f"Module information not found at {module_info_path}")
                return False
                
            # Load module information
            with open(module_info_path, "r") as f:
                module_info = json.load(f)
                
            # Generate documentation
            self.logger.info("Generating module documentation")
            docs_dir = output_path / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            # Create a summary document
            summary_path = docs_dir / "module_summary.md"
            with open(summary_path, "w") as f:
                f.write(f"# Module Migration Summary\n\n")
                f.write(f"## Module Information\n\n")
                f.write(f"- Module ID: {module_id}\n")
                f.write(f"- Module Name: {module_info.get('name', 'Unknown')}\n")
                f.write(f"- Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write(f"## Migration Results\n\n")
                f.write(f"- Reports Processed: {len(successful_report_ids) if successful_report_ids else 0}\n")
                if successful_report_ids:
                    f.write(f"- Successfully Migrated Reports: {len(successful_report_ids)}\n")
                    f.write(f"- Report IDs: {', '.join(successful_report_ids)}\n")
                    
            self.logger.info(f"Generated module summary at {summary_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during module post-processing: {e}")
            return False
    
    def migrate_module_with_session(self, module_id: str, output_path: str,
                                  cognos_url: str, session_key: str,
                                  report_ids: List[str] = None) -> bool:
        """Migrate a single Cognos module to Power BI with explicit session credentials
        
        Args:
            module_id: ID of the Cognos module to migrate
            output_path: Path where migration output will be saved
            cognos_url: The Cognos base URL
            session_key: The session key for authentication
            report_ids: List of report IDs that are associated with this module
            
        Returns:
            bool: True if migration was successful, False otherwise
            
        Raises:
            CognosAPIError: If session is expired or invalid
        """
        # First verify the session is valid
        if not CognosClient.test_connection(cognos_url, session_key):
            raise CognosAPIError("Session key is expired or invalid")
            
        # Create a new migrator instance with explicit credentials
        from cognos_migrator.config import ConfigManager, CognosConfig
        config_manager = ConfigManager()
        cognos_config = config_manager.get_cognos_config()
        
        # Create a new client with explicit session
        self.cognos_client = CognosClient(cognos_config, base_url=cognos_url, session_key=session_key)
        self.module_parser = CognosModuleParser(client=self.cognos_client)
        
        # Proceed with migration using the existing logic
        return self.migrate_module(module_id, output_path, report_ids)
    
    def migrate_module(self, module_id: str, output_path: str, report_ids: List[str] = None) -> bool:
        """Migrate a single Cognos module to Power BI
        
        Args:
            module_id (str): ID of the Cognos module to migrate
            output_path (str): Path where migration output will be saved
            report_ids (List[str], optional): List of report IDs that are associated with this module
            
        Returns:
            bool: True if migration was successful, False otherwise
        """
        try:
            self.logger.info(f"Starting migration of module: {module_id}")
            
            # Create output directory structure
            from pathlib import Path
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create extracted directory for raw extracted data
            extracted_dir = output_dir / "extracted"
            extracted_dir.mkdir(exist_ok=True)
            
            # Create pbit directory for pbitools files
            pbit_dir = output_dir / "pbit"
            pbit_dir.mkdir(exist_ok=True)
            
            # Step 1: Fetch Cognos module information
            module_info = self.cognos_client.get_module(module_id)
            if not module_info:
                self.logger.error(f"Failed to fetch Cognos module info: {module_id}")
                return False
                
            # Step 2: Fetch module metadata
            module_metadata = self.cognos_client.get_module_metadata(module_id)
            if not module_metadata:
                self.logger.error(f"Failed to fetch Cognos module metadata: {module_id}")
                return False
            
            # Save module information and metadata
            module_info_path = extracted_dir / "module_info.json"
            with open(module_info_path, 'w', encoding='utf-8') as f:
                json.dump(module_info, f, indent=2)
                
            module_metadata_path = extracted_dir / "module_metadata.json"
            with open(module_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(module_metadata, f, indent=2)
                
            # Save associated report IDs if provided
            if report_ids:
                self.logger.info(f"Associating module with {len(report_ids)} reports: {report_ids}")
                report_ids_path = extracted_dir / "associated_reports.json"
                with open(report_ids_path, 'w', encoding='utf-8') as f:
                    json.dump({"report_ids": report_ids}, f, indent=2)
            
            # Step 3: Extract module components using specialized extractors
            # Each extractor will save its output to JSON files in the extracted directory
            # Convert module_metadata to JSON string for extractors
            module_metadata_json = json.dumps(module_metadata)
            
            self.logger.info("Extracting module structure")
            try:
                module_structure = self.module_structure_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting module structure: {e}")
                module_structure = {}
            
            self.logger.info("Extracting query subjects and items")
            try:
                query_data = self.module_query_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting query subjects: {e}")
                query_data = {}
            
            self.logger.info("Extracting data items and calculated items")
            try:
                data_items = self.module_data_item_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting data items: {e}")
                data_items = {}
            
            self.logger.info("Extracting relationships")
            try:
                relationships = self.module_relationship_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting relationships: {e}")
                relationships = {}
            
            self.logger.info("Extracting hierarchies")
            try:
                hierarchies = self.module_hierarchy_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting hierarchies: {e}")
                hierarchies = {}
                
            self.logger.info("Extracting source data information")
            try:
                source_data = self.module_source_extractor.extract_and_save(module_metadata_json, extracted_dir)
            except Exception as e:
                self.logger.error(f"Error extracting source data: {e}")
                source_data = {}
            
            self.logger.info("Collecting calculations from reports")
            try:
                if report_ids:
                    # Use the new method to collect calculations from reports
                    calculations = self.module_expression_extractor.collect_report_calculations(
                        report_ids, output_path, extracted_dir
                    )
                else:
                    self.logger.warning("No report IDs provided, skipping calculation collection")
                    calculations = {"calculations": []}
            except Exception as e:
                self.logger.error(f"Error collecting calculations from reports: {e}")
                calculations = {"calculations": []}
            
            # Combine all extracted data into a parsed module structure
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
                'associated_reports': report_ids or []
            }
            
            # Save the combined parsed module
            parsed_module_path = extracted_dir / "parsed_module.json"
            with open(parsed_module_path, 'w', encoding='utf-8') as f:
                # Remove raw_module from the saved JSON to avoid duplication
                parsed_module_to_save = {k: v for k, v in parsed_module.items() if k != 'raw_module'}
                json.dump(parsed_module_to_save, f, indent=2)
            
            # Step 3: Convert to Power BI structures
            powerbi_project = self._convert_cognos_to_powerbi(parsed_module)
            if not powerbi_project:
                self.logger.error(f"Failed to convert module: {module_id}")
                return False
            
            # If CPF metadata is available, enhance the Power BI project with it
            if self.cpf_extractor and self.cpf_metadata_enhancer:
                self.cpf_metadata_enhancer.enhance_project(powerbi_project)
            
            # Step 4: Generate Power BI project files
            success = self.project_generator.generate_project(powerbi_project, str(pbit_dir))
            if not success:
                self.logger.error(f"Failed to generate Power BI project files")
                return False
            
            # Step 5: Generate documentation
            self.doc_generator.generate_migration_report(powerbi_project, extracted_dir)
            
            # If CPF metadata is available, save it to the extracted folder
            if self.cpf_extractor:
                cpf_metadata_path = extracted_dir / "cpf_metadata.json"
                self.cpf_extractor.parser.save_metadata_to_json(str(cpf_metadata_path))
                self.logger.info(f"Saved CPF metadata to: {cpf_metadata_path}")
            
            self.logger.info(f"Successfully migrated module {module_id} to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed for module {module_id}: {e}")
            return False

    def _convert_cognos_to_powerbi(self, parsed_module: Dict[str, Any]) -> PowerBIProject:
        """Convert parsed Cognos module to Power BI project
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI project
        """
        try:
            # Extract module name from raw module
            raw_module = parsed_module.get('raw_module', {})
            module_name = raw_module.get('name', 'CognosModule')
            module_id = raw_module.get('id', '')
            
            # Create Power BI project
            powerbi_project = PowerBIProject(
                name=module_name
            )
            
            # We can't store metadata directly in PowerBIProject, so we'll add it to the report metadata
            # when we create the report structure
            
            # Create data model
            data_model = self._create_data_model(parsed_module)
            powerbi_project.data_model = data_model
            
            # Create report structure (empty report with tables)
            report = self._create_report_structure(parsed_module, module_name)
            powerbi_project.report = report
            
            # Add migration metadata
            powerbi_project.migration_metadata = {
                'source_type': 'cognos_module',
                'source_id': module_id,
                'source_name': module_name,
                'migration_date': datetime.now().isoformat(),
                'migrator_version': '1.0.0',
                'associated_reports': parsed_module.get('associated_reports', [])
            }
            
            return powerbi_project
            
        except Exception as e:
            self.logger.error(f"Error converting module to Power BI: {e}")
            return None
    
    def _create_data_model(self, parsed_module: Dict[str, Any]) -> DataModel:
        """Create Power BI data model from parsed module
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI data model
        """
        # Extract module name from raw module
        raw_module = parsed_module.get('raw_module', {})
        module_name = raw_module.get('name', 'CognosModule')
        
        # Initialize DataModel with required parameters
        data_model = DataModel(
            name=f"{module_name} Data Model",
            tables=[]
        )
        
        # Add tables
        query_subjects = parsed_module.get('query_subjects', [])
        data_items_by_subject = parsed_module.get('data_items', {})
        
        for query_subject in query_subjects:
            subject_id = query_subject.get('identifier', '')
            if not subject_id:
                continue
                
            # Create table
            # Use identifier field for table name instead of label for more accurate naming
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
                    
                # Use identifier field for column name instead of label for more accurate naming
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
            
            # Add measures from collected calculations
            calculations = parsed_module.get('calculations', [])
            
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
                name=rel_dict.get('id', str(uuid.uuid4())),  # Use the UUID as the name
                from_table=rel_dict.get('from_table', ''),
                from_column=rel_dict.get('from_column', ''),
                to_table=rel_dict.get('to_table', ''),
                to_column=rel_dict.get('to_column', ''),
                cardinality=rel_dict.get('cardinality', 'many'),  # Use 'many' as default to match TMDL format
                cross_filter_direction=rel_dict.get('cross_filter_behavior', 'OneDirection'),
                is_active=rel_dict.get('is_active', True)
            )
            relationship_objects.append(relationship)
            
        data_model.relationships = relationship_objects
        
        return data_model
    def _create_report_structure(self, parsed_module: Dict[str, Any], module_name: str) -> Report:
        """Create Power BI report structure from parsed module
        
        Args:
            parsed_module: Parsed module structure
            module_name: Name of the module
            
        Returns:
            Power BI report
        """
        # Get module ID from raw module
        raw_module = parsed_module.get('raw_module', {})
        module_id = raw_module.get('id', str(uuid.uuid4()))
        
        report = Report(
            id=f"report_{module_id}",
            name=f"{module_name} Report"
        )
        
        # Store module metadata in report metadata
        report.metadata = {
            "source_module_id": module_id,
            "source_description": f"Report generated from Cognos module: {module_name}"
        }
        
        # Create a default page with tables from the module
        page = ReportPage(
            name="Overview",
            display_name="Overview"
        )
        
        # Add page to report
        report.sections.append(page)
        
        return report
    def _determine_measure_format(self, calc_item: Dict[str, Any]) -> str:
        """Determine the appropriate format for a measure based on its properties
        
        Args:
            calc_item: Calculated item dictionary
            
        Returns:
            Format string for the measure
        """
        # Use the same logic as in ModuleDataItemExtractor.determine_powerbi_format
        datatype = calc_item.get('datatype', '').upper()
        expression = calc_item.get('expression', '').lower()
        
        # Handle numeric formats
        if 'DECIMAL' in datatype or 'NUMERIC' in datatype:
            if 'percent' in expression:
                return '0.00%;-0.00%;0.00%'
            else:
                return '#,0.00;-#,0.00;0.00'
        elif 'INT' in datatype:
            return '#,0;-#,0;0'
        elif 'FLOAT' in datatype or 'DOUBLE' in datatype or 'REAL' in datatype:
            return '#,0.00;-#,0.00;0.00'
        
        # Handle currency
        if any(term in expression for term in ['price', 'cost', 'amount']):
            return '$#,0.00;-$#,0.00;$0.00'
        
        # Default format
        return ''
    
    def _save_extracted_data(self, cognos_module: Dict[str, Any], extracted_dir: Path) -> None:
        """Save extracted module data to files
        
        Args:
            cognos_module: Raw Cognos module data
            extracted_dir: Directory to save extracted data
        """
        try:
            # Save module metadata
            module_metadata_path = extracted_dir / "module_metadata.json"
            with open(module_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(cognos_module.get('content', {}), f, indent=2)
            
            # Save module specification
            module_spec_path = extracted_dir / "module_specification.xml"
            with open(module_spec_path, 'w', encoding='utf-8') as f:
                f.write(cognos_module.get('specification', ''))
            
            self.logger.info(f"Saved extracted module data to: {extracted_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving extracted data: {e}")


# Legacy alias for backward compatibility
CognosToPowerBIModuleMigrator = CognosModuleMigrator
