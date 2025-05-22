"""Generator for report settings."""
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from bimigrator.generators.base_template_generator import BaseTemplateGenerator
from bimigrator.models.power_bi_report_settings import PowerBiReportSettings


class ReportSettingsGenerator(BaseTemplateGenerator):
    """Generator for report settings."""

    def generate_report_settings(self, settings: PowerBiReportSettings, output_dir: Optional[Path] = None) -> Path:
        """Generate report settings file.
        
        Args:
            settings: PowerBiReportSettings object containing report settings
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Convert settings to dictionary using dataclasses.asdict
        settings_dict = asdict(settings)

        # Map dictionary keys to template variables
        template_context = {
            'version': settings_dict['version'],
            'type_detection_enabled': settings_dict['queries_settings']['type_detection_enabled'],
            'relationship_import_enabled': settings_dict['queries_settings']['relationship_import_enabled'],
            'queries_settings_version': settings_dict['queries_settings']['version']
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='report_settings',
            context=template_context
        )
        return output_path
