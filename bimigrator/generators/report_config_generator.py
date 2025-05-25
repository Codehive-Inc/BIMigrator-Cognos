"""Generator for Power BI report config."""
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Dict, Any

from bimigrator.generators.base_template_generator import BaseTemplateGenerator
from bimigrator.models.power_bi_report_config import PowerBiReportConfig


class ReportConfigGenerator(BaseTemplateGenerator):
    """Generator for Power BI report config."""

    def generate_report_config(self, report_config: PowerBiReportConfig, output_dir: Optional[Path] = None) -> Path:
        """Generate report config.json file.
        
        Args:
            report_config: PowerBiReportConfig object containing report config
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Convert report config to dictionary using dataclasses.asdict
        config_dict = asdict(report_config)
        
        # Prepare template context
        template_context = {
            'version': config_dict['version'],
            'theme_name': config_dict['theme_collection']['base_theme']['name'],
            'theme_version': config_dict['theme_collection']['base_theme']['version'],
            'theme_type': config_dict['theme_collection']['base_theme']['type'],
            'active_section_index': config_dict['active_section_index'],
            'default_drill_filter': config_dict['default_drill_filter_other_visuals'],
            'is_cross_highlighting_disabled': False,
            'is_slicer_selections_enabled': True,
            'is_filter_selections_enabled': True,
            'is_field_well_enabled': True,
            'is_apply_all_enabled': True,
            'use_new_filter_pane': config_dict['settings']['use_new_filter_pane_experience'],
            'allow_change_filter_types': config_dict['settings']['allow_change_filter_types']
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='report_config',
            context=template_context
        )
        return output_path
