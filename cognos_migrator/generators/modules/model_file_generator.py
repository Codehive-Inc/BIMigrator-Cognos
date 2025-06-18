"""
Module-specific model file generator for Cognos to Power BI migration
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from ...models import Table, DataModel, PowerBIProject
from ..model_file_generator import ModelFileGenerator

class ModuleModelFileGenerator(ModelFileGenerator):
    """
    Module-specific model file generator for Power BI
    Extends the standard ModelFileGenerator with module-specific functionality
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the module model file generator"""
        super().__init__(template_dir)
        self.logger = logging.getLogger(__name__)
        
    def generate_model_files(self, data_model: DataModel, output_dir: str, 
                           module_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate Power BI model files with module-specific enhancements
        
        Args:
            data_model: Data model to generate files for
            output_dir: Directory to write files to
            module_context: Optional module context information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating module-specific model files in {output_dir}")
            
            # Generate base model files using parent class
            success = super().generate_model_files(data_model, output_dir)
            if not success:
                return False
                
            # Add module-specific enhancements if module context is provided
            if module_context:
                self._enhance_model_with_module_context(output_dir, module_context)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate module-specific model files: {e}")
            return False
            
    def _enhance_model_with_module_context(self, output_dir: str, 
                                         module_context: Dict[str, Any]) -> None:
        """
        Enhance the generated model files with module-specific context
        
        Args:
            output_dir: Directory containing the generated files
            module_context: Module context information
        """
        try:
            # Path to model.bim file
            model_path = Path(output_dir) / "model.bim"
            if not model_path.exists():
                self.logger.warning(f"Model file not found at {model_path}")
                return
                
            # Load the model file
            with open(model_path, "r") as f:
                model_data = json.load(f)
                
            # Add module annotations
            if "annotations" not in model_data:
                model_data["annotations"] = []
                
            # Add module context as annotations
            model_data["annotations"].append({
                "name": "ModuleSource",
                "value": module_context.get("module_name", "Unknown Module")
            })
            
            model_data["annotations"].append({
                "name": "ModuleId",
                "value": module_context.get("module_id", "Unknown")
            })
            
            # Update model name to include module name
            if "name" in model_data and module_context.get("module_name"):
                model_data["name"] = f"{module_context['module_name']} - {model_data['name']}"
                
            # Save enhanced model file
            with open(model_path, "w") as f:
                json.dump(model_data, f, indent=2)
                
            self.logger.info(f"Enhanced model file with module context")
            
        except Exception as e:
            self.logger.error(f"Failed to enhance model with module context: {e}")
        
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None, 
                           data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, 
                           m_query: Optional[str] = None, report_name: Optional[str] = None) -> Dict[str, Any]:
        """Build context for table template with module-specific enhancements"""
        # Get base context from parent class
        context = super()._build_table_context(table, report_spec, data_items, extracted_dir, m_query, report_name)
        
        # Add module-specific metadata to the context
        context['is_module_table'] = True
        
        # Add module source if available
        if hasattr(table, 'module_source'):
            context['module_source'] = table.module_source
            
        # Add module ID if available
        if hasattr(table, 'module_id'):
            context['module_id'] = table.module_id
            
        return context
        
    def _build_m_expression(self, table: Table, report_spec: Optional[str] = None) -> str:
        """
        Build M expression for table with module-specific optimizations
        
        Args:
            table: Table object
            report_spec: Optional report specification
            
        Returns:
            str: M expression for the table
        """
        # Get base M expression from parent class
        m_expression = super()._build_m_expression(table, report_spec)
        
        # Add module-specific optimizations or modifications if needed
        if hasattr(table, 'module_source') and table.module_source:
            # Add module source as metadata in the M query
            module_metadata = f"// Source: Module - {table.module_source}\n"
            m_expression = module_metadata + m_expression
            
        return m_expression
