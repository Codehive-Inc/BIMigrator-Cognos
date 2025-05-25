"""Generator for Power BI report structure."""
from dataclasses import asdict
from pathlib import Path
from typing import Optional, List, Dict, Any

from bimigrator.generators.base_template_generator import BaseTemplateGenerator
from bimigrator.models.power_bi_report import PowerBiReport, ResourceItem


class ReportGenerator(BaseTemplateGenerator):
    """Generator for Power BI report structure."""

    def generate_report(self, report: PowerBiReport, output_dir: Optional[Path] = None) -> Path:
        """Generate report.json file.
        
        Args:
            report: PowerBiReport object containing report structure
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Convert report to dictionary using dataclasses.asdict
        report_dict = asdict(report)
        
        # Prepare shared resources for template
        shared_resources = []
        if report_dict['resource_packages']:
            for package in report_dict['resource_packages']:
                if package['resource_package']['items']:
                    for item in package['resource_package']['items']:
                        shared_resources.append({
                            'name': item['name'],
                            'path': item['path'],
                            'type': item['type']
                        })

        # Map dictionary keys to template variables
        template_context = {
            'report_id': report_dict['report_id'],
            'layout_optimization': report_dict['layout_optimization'],
            'shared_resources': shared_resources
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='report',
            context=template_context
        )
        return output_path
