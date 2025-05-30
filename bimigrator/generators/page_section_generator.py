"""Generator for creating page section files."""
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Optional

from ..config.data_classes import PowerBiReportSection
from .base_template_generator import BaseTemplateGenerator


class PageSectionGenerator(BaseTemplateGenerator):
    """Generator for creating page section files."""

    def __init__(self, config: Dict[str, Any], input_name: str, output_dir: Optional[Path] = None):
        """Initialize generator with configuration.
        
        Args:
            config: Configuration dictionary
            input_name: Name of input file
            output_dir: Optional output directory override
        """
        super().__init__(config, input_name, output_dir)

    def generate_page_section(self, section: PowerBiReportSection, output_dir: Optional[Path] = None) -> Path:
        """Generate page section file.
        
        Args:
            section: PowerBiReportSection object containing section data
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Convert section to dictionary using dataclasses.asdict
        section_dict = asdict(section)
        
        # Prepare context for template
        context = {
            'name': section_dict['name'],
            'display_name': section_dict['display_name'],
            'ordinal': 0,  # Default ordinal
            'width': section_dict['layout']['width'],
            'height': section_dict['layout']['height'],
            'display_option': 1  # Default display option
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='page_section',
            context=context,
            output_dir=output_dir
        )
        return output_path
