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

from cognos_migrator.config import ConfigManager, MigrationConfig
from cognos_migrator.extractors.modules import ModuleExtractor, ModuleStructureExtractor, ModuleQueryExtractor, ModuleDataItemExtractor, ModuleExpressionExtractor, ModuleRelationshipExtractor, ModuleHierarchyExtractor
from cognos_migrator.extractors.modules.module_source_extractor import ModuleSourceExtractor
from cognos_migrator.enhancers import CPFMetadataEnhancer
from cognos_migrator.converters import ExpressionConverter
from .client import CognosClient
from .module_parser import CognosModuleParser
from .generators import PowerBIProjectGenerator, DocumentationGenerator
from .generators.module_generators import ModuleModelFileGenerator
from .models import (
    CognosModule, PowerBIProject, DataModel, Report, 
    Table, Column, Relationship, Measure, ReportPage
)
from .cpf_extractor import CPFExtractor


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
