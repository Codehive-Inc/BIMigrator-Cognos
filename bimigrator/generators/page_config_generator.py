"""Generator for creating page configuration files."""
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..config.data_classes import PowerBiVisualObject
from .base_template_generator import BaseTemplateGenerator


class PageConfigGenerator(BaseTemplateGenerator):
    """Generator for creating page configuration files."""

    def __init__(self, config: Dict[str, Any], input_name: str, output_dir: Optional[Path] = None):
        """Initialize generator with configuration.
        
        Args:
            config: Configuration dictionary
            input_name: Name of input file
            output_dir: Optional output directory override
        """
        super().__init__(config, input_name, output_dir)

    def generate_page_config(self, 
                            page_name: str, 
                            visuals: List[PowerBiVisualObject] = None, 
                            layout: Dict[str, Any] = None,
                            output_dir: Optional[Path] = None) -> Path:
        """Generate page configuration file.
        
        Args:
            page_name: Name of the page
            visuals: List of visual objects for the page
            layout: Layout configuration for the page
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Use default values if not provided
        visuals = visuals or []
        layout = layout or {
            'width': 1280,
            'height': 720,
            'display_option': '1'
        }
        
        # Prepare context for template
        context = {
            'visuals': visuals,
            'layout': layout
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='page_config',
            context=context
        )
        return output_path
