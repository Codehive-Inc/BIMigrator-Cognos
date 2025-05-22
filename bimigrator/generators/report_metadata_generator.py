"""Generator for creating report metadata files."""
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Optional

from ..config.data_classes import PowerBiReportMetadata
from .base_template_generator import BaseTemplateGenerator


class ReportMetadataGenerator(BaseTemplateGenerator):
    """Generator for creating report metadata files."""

    def __init__(self, config: Dict[str, Any], input_name: str, output_dir: Optional[Path] = None):
        """Initialize generator with configuration.
        
        Args:
            config: Configuration dictionary
            input_name: Name of input file
            output_dir: Optional output directory override
        """
        super().__init__(config, input_name, output_dir)

    def generate_report_metadata(self, metadata: PowerBiReportMetadata, output_dir: Optional[Path] = None) -> Path:
        """Generate report metadata file.
        
        Args:
            metadata: PowerBiReportMetadata object containing report metadata
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Convert metadata to dictionary using dataclasses.asdict
        metadata_dict = asdict(metadata)
        
        # Convert snake_case keys to PascalCase for PowerBI format
        context = {
            'version': metadata_dict['version'],
            'created_from': metadata_dict['created_from'],
            'created_from_release': metadata_dict['created_from_release']
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='report_metadata',
            context=context
        )
        return output_path
