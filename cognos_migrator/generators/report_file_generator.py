"""
Report file generator for Power BI projects.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

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
        return report_dir
    
    def _generate_report_file(self, report: Report, report_dir: Path):
        """Generate report.json file"""
        context = {
            'report_id': report.id,
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
    
    def _generate_report_config_file(self, report: Report, report_dir: Path):
        """Generate report.config.json file"""
        context = {
            'report_id': report.id,
            'report_name': report.name
        }
        
        content = self.template_engine.render('report_config', context)
        
        config_file = report_dir / 'report.config.json'
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
    
    def _generate_report_metadata_file(self, report: Report, report_dir: Path):
        """Generate report.metadata.json file"""
        context = {
            'report_id': report.id,
            'report_name': report.name
        }
        
        content = self.template_engine.render('report_metadata', context)
        
        metadata_file = report_dir / 'report.metadata.json'
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
    
    def _generate_report_settings_file(self, report: Report, report_dir: Path):
        """Generate report.settings.json file"""
        context = {
            'report_id': report.id,
            'report_name': report.name
        }
        
        content = self.template_engine.render('report_settings', context)
        
        settings_file = report_dir / 'report.settings.json'
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
    
    def _generate_report_sections(self, report: Report, report_dir: Path):
        """Generate report section files"""
        sections_dir = report_dir / 'sections'
        sections_dir.mkdir(exist_ok=True)
        
        # If report has sections, generate a file for each section
        if hasattr(report, 'sections') and report.sections:
            for i, section in enumerate(report.sections):
                context = {
                    'section_id': section.get('id', f'section{i}'),
                    'section_name': section.get('name', f'Section {i}'),
                    'section_display_name': section.get('display_name', f'Section {i}'),
                    'visuals': section.get('visuals', [])
                }
                
                content = self.template_engine.render('report_section', context)
                
                section_file = sections_dir / f"{context['section_id']}.json"
                with open(section_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                self.logger.info(f"Generated report section file: {section_file}")
        else:
            # Generate a default section
            context = {
                'section_id': 'section1',
                'section_name': 'Page 1',
                'section_display_name': 'Page 1',
                'visuals': []
            }
            
            content = self.template_engine.render('report_section', context)
            
            section_file = sections_dir / 'section1.json'
            with open(section_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.logger.info(f"Generated default report section file: {section_file}")
    
    def _generate_diagram_layout(self, report_dir: Path):
        """Generate diagram layout file"""
        # Create a basic layout context with nodes and edges
        # This addresses the 'layout' is undefined error
        context = {
            'layout': {
                'nodes': [],
                'edges': []
            }
        }
        
        try:
            content = self.template_engine.render('diagram_layout', context)
            
            layout_dir = report_dir / 'diagramLayout'
            layout_dir.mkdir(exist_ok=True)
            
            layout_file = layout_dir / 'layout.json'
            with open(layout_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Save to extracted directory if applicable
            extracted_dir = get_extracted_dir(report_dir)
            if extracted_dir:
                save_json_to_extracted_dir(extracted_dir, "layout.json", context['layout'])
                
            self.logger.info(f"Generated diagram layout file: {layout_file}")
        except Exception as e:
            self.logger.error(f"Error generating diagram layout: {e}")
    

