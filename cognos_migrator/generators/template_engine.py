"""
Template engine for rendering Power BI project templates.
"""
import os
import re
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional
import json

from cognos_migrator.utils.json_encoder import ModelJSONEncoder, model_to_dict

from pybars import Compiler
from jinja2 import Environment, FileSystemLoader, Template


class TemplateEngine:
    """Template engine for rendering Power BI project templates"""
    
    def __init__(self, template_directory: str):
        """Initialize template engine with template directory"""
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Template directory passed to TemplateEngine: {template_directory}")
        
        # Convert to Path object for better path handling
        if isinstance(template_directory, str):
            self.template_directory = Path(template_directory)
        else:
            self.template_directory = template_directory
            
        self.logger.info(f"Using template directory: {self.template_directory}")
        
        # Initialize template cache
        self.templates = {}
        self.template_info = {}
        self.handlebars_compiler = Compiler()
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_directory)),
            autoescape=False,  # Don't escape HTML by default
            trim_blocks=True,  # Remove first newline after a block
            lstrip_blocks=True  # Strip tabs and spaces from the beginning of a line to the start of a block
        )
        
        # Add custom filters
        self.jinja_env.filters['safe'] = lambda x: x  # 'safe' filter to prevent escaping
        
        # Load all templates
        self._load_templates()
    
    def _load_templates(self):
        """Load all template files"""
        if not self.template_directory.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_directory}")
        
        # Define which templates use which engine
        handlebars_templates = ['table']
        
        template_files = {
            # Model templates
            'database': {'filename': 'database.tmdl', 'path': 'Model', 'target_filename': 'database.tmdl'},
            'table': {'filename': 'Table.tmdl', 'path': 'Model/tables', 'target_filename': '{table_name}.tmdl'},
            'relationship': {'filename': 'relationship.tmdl', 'path': 'Model', 'target_filename': 'relationships.tmdl'},
            'model': {'filename': 'model.tmdl', 'path': 'Model', 'target_filename': 'model.tmdl'},
            'culture': {'filename': 'culture.tmdl', 'path': 'Model/cultures', 'target_filename': '{culture_name}.tmdl'},
            'expressions': {'filename': 'expressions.tmdl', 'path': 'Model', 'target_filename': 'expressions.tmdl'},
            
            # Project templates
            'pbixproj': {'filename': 'pbixproj.json', 'path': '', 'target_filename': '.pbixproj.json'},
            
            # Report templates
            'report': {'filename': 'report.json', 'path': 'Report', 'target_filename': 'report.json'},
            'report_config': {'filename': 'report.config.json', 'path': 'Report', 'target_filename': 'report.config.json'},  # Legacy name
            'config': {'filename': 'report.config.json', 'path': 'Report', 'target_filename': 'config.json'},  # New name
            'report_metadata': {'filename': 'report.metadata.json', 'path': '', 'target_filename': 'ReportMetadata.json'},
            'report_settings': {'filename': 'report.settings.json', 'path': '', 'target_filename': 'ReportSettings.json'},
            'report_section': {'filename': 'report.section.json', 'path': 'Report/sections', 'target_filename': '{section_id}.json'},
            
            # Slicer visual templates
            'slicer_visual_container': {'filename': 'slicer.visualContainer.json', 'path': 'Report/sections', 'target_filename': 'visualContainer.json'},
            'slicer_config': {'filename': 'slicer.config.json', 'path': 'Report/sections', 'target_filename': 'config.json'},
            'slicer_query': {'filename': 'slicer.query.json', 'path': 'Report/sections', 'target_filename': 'query.json'},
            'slicer_data_transforms': {'filename': 'slicer.dataTransforms.json', 'path': 'Report/sections', 'target_filename': 'dataTransforms.json'},
            
            'diagram_layout': {'filename': 'diagram.layout.json', 'path': '', 'target_filename': 'DiagramLayout.json'},
            
            # Metadata templates
            'version': {'filename': 'version.txt', 'path': '', 'target_filename': 'Version.txt'}
        }
        
        # Load each template
        for template_name, template_info in template_files.items():
            template_path = self.template_directory / template_info['filename']
            if not template_path.exists():
                self.logger.warning(f"Template file not found: {template_path}")
                continue
                
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
            if template_name in handlebars_templates:
                # Compile handlebars template
                self.templates[template_name] = self.handlebars_compiler.compile(template_content)
            else:
                # Compile Jinja2 template
                self.templates[template_name] = self.jinja_env.from_string(template_content)
                
        # Store the template info for later use
        self.template_info = template_files
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a template
        
        Args:
            template_name: Name of the template
            
        Returns:
            Dictionary with template information (filename, path, target_filename)
        """
        if template_name not in self.template_info:
            raise ValueError(f"Template info not found: {template_name}")
            
        return self.template_info[template_name]
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context"""
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
            
        template = self.templates[template_name]
        
        # Debug logging
        self.logger.debug(f"Rendering template: {template_name}")
        self.logger.debug(f"Context keys: {list(context.keys())}")
        
        if template_name == 'table':
            # Use handlebars for table template
            result = template(context)
            return result
        else:
            # Use Jinja2 for other templates
            try:
                return self._render_jinja_template(template, context)
            except Exception as e:
                self.logger.error(f"Error rendering template {template_name}: {e}")
                raise
    
    def _render_jinja_template(self, template: Template, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with the given context"""
        try:
            # Process context to ensure JSON serializable values for complex structures
            processed_context = {}
            
            # First convert any non-serializable objects to dictionaries
            serializable_context = {}
            for key, value in context.items():
                serializable_context[key] = model_to_dict(value)
            
            # Then process for template rendering
            for key, value in serializable_context.items():
                if isinstance(value, (dict, list)):
                    # Convert to JSON string if needed by the template
                    processed_context[key + '_json'] = json.dumps(value, cls=ModelJSONEncoder)
                processed_context[key] = value
                
            # Render the template with the processed context
            return template.render(**processed_context)
        except Exception as e:
            self.logger.error(f"Error rendering template: {e}")
            raise
