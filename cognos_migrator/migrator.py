"""
Cognos Migrator implementation with explicit session credentials

This module provides the CognosModuleMigratorExplicit class that handles
migration of Cognos modules and reports to Power BI without requiring
environment variables or .env files.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

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
from cognos_migrator.converters import ExpressionConverter
from cognos_migrator.module_parser import CognosModuleParser
from cognos_migrator.generators import PowerBIProjectGenerator, DocumentationGenerator
from cognos_migrator.generators.module_generators import ModuleModelFileGenerator
from cognos_migrator.models import (
    PowerBIProject, DataModel, Report, Table, Column, Relationship, 
    Measure, ReportPage
)
from cognos_migrator.cpf_extractor import CPFExtractor


class CognosModuleMigratorExplicit:
    """Migration orchestrator that works with explicit credentials without .env dependencies"""
    
    def __init__(self, migration_config: MigrationConfig, cognos_config: CognosConfig,
                 cognos_url: str, session_key: str, logger=None, cpf_file_path: str = None):
        """Initialize the migrator with explicit credentials
        
        Args:
            migration_config: Configuration for migration options
            cognos_config: Configuration for Cognos API
            cognos_url: The Cognos base URL
            session_key: The session key for authentication
            logger: Optional logger instance
            cpf_file_path: Optional path to CPF file for enhanced metadata
        """
        self.config = migration_config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize client with explicit credentials
        self.cognos_client = CognosClient(cognos_config, base_url=cognos_url, session_key=session_key)
        self.module_parser = CognosModuleParser(client=self.cognos_client)
        
        # Initialize generators with LLM service enabled
        from cognos_migrator.generators.template_engine import TemplateEngine
        from cognos_migrator.llm_service import LLMServiceClient
        from cognos_migrator.converters import MQueryConverter
        
        template_engine = TemplateEngine(template_directory=migration_config.template_directory)
        
        # Initialize LLM service client and M-query converter
        llm_service_client = None
        mquery_converter = None
        
        if migration_config.llm_service_enabled and migration_config.llm_service_url:
            try:
                llm_service_client = LLMServiceClient(
                    base_url=migration_config.llm_service_url,
                    api_key=migration_config.llm_service_api_key
                )
                mquery_converter = MQueryConverter(llm_service_client)
                self.logger.info(f"LLM service client initialized with URL: {migration_config.llm_service_url}")
                self.logger.info("M-query converter initialized with LLM service")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM service: {e}")
                self.logger.warning("Proceeding without M-query conversion")
        
        # Create project generator
        self.project_generator = PowerBIProjectGenerator(migration_config)
        
        # Initialize module-specific model file generator with M-query converter
        if hasattr(self.project_generator, 'model_file_generator'):
            module_model_file_generator = ModuleModelFileGenerator(
                template_engine, 
                mquery_converter=mquery_converter
            )
            self.project_generator.model_file_generator = module_model_file_generator
            
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
    
    def migrate_module(self, module_id: str, output_path: str, folder_id: str = None, cpf_file_path: str = None) -> bool:
        """Migrate module - uses the same logic as CognosModuleMigrator.migrate_module
        
        Args:
            module_id: ID of the Cognos module to migrate
            output_path: Path where migration output will be saved
            folder_id: Optional folder ID containing reports to migrate
            cpf_file_path: Optional path to CPF file for enhanced metadata
            
        Returns:
            bool: True if migration was successful, False otherwise
        """
        # Implementation will be moved from main.py
        pass
    
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
        # Implementation will be moved from main.py
        pass
    
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
        # Implementation will be moved from main.py
        pass
    
    def _convert_cognos_to_powerbi(self, parsed_module: Dict[str, Any]) -> PowerBIProject:
        """Convert parsed Cognos module to Power BI project
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI project
        """
        # Implementation will be moved from main.py
        pass
    
    def _create_data_model(self, parsed_module: Dict[str, Any]) -> DataModel:
        """Create Power BI data model from parsed module
        
        Args:
            parsed_module: Parsed module structure
            
        Returns:
            Power BI data model
        """
        # Implementation will be moved from main.py
        pass
    
    def _create_report_structure(self, parsed_module: Dict[str, Any], module_name: str) -> Report:
        """Create Power BI report structure from parsed module
        
        Args:
            parsed_module: Parsed module structure
            module_name: Name of the module
            
        Returns:
            Power BI report structure
        """
        # Implementation will be moved from main.py
        pass
    
    def _generate_migration_summary(self, results: Dict[str, bool], output_path: str) -> None:
        """Generate migration summary report
        
        Args:
            results: Dictionary mapping report IDs to success status
            output_path: Base output path for the migration
        """
        # Implementation will be moved from main.py
        pass
    
    def _save_extracted_report_data(self, cognos_report, extracted_dir) -> None:
        """Save extracted report data to files for investigation
        
        This is copied from CognosMigrator._save_extracted_data but adapted
        to work without dependencies on environment variables.
        """
        # Implementation will be moved from main.py
        pass
    
    def _convert_cognos_report_to_powerbi(self, cognos_report) -> PowerBIProject:
        """Convert Cognos report to Power BI project structure
        
        This is adapted from CognosMigrator._convert_cognos_to_powerbi but
        works without environment variable dependencies.
        """
        # Implementation will be moved from main.py
        pass
    
    def _convert_parsed_structure(self, parsed_structure, safe_table_name: str) -> Dict[str, Any]:
        """Convert parsed Cognos structure to migration data format
        
        Copied from CognosMigrator._convert_parsed_structure
        """
        # Implementation will be moved from main.py
        pass
    
    def _create_report_data_model(self, converted_data: Dict[str, Any], model_name: str) -> DataModel:
        """Create Power BI data model from converted data
        
        Adapted from CognosMigrator._create_data_model
        """
        # Implementation will be moved from main.py
        pass
    
    def _create_report_structure_from_cognos(self, cognos_report, converted_data: Dict[str, Any], data_model: DataModel) -> Report:
        """Create Power BI report structure
        
        Adapted from CognosMigrator._create_report_structure
        """
        # Implementation will be moved from main.py
        pass
    
    def _determine_measure_format(self, calc_item: Dict[str, Any]) -> str:
        """Determine format string for a measure
        
        Args:
            calc_item: Calculated item data
            
        Returns:
            Format string for the measure
        """
        # Implementation will be moved from main.py
        pass
