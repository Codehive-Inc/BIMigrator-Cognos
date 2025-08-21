"""
Staging Table Handler - Orchestrator for different staging table approaches.

This module acts as an orchestrator that delegates to specialized handlers based on
the configuration settings for model_handling and data_load_mode.

Supported combinations:
1. star_schema + import
2. star_schema + direct_query  
3. merged_tables + import
4. merged_tables + direct_query
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from cognos_migrator.models import DataModel
from .staging_handlers import StarSchemaHandler, MergedTablesHandler


class StagingTableHandler:
    """
    Orchestrator for staging table processing with different approaches.
    
    This class delegates the actual processing to specialized handlers based on
    the configuration settings.
    """
    
    def __init__(self, settings: Optional[Dict[str, Any]] = None, 
                 extracted_dir: Optional[Path] = None, 
                 mquery_converter: Optional[Any] = None):
        """
        Initialize the staging table handler orchestrator.
        
        Args:
            settings: Optional settings dictionary. If None, will load from settings.json
            extracted_dir: Directory containing extracted files (for SQL relationships)
            mquery_converter: M-query converter instance for generating baseline queries
        """
        self.logger = logging.getLogger(__name__)
        self.extracted_dir = extracted_dir
        self.mquery_converter = mquery_converter
        
        # Load settings if not provided
        if settings is None:
            settings_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / 'settings.json'
            if settings_path.exists():
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                    self.logger.info(f"Loaded settings from {settings_path}")
                except Exception as e:
                    self.logger.warning(f"Error loading settings from {settings_path}: {e}")
                    settings = {}
            else:
                self.logger.warning(f"Settings file not found at {settings_path}")
                settings = {}
        
        # Extract staging table settings
        self.staging_settings = settings.get('staging_tables', {})
        self.enabled = self.staging_settings.get('enabled', False)
        self.naming_prefix = self.staging_settings.get('naming_prefix', 'stg_')
        self.data_load_mode = self.staging_settings.get('data_load_mode', 'import')
        self.model_handling = self.staging_settings.get('model_handling', 'none')
        
        # Log settings
        self.logger.info(f"Staging table settings: enabled={self.enabled}, "
                         f"naming_prefix={self.naming_prefix}, "
                         f"data_load_mode={self.data_load_mode}, "
                         f"model_handling={self.model_handling}")
        
        # Initialize specialized handlers
        self._initialize_handlers()
    
    def _initialize_handlers(self) -> None:
        """Initialize the specialized handlers with common settings."""
        if not self.enabled or self.model_handling == 'none':
            return
        
        handler_settings = {
            'enabled': self.enabled,
            'naming_prefix': self.naming_prefix,
            'data_load_mode': self.data_load_mode,
            'model_handling': self.model_handling
        }
        
        # Initialize handlers
        self.star_schema_handler = StarSchemaHandler(
            settings=handler_settings,
            extracted_dir=self.extracted_dir,
            mquery_converter=self.mquery_converter
        )
        
        self.merged_tables_handler = MergedTablesHandler(
            settings=handler_settings,
            extracted_dir=self.extracted_dir,
            mquery_converter=self.mquery_converter
        )
    
    def process_data_model(self, data_model: DataModel) -> DataModel:
        """
        Process a data model to add staging tables based on settings.
        
        This method acts as an orchestrator, delegating to the appropriate
        specialized handler based on the configuration.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with staging tables added if enabled
        """
        # If staging tables are not enabled or model_handling is 'none', return the original model
        if not self.enabled or self.model_handling == 'none':
            self.logger.info("Staging tables are disabled or set to 'none', returning original model")
            return data_model
        
        self.logger.info(f"Processing data model for staging tables with model_handling={self.model_handling}, "
                         f"data_load_mode={self.data_load_mode}")
        
        # Delegate to appropriate handler based on model_handling and data_load_mode
        try:
            if self.model_handling == 'star_schema':
                return self._process_star_schema(data_model)
            elif self.model_handling == 'merged_tables':
                return self._process_merged_tables(data_model)
            else:
                self.logger.warning(f"Unknown model_handling value: {self.model_handling}, returning original model")
                return data_model
        except Exception as e:
            self.logger.error(f"Error processing data model with {self.model_handling} + {self.data_load_mode}: {e}")
            self.logger.info("Returning original data model due to processing error")
            return data_model
    
    def _process_star_schema(self, data_model: DataModel) -> DataModel:
        """
        Process data model using star schema approach.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with star schema staging tables
        """
        if self.data_load_mode == 'import':
            return self.star_schema_handler.process_import_mode(data_model)
        elif self.data_load_mode == 'direct_query':
            return self.star_schema_handler.process_direct_query_mode(data_model)
        else:
            self.logger.warning(f"Unknown data_load_mode value: {self.data_load_mode}, using import mode")
            return self.star_schema_handler.process_import_mode(data_model)
    
    def _process_merged_tables(self, data_model: DataModel) -> DataModel:
        """
        Process data model using merged tables approach.
        
        Args:
            data_model: The data model to process
            
        Returns:
            The processed data model with merged staging tables
        """
        if self.data_load_mode == 'import':
            return self.merged_tables_handler.process_import_mode(data_model)
        elif self.data_load_mode == 'direct_query':
            return self.merged_tables_handler.process_direct_query_mode(data_model)
        else:
            self.logger.warning(f"Unknown data_load_mode value: {self.data_load_mode}, using import mode")
            return self.merged_tables_handler.process_import_mode(data_model)

