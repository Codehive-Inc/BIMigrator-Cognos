"""Generator for diagram layout."""
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from bimigrator.generators.base_template_generator import BaseTemplateGenerator
from bimigrator.models.power_bi_diagram_layout import PowerBiDiagramLayout


class DiagramLayoutGenerator(BaseTemplateGenerator):
    """Generator for diagram layout."""

    def generate_diagram_layout(self, layout: PowerBiDiagramLayout, output_dir: Optional[Path] = None) -> Path:
        """Generate diagram layout file.
        
        Args:
            layout: PowerBiDiagramLayout object containing diagram layout
            output_dir: Optional output directory override
            
        Returns:
            Path to generated file
        """
        if output_dir:
            self.output_dir = output_dir.parent
            self.pbit_dir = output_dir
            self.extracted_dir = self.output_dir / 'extracted'

        # Convert layout to dictionary using dataclasses.asdict
        layout_dict = asdict(layout)

        # Map dictionary keys to template variables
        template_context = {
            'version': layout_dict['version'],
            'tables': [
                {
                    'id': table['id'],
                    'x': table['x'],
                    'y': table['y']
                }
                for table in layout_dict['layout']['tables']
            ]
        }

        # Generate file using template
        output_path = self.generate_file(
            template_type='diagram_layout',
            context=template_context
        )
        return output_path
