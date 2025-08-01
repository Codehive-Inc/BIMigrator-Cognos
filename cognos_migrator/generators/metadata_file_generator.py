"""
Metadata file generator for Power BI projects.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from cognos_migrator.common.websocket_client import logging_helper

from ..models import PowerBIProject
from .template_engine import TemplateEngine


class MetadataFileGenerator:
    """Generator for Power BI metadata files (version.txt)"""
    
    def __init__(self, template_engine: TemplateEngine):
        """
        Initialize the metadata file generator
        
        Args:
            template_engine: Template engine for rendering templates
        """
        self.template_engine = template_engine
        self.logger = logging.getLogger(__name__)
    
    def generate_metadata_files(self, project: PowerBIProject, output_dir: Path) -> Path:
        """
        Generate metadata files
        
        Args:
            project: Power BI project object
            output_dir: Output directory
            
        Returns:
            Path to the metadata directory
        """
        # Generate version.txt
        self._generate_version_file(project, output_dir)
        
        self.logger.info(f"Generated metadata files in: {output_dir}")
        return output_dir
    
    def _generate_version_file(self, project: PowerBIProject, output_dir: Path):
        """Generate version.txt file"""
        context = {
            'version': project.version
        }
        
        # Get template info to determine the target filename and path
        template_name = 'version'
        content = self.template_engine.render(template_name, context)
        
        # Get template info
        template_info = self.template_engine.get_template_info(template_name)
        target_filename = template_info['target_filename']
        
        # Version file should be directly in the output directory
        version_file = output_dir / target_filename
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated version file: {version_file}")
        logging_helper(message=f"Generated version file: {version_file}", 
                     message_type="info")