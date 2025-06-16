"""
Module migration orchestrator for Cognos to Power BI migration
"""

import os
import sys
import json
import logging
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from cognos_migrator.config import ConfigManager, MigrationConfig
from cognos_migrator.extractors.modules import ModuleExtractor, ModuleStructureExtractor, ModuleQueryExtractor, ModuleDataItemExtractor, ModuleExpressionExtractor, ModuleRelationshipExtractor, ModuleHierarchyExtractor
from cognos_migrator.enhancers import CPFMetadataEnhancer
from cognos_migrator.converters import ExpressionConverter
from .client import CognosClient
from .module_parser import CognosModuleParser
from .generators import PowerBIProjectGenerator, DocumentationGenerator
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
        self.project_generator = PowerBIProjectGenerator(config)
        self.doc_generator = DocumentationGenerator(config)
        
        # Initialize LLM service client for expression conversion
        from cognos_migrator.llm_service import LLMServiceClient
        self.llm_service_client = LLMServiceClient()
        
        # Initialize expression converter with LLM service
        self.expression_converter = ExpressionConverter(llm_service_client=self.llm_service_client, logger=self.logger)
        
        # Initialize module extractors
        self.module_structure_extractor = ModuleStructureExtractor(logger=self.logger)
        self.module_query_extractor = ModuleQueryExtractor(logger=self.logger)
        self.module_data_item_extractor = ModuleDataItemExtractor(logger=self.logger)
        self.module_expression_extractor = ModuleExpressionExtractor(llm_client=self.llm_service_client, logger=self.logger)
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
    
    def migrate_module(self, module_id: str, output_path: str) -> bool:
        """Migrate a single Cognos module to Power BI"""
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
            
            # Step 1: Fetch Cognos module
            cognos_module = self.cognos_client.get_module(module_id)
            if not cognos_module:
                self.logger.error(f"Failed to fetch Cognos module: {module_id}")
                return False
            
            # Save raw module data
            module_content = cognos_module.get('content', '')
            if not module_content:
                self.logger.error("Empty module content")
                return False
                
            # Save raw module data to JSON and XML files
            module_metadata_path = extracted_dir / "module_metadata.json"
            with open(module_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(cognos_module.get('content', {}), f, indent=2)
                
            module_spec_path = extracted_dir / "module_specification.xml"
            with open(module_spec_path, 'w', encoding='utf-8') as f:
                f.write(cognos_module.get('specification', ''))
            
            # Step 2: Extract module components using specialized extractors
            # Each extractor will save its output to JSON files in the extracted directory
            self.logger.info("Extracting module structure")
            module_structure = self.module_structure_extractor.extract_and_save(module_content, extracted_dir)
            
            self.logger.info("Extracting query subjects and items")
            query_data = self.module_query_extractor.extract_and_save(module_content, extracted_dir)
            
            self.logger.info("Extracting data items and calculated items")
            data_items = self.module_data_item_extractor.extract_and_save(module_content, extracted_dir)
            
            self.logger.info("Extracting relationships")
            relationships = self.module_relationship_extractor.extract_and_save(module_content, extracted_dir)
            
            self.logger.info("Extracting hierarchies")
            hierarchies = self.module_hierarchy_extractor.extract_and_save(module_content, extracted_dir)
            
            self.logger.info("Extracting and converting expressions")
            expressions = self.module_expression_extractor.extract_and_save(module_content, extracted_dir)
            
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
                'expressions': expressions.get('cognos_expressions', {}),
                'dax_expressions': expressions.get('dax_expressions', {}),
                'raw_module': cognos_module
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
                name=module_name,
                description=f"Migrated from Cognos module: {module_name}",
                source_id=module_id
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
                'migrator_version': '1.0.0'
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
        data_model = DataModel()
        
        # Add tables
        query_subjects = parsed_module.get('query_subjects', [])
        data_items_by_subject = parsed_module.get('data_items', {})
        
        for query_subject in query_subjects:
            subject_id = query_subject.get('identifier', '')
            if not subject_id:
                continue
                
            # Create table
            table = Table(
                name=query_subject.get('label', subject_id) or subject_id,
                source_name=subject_id
            )
            
            # Add columns
            data_items = data_items_by_subject.get(subject_id, [])
            for data_item in data_items:
                # Skip hidden items if configured to do so
                if data_item.get('hidden', False) and self.config.skip_hidden_columns:
                    continue
                    
                column = Column(
                    name=data_item.get('label', '') or data_item.get('identifier', ''),
                    source_name=data_item.get('identifier', ''),
                    data_type=data_item.get('powerbi_datatype', 'String'),
                    format=data_item.get('powerbi_format', ''),
                    description=data_item.get('description', ''),
                    is_hidden=data_item.get('hidden', False)
                )
                table.columns.append(column)
            
            # Add measures from calculated items
            calculated_items_by_subject = parsed_module.get('calculated_items', {})
            dax_expressions_by_subject = parsed_module.get('dax_expressions', {})
            
            calculated_items = calculated_items_by_subject.get(subject_id, [])
            dax_expressions = dax_expressions_by_subject.get(subject_id, {})
            
            for calc_item in calculated_items:
                item_id = calc_item.get('identifier', '')
                if not item_id:
                    continue
                    
                # Get DAX expression if available
                dax_expression = dax_expressions.get(item_id, calc_item.get('expression', ''))
                
                measure = Measure(
                    name=calc_item.get('label', '') or item_id,
                    expression=dax_expression,
                    description=calc_item.get('description', ''),
                    format=self._determine_measure_format(calc_item)
                )
                table.measures.append(measure)
            
            # Add hierarchies
            powerbi_hierarchies_by_table = parsed_module.get('powerbi_hierarchies', {})
            table_hierarchies = powerbi_hierarchies_by_table.get(subject_id, [])
            
            for hierarchy in table_hierarchies:
                table.hierarchies.append(hierarchy)
            
            data_model.tables.append(table)
        
        # Add relationships
        powerbi_relationships = parsed_module.get('powerbi_relationships', [])
        data_model.relationships = powerbi_relationships
        
        return data_model
    
    def _create_report_structure(self, parsed_module: Dict[str, Any], module_name: str) -> Report:
        """Create Power BI report structure from parsed module
        
        Args:
            parsed_module: Parsed module structure
            module_name: Name of the module
            
        Returns:
            Power BI report
        """
        report = Report(
            name=f"{module_name} Report",
            description=f"Report generated from Cognos module: {module_name}"
        )
        
        # Create a default page with tables from the module
        page = ReportPage(
            name="Overview",
            display_name="Overview"
        )
        
        # Add page to report
        report.pages.append(page)
        
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
