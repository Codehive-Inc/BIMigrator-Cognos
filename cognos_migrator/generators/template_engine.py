"""
Template engine for rendering Power BI project templates.
"""
import os
import re
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional
import json

import pybars
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
        self.handlebars_compiler = pybars.Compiler()
        
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
            'database': 'database.tmdl',
            'table': 'Table.tmdl',
            'relationship': 'relationship.tmdl',
            'model': 'model.tmdl',
            'culture': 'culture.tmdl',
            'expressions': 'expressions.tmdl',
            'pbixproj': 'pbixproj.json',
            'report_config': 'report.config.json',
            'report': 'report.json',
            'report_metadata': 'report.metadata.json',
            'report_settings': 'report.settings.json',
            'report_section': 'report.section.json',
            'diagram_layout': 'diagram.layout.json',
            'version': 'version.txt'
        }
        
        # Load each template
        for template_name, file_name in template_files.items():
            template_path = self.template_directory / file_name
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
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the given context"""
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
            
        template = self.templates[template_name]
        
        if template_name == 'table':
            # Use handlebars for table template
            result = template(context)
            return result
        else:
            # Use Jinja2 for other templates
            return self._render_jinja_template(template, context)
    
    def _render_jinja_template(self, template: Template, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with the given context"""
        try:
            # Process context to ensure JSON serializable values for complex structures
            processed_context = {}
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    # Convert to JSON string if needed by the template
                    processed_context[key + '_json'] = json.dumps(value)
                processed_context[key] = value
                
            # Render the template with the processed context
            return template.render(**processed_context)
        except Exception as e:
            self.logger.error(f"Error rendering template: {e}")
            raise
