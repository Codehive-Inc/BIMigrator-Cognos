"""Generator for creating page filters files."""
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..config.data_classes import PowerBiFilter
from .base_template_generator import BaseTemplateGenerator


class PageFiltersGenerator(BaseTemplateGenerator):
    """Generator for creating page filters files."""

    def __init__(self, config: Dict[str, Any], input_name: str, output_dir: Optional[Path] = None):
        """Initialize generator with configuration.
        
        Args:
            config: Configuration dictionary
            input_name: Name of input file
            output_dir: Optional output directory override
        """
        super().__init__(config, input_name, output_dir)

    def generate_page_filters(self, 
                             page_name: str, 
                             filters: List[PowerBiFilter] = None,
                             output_dir: Optional[Path] = None) -> Path:
        """Generate page filters file.
        
        Args:
            page_name: Name of the page
            filters: List of filters for the page
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Use empty list if filters not provided
        filters = filters or []
        
        # Prepare context for template
        context = {
            'filters': filters
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='page_filters',
            context=context
        )
        return output_path
