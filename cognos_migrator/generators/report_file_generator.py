"""
Report file generator for Power BI projects.
"""
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union

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
                if isinstance(section, dict):
                    # Dictionary format
                    section_id = section.get('id', f'section{i}')
                    section_name = section.get('name', f'Section {i}')
                    section_display_name = section.get('display_name', f'Section {i}')
                    visuals = section.get('visuals', [])
                    width = section.get('width', 1280)
                    height = section.get('height', 720)
                else:
                    # ReportPage object format
                    section_id = getattr(section, 'id', f'section{i}')
                    section_name = section.name
                    section_display_name = section.display_name
                    visuals = section.visuals
                    width = getattr(section, 'width', 1280)
                    height = getattr(section, 'height', 720)
                
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
                
                # Create a sanitized name for the section directory
                sanitized_name = self._sanitize_filename(section_name)
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

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to be safe for file system use
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        
        # Ensure the filename is not empty
        if not sanitized:
            sanitized = 'unnamed'
            
        return sanitized
