"""
Module-specific generators for Cognos to Power BI migration
These generators handle module-specific aspects of the migration process
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from ..models import Table, DataModel, PowerBIProject
from .model_file_generator import ModelFileGenerator

class ModuleModelFileGenerator(ModelFileGenerator):
    """
    Module-specific model file generator for Power BI
    Extends the standard ModelFileGenerator with module-specific functionality
    """
    
    def __init__(self, template_engine=None, mquery_converter=None):
        """Initialize the module model file generator
        
        Args:
            template_engine: Template engine for rendering templates
            mquery_converter: Optional MQueryConverter for generating M-queries
        """
        super().__init__(template_engine, mquery_converter)
        self.logger = logging.getLogger(__name__)
        
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None, 
                           data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, 
                           m_query: Optional[str] = None, report_name: Optional[str] = None) -> Dict[str, Any]:
        """Build context for table template with module-specific enhancements"""
        # Get base context from parent class
        context = super()._build_table_context(table, report_spec, data_items, extracted_dir, m_query, report_name)
        
        # Add module-specific metadata to the context
        context['is_module_table'] = True
        
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
        # For now, we're just returning the base expression
        
        return m_expression

class ModuleDocumentationGenerator:
    """
    Generates module-specific documentation for the migration
    """
    
    def __init__(self):
        """Initialize the module documentation generator"""
        self.logger = logging.getLogger(__name__)
        
    def generate_module_documentation(self, module_path: Path, module_info: Dict[str, Any], 
                                    module_metadata: Dict[str, Any]) -> bool:
        """
        Generate module-specific documentation
        
        Args:
            module_path: Path to the module directory
            module_info: Module information
            module_metadata: Module metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            docs_dir = module_path / "documentation"
            docs_dir.mkdir(exist_ok=True)
            
            # Generate module overview
            self._generate_module_overview(docs_dir, module_info, module_metadata)
            
            # Generate data model documentation
            self._generate_data_model_documentation(docs_dir, module_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate module documentation: {e}")
            return False
            
    def _generate_module_overview(self, docs_dir: Path, module_info: Dict[str, Any], 
                                module_metadata: Dict[str, Any]) -> None:
        """Generate module overview documentation"""
        try:
            overview_path = docs_dir / "module_overview.md"
            
            # Extract module information
            module_name = module_info.get('name', 'Unknown Module')
            module_description = module_info.get('description', 'No description available')
            module_id = module_info.get('id', 'Unknown ID')
            
            # Create overview content
            content = f"""# Module: {module_name}

## Overview
- **Module ID**: {module_id}
- **Description**: {module_description}

## Migration Information
- **Migration Date**: {module_metadata.get('migration_date', 'Unknown')}
- **Migration Tool Version**: {module_metadata.get('tool_version', 'Unknown')}

## Module Structure
"""
            
            # Add module structure if available
            if 'structure' in module_metadata:
                content += "### Components\n"
                for component in module_metadata.get('structure', {}).get('components', []):
                    content += f"- {component.get('name', 'Unknown')}\n"
            
            # Write to file
            with open(overview_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate module overview: {e}")
            
    def _generate_data_model_documentation(self, docs_dir: Path, module_path: Path) -> None:
        """Generate data model documentation"""
        try:
            model_doc_path = docs_dir / "data_model.md"
            
            # Look for model information in the module
            model_info = {}
            model_info_path = module_path / "extracted" / "model_info.json"
            
            if model_info_path.exists():
                with open(model_info_path, "r") as f:
                    model_info = json.load(f)
            
            # Create model documentation content
            content = """# Data Model Documentation

## Tables
"""
            
            # Add tables if available
            tables = model_info.get('tables', [])
            if tables:
                for table in tables:
                    table_name = table.get('name', 'Unknown')
                    content += f"### {table_name}\n"
                    
                    # Add columns
                    content += "| Column | Data Type | Description |\n"
                    content += "|--------|-----------|-------------|\n"
                    
                    for column in table.get('columns', []):
                        col_name = column.get('name', 'Unknown')
                        col_type = column.get('datatype', 'Unknown')
                        col_desc = column.get('description', '')
                        content += f"| {col_name} | {col_type} | {col_desc} |\n"
                    
                    content += "\n"
            else:
                content += "*No tables found in the data model*\n"
            
            # Write to file
            with open(model_doc_path, "w") as f:
                f.write(content)
                
        except Exception as e:
            self.logger.error(f"Failed to generate data model documentation: {e}")
