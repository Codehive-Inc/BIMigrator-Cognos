"""
Documentation generator for Power BI projects.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from cognos_migrator.common.websocket_client import logging_helper

from ..models import PowerBIProject, DataModel, Report
from .template_engine import TemplateEngine


class DocumentationGenerator:
    """Generator for migration documentation"""
    
    def __init__(self, config=None):
        """Initialize the documentation generator
        
        Args:
            config: Optional migration configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
    
    def generate_migration_report(self, project: PowerBIProject, output_dir: Path, 
                                 conversion_stats: Optional[Dict[str, Any]] = None,
                                 errors: Optional[List[str]] = None) -> Path:
        """
        Generate migration report markdown file
        
        Args:
            project: Power BI project object
            output_dir: Output directory
            conversion_stats: Optional conversion statistics
            errors: Optional list of errors
            
        Returns:
            Path to the generated report file
        """
        extracted_dir = output_dir / 'extracted'
        extracted_dir.mkdir(exist_ok=True)
        
        # Build report content
        content = self._build_migration_report_content(project, conversion_stats, errors)
        
        # Write report file
        report_file = extracted_dir / 'migration_report.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated migration report: {report_file}")
        logging_helper(message=f"Generated migration report: {report_file}", 
                    message_type="info")
        return report_file
    
    def _build_migration_report_content(self, project: PowerBIProject, 
                                       conversion_stats: Optional[Dict[str, Any]] = None,
                                       errors: Optional[List[str]] = None) -> str:
        """Build migration report content"""
        content = f"# Migration Report: {project.name}\n\n"
        
        # Add summary section
        content += "## Summary\n\n"
        content += f"- **Report Name**: {project.name}\n"
        content += f"- **Migration Date**: {project.last_modified.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Add data model section
        if project.data_model:
            content += "\n## Data Model\n\n"
            content += f"- **Model Name**: {project.data_model.name}\n"
            content += f"- **Tables**: {len(project.data_model.tables)}\n"
            
            # Add table details
            content += "\n### Tables\n\n"
            for table in project.data_model.tables:
                content += f"- **{table.name}**\n"
                content += f"  - Columns: {len(table.columns)}\n"
                
                # Add column details
                content += "  - Column details:\n"
                for col in table.columns:
                    data_type = col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type)
                    content += f"    - {col.name} ({data_type})\n"
                content += "\n"
            
            # Add relationships
            if project.data_model.relationships:
                content += "\n### Relationships\n\n"
                for rel in project.data_model.relationships:
                    content += f"- {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}\n"
        
        # Add report section
        if project.report:
            content += "\n## Report\n\n"
            content += f"- **Report ID**: {project.report.id}\n"
            content += f"- **Report Name**: {project.report.name}\n"
            
            # Add sections
            if hasattr(project.report, 'sections') and project.report.sections:
                content += f"- **Pages**: {len(project.report.sections)}\n"
                
                content += "\n### Pages\n\n"
                for i, section in enumerate(project.report.sections):
                    # Handle both dictionary and ReportPage object formats
                    if isinstance(section, dict):
                        section_name = section.get('name', f'Section {i}')
                        visuals = section.get('visuals', [])
                    else:
                        # ReportPage object
                        section_name = section.name
                        visuals = section.visuals
                        
                    content += f"- **{section_name}**\n"
                    
                    # Add visuals
                    if visuals:
                        content += f"  - Visuals: {len(visuals)}\n"
                        for j, visual in enumerate(visuals):
                            if isinstance(visual, dict):
                                visual_type = visual.get('type', 'Unknown')
                                visual_name = visual.get('name', f'Visual {j}')
                            else:
                                # Handle non-dict visual objects if needed
                                visual_type = getattr(visual, 'type', 'Unknown')
                                visual_name = getattr(visual, 'name', f'Visual {j}')
                                
                            content += f"    - {visual_name} ({visual_type})\n"
                    else:
                        content += "  - No visuals\n"
                    content += "\n"
        
        # Add conversion statistics
        if conversion_stats:
            content += "\n## Conversion Statistics\n\n"
            
            if 'expressions' in conversion_stats:
                expr_stats = conversion_stats['expressions']
                content += f"- **Expressions Converted**: {expr_stats.get('converted', 0)}/{expr_stats.get('total', 0)}\n"
                content += f"- **Conversion Success Rate**: {expr_stats.get('success_rate', 0):.2f}%\n"
            
            if 'tables' in conversion_stats:
                table_stats = conversion_stats['tables']
                content += f"- **Tables Converted**: {table_stats.get('converted', 0)}/{table_stats.get('total', 0)}\n"
                content += f"- **Table Conversion Success Rate**: {table_stats.get('success_rate', 0):.2f}%\n"
        
        # Add errors
        if errors and len(errors) > 0:
            content += "\n## Errors\n\n"
            for error in errors:
                content += f"- {error}\n"
        
        # Add next steps
        content += "\n## Next Steps\n\n"
        content += "1. Open the generated .pbit file in Power BI Desktop\n"
        content += "2. Review and fix any errors in the data model\n"
        content += "3. Connect to the appropriate data source\n"
        content += "4. Refresh the data\n"
        
        return content
