"""
Report file generator for Power BI projects.
"""
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from cognos_migrator.common.websocket_client import logging_helper

from ..models import Report
from .template_engine import TemplateEngine
from .utils import get_extracted_dir, save_json_to_extracted_dir


class ReportFileGenerator:
    """Generator for Power BI report files (report.json, report.config.json, etc.)"""
    
    def __init__(self, template_engine: TemplateEngine):
        """
        Initialize the report file generator
        
        Args:
            template_engine: Template engine for rendering templates
        """
        self.template_engine = template_engine
        self.logger = logging.getLogger(__name__)
    
    def generate_report_files(self, report: Report, output_dir: Path) -> Path:
        """
        Generate report files
        
        Args:
            report: Report object
            output_dir: Output directory
            
        Returns:
            Path to the report directory
        """
        report_dir = output_dir / 'Report'
        report_dir.mkdir(exist_ok=True)
        
        # Generate report.json
        self._generate_report_file(report, report_dir)
        
        # Generate report.config.json
        self._generate_report_config_file(report, report_dir)
        
        # Generate report.metadata.json
        self._generate_report_metadata_file(report, report_dir)
        
        # Generate report.settings.json
        self._generate_report_settings_file(report, report_dir)
        
        # Generate report sections
        self._generate_report_sections(report, report_dir)
        
        # Generate diagram layout
        self._generate_diagram_layout(report_dir)
        
        self.logger.info(f"Generated report files in: {report_dir}")
        logging_helper(message=f"Generated report files in: {report_dir}",
                       message_type="info")
        return report_dir
    
    def _generate_report_file(self, report: Report, report_dir: Path):
        """Generate report.json file"""
        context = {
            'report_id': 0,  # Use 0 as the default ID for compatibility
            'report_name': report.name,
            'sections': report.sections if hasattr(report, 'sections') else []
        }
        
        content = self.template_engine.render('report', context)
        
        report_file = report_dir / 'report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(report_dir)
        if extracted_dir:
            # Save report info as JSON
            report_json = {
                "id": report.id,
                "name": report.name,
                "sections": len(report.sections) if hasattr(report, 'sections') else 0
            }
            save_json_to_extracted_dir(extracted_dir, "report.json", report_json)
            
        self.logger.info(f"Generated report file: {report_file}")
        logging_helper(message=f"Generated report file: {report_file}",
                       message_type="info")
    
    def _generate_report_config_file(self, report: Report, report_dir: Path):
        """Generate report configuration file (report.config.json or config.json)"""
        context = {
            'report_id': report.id,
            'report_name': report.name
        }
        
        # Use the 'config' template which points to the new name
        template_name = 'config'
        content = self.template_engine.render(template_name, context)
        
        # Get template info to determine the target filename
        template_info = self.template_engine.get_template_info(template_name)
        target_filename = template_info['target_filename']
        
        # Create the config file directly in the Report directory
        config_file = report_dir / target_filename
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(report_dir)
        if extracted_dir:
            try:
                # Try to parse the content as JSON
                config_data = json.loads(content)
                save_json_to_extracted_dir(extracted_dir, "report_config.json", config_data)
            except json.JSONDecodeError:
                self.logger.warning("Could not parse report config content as JSON")
            
        self.logger.info(f"Generated report config file: {config_file}")
        logging_helper(message=f"Generated report config file: {config_file}",
                       message_type="info")

    def _generate_report_metadata_file(self, report: Report, report_dir: Path):
        """Generate report metadata file"""
        context = {
            'report_id': report.id,
            'report_name': report.name
        }
        
        # Use the template engine to render the metadata file
        template_name = 'report_metadata'
        content = self.template_engine.render(template_name, context)
        
        # Get template info to determine the target filename
        template_info = self.template_engine.get_template_info(template_name)
        target_filename = template_info['target_filename']
        
        # ReportMetadata.json should be directly in the pbit directory (one level up from report_dir)
        metadata_file = report_dir.parent / target_filename
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(report_dir)
        if extracted_dir:
            try:
                # Try to parse the content as JSON
                metadata_data = json.loads(content)
                save_json_to_extracted_dir(extracted_dir, "report_metadata.json", metadata_data)
            except json.JSONDecodeError:
                self.logger.warning("Could not parse report metadata content as JSON")
            
        self.logger.info(f"Generated report metadata file: {metadata_file}")
        logging_helper(message=f"Generated report metadata file: {metadata_file}",
                       message_type="info")
    
    def _generate_report_settings_file(self, report: Report, report_dir: Path):
        """Generate report settings file"""
        context = {
            'report_id': report.id,
            'report_name': report.name
        }
        
        template_name = 'report_settings'
        content = self.template_engine.render(template_name, context)
        
        # Get template info to determine the target filename
        template_info = self.template_engine.get_template_info(template_name)
        target_filename = template_info['target_filename']
        
        # ReportSettings.json should be directly in the pbit directory (one level up from report_dir)
        settings_file = report_dir.parent / target_filename
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(report_dir)
        if extracted_dir:
            try:
                # Try to parse the content as JSON
                settings_data = json.loads(content)
                save_json_to_extracted_dir(extracted_dir, "report_settings.json", settings_data)
            except json.JSONDecodeError:
                self.logger.warning("Could not parse report settings content as JSON")
            
        self.logger.info(f"Generated report settings file: {settings_file}")
        logging_helper(message=f"Generated report settings file: {settings_file}",
                       message_type="info")
    
    def _generate_report_sections(self, report: Report, report_dir: Path):
        """Generate report section files"""
        # Create sections directory directly under report_dir
        sections_dir = report_dir / 'sections'
        sections_dir.mkdir(parents=True, exist_ok=True)
        
        # If report has sections, generate a file for each section
        if hasattr(report, 'sections') and report.sections:
            for i, section in enumerate(report.sections):
                # Handle both dictionary and ReportPage object formats
                # Try to get report name from extracted data for better naming
                report_name = None
                extracted_dir = get_extracted_dir(report_dir)
                if extracted_dir:
                    report_details_file = extracted_dir / "report_details.json"
                    if report_details_file.exists():
                        try:
                            with open(report_details_file, 'r', encoding='utf-8') as f:
                                report_details = json.load(f)
                                report_name = report_details.get('name')
                        except Exception as e:
                            self.logger.warning(f"Could not load report name from report_details.json: {e}")
                
                if isinstance(section, dict):
                    # Dictionary format
                    section_id = section.get('id', f'section{i}')
                    base_section_name = section.get('name', f'Section {i}')
                    section_display_name = section.get('display_name', f'Section {i}')
                    visuals = section.get('visuals', [])
                    width = section.get('width', 1280)
                    height = section.get('height', 720)
                else:
                    # ReportPage object format
                    section_id = getattr(section, 'id', f'section{i}')
                    base_section_name = section.name
                    section_display_name = section.display_name
                    visuals = section.visuals
                    width = getattr(section, 'width', 1280)
                    height = getattr(section, 'height', 720)
                
                # Enhance section name with report name if available
                if report_name and report_name != "Unknown Report":
                    section_name = f"{report_name} - {base_section_name}"
                    section_display_name = f"{report_name} - {base_section_name}"
                else:
                    section_name = base_section_name
                
                # Generate unique ID for section name (similar to Power BI's format)
                import uuid
                section_unique_id = uuid.uuid4().hex[:20]
                
                # Build context with Power BI compatible fields
                context = {
                    # Legacy fields (kept for backward compatibility)
                    'section_id': section_id,
                    'section_name': section_name,
                    'section_display_name': section_display_name,
                    'visuals': visuals,
                    # Layout information
                    'layout': {
                        'width': width,
                        'height': height,
                        'display_option': 'FitToPage'
                    },
                    
                    # New fields for Power BI compatibility
                    'name': section_unique_id,
                    'displayName': section_display_name,
                    'ordinal': i,
                    'displayOption': 1,
                    'width': width,
                    'height': height
                }
                
                # Create a sanitized name for the section directory with length limits
                sanitized_name = self._sanitize_filename(section_name[:30])  # Limit to 30 chars, then sanitize
                section_dir_name = f"{i:03d}_{sanitized_name}"
                section_dir = sections_dir / section_dir_name
                section_dir.mkdir(exist_ok=True)
                
                # Generate section.json in the section directory
                template_name = 'report_section'
                content = self.template_engine.render(template_name, context)
                section_file = section_dir / "section.json"
                with open(section_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Create empty config.json in the section directory
                config_file = section_dir / "config.json"
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write("{}")
                
                # Create filters.json with actual filter data from Cognos
                filters_file = section_dir / "filters.json"
                section_filters = []
                
                # First try to get filters from extracted data
                extracted_dir = get_extracted_dir(report_dir)
                if extracted_dir:
                    extracted_filters_file = extracted_dir / "report_filters.json"
                    if extracted_filters_file.exists():
                        try:
                            with open(extracted_filters_file, 'r', encoding='utf-8') as f:
                                extracted_filters = json.load(f)
                                # Convert Cognos prompt filters to slicer visuals
                                slicer_visuals = self._convert_cognos_filters_to_slicers(extracted_filters, extracted_dir)
                                if slicer_visuals:
                                    self._generate_slicer_visual_containers(section_dir, slicer_visuals)
                                    self.logger.info(f"Created {len(slicer_visuals)} slicer visuals from Cognos prompt filters")
                        except Exception as e:
                            self.logger.warning(f"Could not load extracted filters: {e}")
                
                # Fallback: Get filters from section if available
                if not section_filters:
                    if hasattr(section, 'filters') and section.filters:
                        section_filters = section.filters
                    elif isinstance(section, dict) and section.get('filters'):
                        section_filters = section.get('filters', [])
                
                with open(filters_file, 'w', encoding='utf-8') as f:
                    json.dump(section_filters, f, indent=2)
                
                # Save to extracted directory if applicable
                extracted_dir = get_extracted_dir(report_dir)
                if extracted_dir:
                    try:
                        # Try to parse the content as JSON
                        section_data = json.loads(content)
                        save_json_to_extracted_dir(extracted_dir, f"section_{i}.json", section_data)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not parse section content as JSON for section {i}")
                
                self.logger.info(f"Generated report section file: {section_file}")
                logging_helper(message=f"Generated report section file: {section_file}",
                            message_type="info")
        else:
            # Generate a default section if no sections are provided
            # Generate unique ID for section name
            import uuid
            section_unique_id = uuid.uuid4().hex[:20]
            
            context = {
                # Legacy fields
                'section_id': 'section0',
                'section_name': 'Page 1',
                'section_display_name': 'Page 1',
                'visuals': [],
                # Layout information
                'layout': {
                    'width': 1280,
                    'height': 720,
                    'display_option': 'FitToPage'
                },
                
                # New fields for Power BI compatibility
                'name': section_unique_id,
                'displayName': 'Page 1',
                'ordinal': 0,
                'displayOption': 1,
                'width': 1280,
                'height': 1280
            }
            
            # Create a directory for the default section
            section_dir_name = "000_Page 1"
            section_dir = sections_dir / section_dir_name
            section_dir.mkdir(exist_ok=True)
            
            # Generate section.json in the section directory
            template_name = 'report_section'
            content = self.template_engine.render(template_name, context)
            section_file = section_dir / "section.json"
            with open(section_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Create empty config.json in the section directory
            config_file = section_dir / "config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write("{}")
            
            # Create empty filters.json in the section directory as an empty array
            filters_file = section_dir / "filters.json"
            with open(filters_file, 'w', encoding='utf-8') as f:
                f.write("[]")
            
            # Save to extracted directory if applicable
            extracted_dir = get_extracted_dir(report_dir)
            if extracted_dir:
                try:
                    # Try to parse the content as JSON
                    section_data = json.loads(content)
                    save_json_to_extracted_dir(extracted_dir, "section_0.json", section_data)
                except json.JSONDecodeError:
                    self.logger.warning("Could not parse default section content as JSON")
            
            self.logger.info(f"Generated report section file: {section_file}")
            logging_helper(message=f"Generated report section file: {section_file}",
                        message_type="info")
    
    def _generate_diagram_layout(self, report_dir: Path):
        """Generate diagram layout file"""
        # Create a basic layout context with nodes and edges
        # Provide the expected variables directly in the context
        context = {
            'version': '1.0',
            'nodes': [],  # Direct access in template
            'edges': []   # Direct access in template
        }
        
        try:
            template_name = 'diagram_layout'
            content = self.template_engine.render(template_name, context)
            
            # Get template info to determine the target filename
            template_info = self.template_engine.get_template_info(template_name)
            target_filename = template_info['target_filename']
            
            # DiagramLayout.json should be directly in the pbit directory (one level up from report_dir)
            layout_file = report_dir.parent / target_filename
            with open(layout_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Save to extracted directory if applicable
            extracted_dir = get_extracted_dir(report_dir)
            if extracted_dir:
                # Save the diagram layout context directly
                layout_data = {
                    "version": context.get('version', '1.0'),
                    "nodes": context.get('nodes', []),
                    "edges": context.get('edges', [])
                }
                save_json_to_extracted_dir(extracted_dir, "layout.json", layout_data)
                
            self.logger.info(f"Generated diagram layout file: {layout_file}")
        except Exception as e:
            self.logger.error(f"Error generating diagram layout: {e}")
    
    def _convert_cognos_filters_to_slicers(self, cognos_filters: List[Dict], extracted_dir: Optional[Path] = None) -> List[Dict]:
        """Convert Cognos prompt filters to Power BI slicer visuals with proper table mapping"""
        slicer_visuals = []
        
        # Load report_queries.json to map fields to their actual tables
        field_to_table_map = {}
        if extracted_dir:
            report_queries_file = extracted_dir / "report_queries.json"
            if report_queries_file.exists():
                try:
                    with open(report_queries_file, 'r', encoding='utf-8') as f:
                        queries = json.load(f)
                        # Build field to table mapping from data_items
                        for query in queries:
                            data_items = query.get('data_items', [])
                            for item in data_items:
                                field_name = item.get('name', '')
                                expression = item.get('expression', '')
                                # Extract table name from expression like "[Database_Layer].[MATERIAL_CHARGES].[SITE_NUMBER]"
                                import re
                                table_match = re.search(r'\[Database_Layer\]\.\[([^\]]+)\]', expression)
                                if table_match and field_name:
                                    table_name = table_match.group(1)
                                    field_to_table_map[field_name] = table_name
                        self.logger.info(f"Built field-to-table mapping with {len(field_to_table_map)} entries from report_queries.json")
                except Exception as e:
                    self.logger.warning(f"Could not load report_queries.json for field mapping: {e}")
        
        for i, cognos_filter in enumerate(cognos_filters):
            # Extract relevant information from Cognos filter
            filter_expression = cognos_filter.get('expression', '')
            query_name = cognos_filter.get('queryName', '')
            
            # Parse the filter expression to extract field and parameter
            # Example: "[SITE_NUMBER]= ?SiteNumber?" -> field: SITE_NUMBER, parameter: SiteNumber
            import re
            match = re.match(r'\[([^\]]+)\]\s*=\s*\?([^?]+)\?', filter_expression)
            
            if match:
                field_name = match.group(1)
                parameter_name = match.group(2)
                
                # Find the correct table for this field
                table_name = field_to_table_map.get(field_name)
                if not table_name:
                    # Fallback: use the query name or default table
                    table_name = query_name if query_name else "MATERIAL_CHARGES"
                    self.logger.warning(f"Could not find table for field {field_name}, using fallback: {table_name}")
                else:
                    self.logger.info(f"Mapped field {field_name} to table {table_name}")
                
                # Generate unique ID for the slicer visual (match Power BI format)
                import uuid
                visual_id = uuid.uuid4().hex[:20]
                
                # Create slicer visual definition
                slicer_visual = {
                    "id": visual_id,
                    "name": f"slicer_{parameter_name.lower()}",
                    "displayName": parameter_name.replace('_', ' ').title(),
                    "type": "slicer",
                    "field": field_name,
                    "table": table_name,
                    "position": {
                        "x": 10 + (i * 200),  # Arrange slicers horizontally
                        "y": 10,
                        "width": 288.41,
                        "height": 86.52
                    },
                    "cognosParameter": parameter_name,
                    "cognosExpression": filter_expression
                }
                slicer_visuals.append(slicer_visual)
                self.logger.info(f"Created slicer visual for field {field_name} -> parameter {parameter_name} in table {table_name}")
        
        return slicer_visuals
    
    def _generate_slicer_visual_containers(self, section_dir: Path, slicer_visuals: List[Dict]):
        """Generate visual container directories and files for slicer visuals using templates"""
        visual_containers_dir = section_dir / "visualContainers"
        visual_containers_dir.mkdir(exist_ok=True)
        
        for i, slicer in enumerate(slicer_visuals):
            # Create visual container directory with shortened naming to avoid filesystem limits
            container_name = f"{i:05d}_{slicer['name'][:20]}_{slicer['id'][:5]}"
            container_dir = visual_containers_dir / container_name
            container_dir.mkdir(exist_ok=True)
            
            # Generate visual container files using templates
            self._generate_slicer_visual_container_files(container_dir, slicer, i)
    
    def _generate_slicer_visual_container_files(self, container_dir: Path, slicer: Dict, ordinal: int):
        """Generate the individual files for a slicer visual container using templates"""
        
        # Prepare template context
        context = {
            'visual_id': slicer['id'],
            'table_name': slicer['table'],
            'field_name': slicer['field'],
            'display_name': slicer['displayName'],
            'x': slicer['position']['x'],
            'y': slicer['position']['y'],
            'width': slicer['position']['width'],
            'height': slicer['position']['height'],
            'z': 0,
            'tab_order': ordinal,
            'table_alias': 'm'  # Standard table alias used in Power BI
        }
        
        # Generate visualContainer.json using template
        visual_container_content = self.template_engine.render('slicer_visual_container', context)
        visual_container_file = container_dir / "visualContainer.json"
        with open(visual_container_file, 'w', encoding='utf-8') as f:
            f.write(visual_container_content)
        
        # Generate config.json using template
        config_content = self.template_engine.render('slicer_config', context)
        config_file = container_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # Generate query.json using template
        query_content = self.template_engine.render('slicer_query', context)
        query_file = container_dir / "query.json"
        with open(query_file, 'w', encoding='utf-8') as f:
            f.write(query_content)
        
        # Generate dataTransforms.json using template
        data_transforms_content = self.template_engine.render('slicer_data_transforms', context)
        data_transforms_file = container_dir / "dataTransforms.json"
        with open(data_transforms_file, 'w', encoding='utf-8') as f:
            f.write(data_transforms_content)
        
        # Generate filters.json (empty for slicer)
        filters_file = container_dir / "filters.json"
        with open(filters_file, 'w', encoding='utf-8') as f:
            f.write("[]")
        
        self.logger.info(f"Generated slicer visual container using templates: {container_dir.name}")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to be safe for file system use
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        # Split by spaces and rejoin with underscores to handle spaces properly
        parts = filename.split()
        sanitized = '_'.join(parts)
        
        # Replace invalid characters with underscores
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', sanitized)
        
        # Remove leading/trailing dots, dashes, and underscores
        sanitized = sanitized.strip('.-_')
        
        # Replace multiple consecutive underscores with single underscore
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove any remaining trailing dashes
        sanitized = re.sub(r'-+$', '', sanitized)
        
        # Final cleanup - remove trailing underscores
        sanitized = sanitized.rstrip('_')
        
        # Ensure the filename is not empty
        if not sanitized:
            sanitized = 'unnamed'
            
        return sanitized
