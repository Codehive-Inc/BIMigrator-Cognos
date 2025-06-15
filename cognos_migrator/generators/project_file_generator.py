"""
Project file generator for Power BI projects.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from ..models import PowerBIProject
from .template_engine import TemplateEngine


class ProjectFileGenerator:
    """Generator for Power BI project files (.pbixproj.json)"""
    
    def __init__(self, template_engine: TemplateEngine):
        """
        Initialize the project file generator
        
        Args:
            template_engine: Template engine for rendering templates
        """
        self.template_engine = template_engine
        self.logger = logging.getLogger(__name__)
    
    def generate_project_file(self, project: PowerBIProject, output_dir: Path) -> Path:
        """
        Generate .pbixproj.json file
        
        Args:
            project: Power BI project object
            output_dir: Output directory
            
        Returns:
            Path to the generated project file
        """
        # Format datetime with timezone information to match Power BI format
        created_formatted = project.created.strftime('%Y-%m-%dT%H:%M:%S.%f0000+00:00')
        last_modified_formatted = project.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f0000+00:00')
        
        context = {
            'version': project.version,
            'created': created_formatted,
            'last_modified': last_modified_formatted
        }
        
        content = self.template_engine.render('pbixproj', context)
        
        project_file = output_dir / '.pbixproj.json'
        with open(project_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated project file: {project_file}")
        return project_file
