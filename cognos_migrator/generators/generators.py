"""
Generator orchestrator for Power BI project generation.

This module orchestrates the generation of Power BI project files using specialized generators.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..models import PowerBIProject, DataModel, Table, Relationship, Report
from ..llm_service import LLMServiceClient
from ..converters import MQueryConverter

# Import specialized generators
from .template_engine import TemplateEngine
from .project_file_generator import ProjectFileGenerator
from .model_file_generator import ModelFileGenerator
from .report_file_generator import ReportFileGenerator
from .metadata_file_generator import MetadataFileGenerator
from .documentation_generator import DocumentationGenerator
from ..config import MigrationConfig
from ..visual_generator import VisualContainerGenerator, PowerBIVisualContainer
from ..report_parser import CognosReportStructure, CognosVisual


class PowerBIProjectOrchestrator:
    """Orchestrates the generation of Power BI project files using specialized generators"""
    
    def __init__(self, config: MigrationConfig):
        """Initialize the Power BI project orchestrator
        
        Args:
            config: Migration configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize template engine
        self.template_engine = TemplateEngine(config.template_directory)
        
        # Initialize specialized generators
        self.project_file_generator = ProjectFileGenerator(self.template_engine)
        self.metadata_file_generator = MetadataFileGenerator(self.template_engine)
        self.documentation_generator = DocumentationGenerator()
        
        # Initialize LLM service and M-query converter if enabled
        self.llm_service = None
        self.mquery_converter = None
        if hasattr(config, 'llm_service_enabled') and config.llm_service_enabled:
            self.logger.info("LLM service is enabled for M-query generation")
            
            # Initialize LLM service client
            self.llm_service = LLMServiceClient(
                base_url=config.llm_service_url,
                api_key=getattr(config, 'llm_service_api_key', None)
            )
            self.logger.info(f"LLM service client initialized with URL: {config.llm_service_url}")
            
            # Initialize M-query converter
            self.mquery_converter = MQueryConverter(self.llm_service)
            self.logger.info("M-query converter initialized with LLM service")
        else:
            self.logger.info("LLM service is disabled, using default M-query generation")
            
        # Initialize generators that depend on LLM service
        self.model_file_generator = ModelFileGenerator(self.template_engine, self.mquery_converter)
        self.report_file_generator = ReportFileGenerator(self.template_engine)
        
        # Initialize visual generator
        self.visual_generator = VisualContainerGenerator()
    
    def generate_project(self, project: PowerBIProject, output_path: str) -> bool:
        """Generate complete Power BI project structure
        
        Args:
            project: Power BI project object
            output_path: Output directory path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate project file
            self.project_file_generator.generate_project_file(project, output_dir)
            
            # Generate model files
            if project.data_model:
                self.model_file_generator.generate_model_files(project.data_model, output_dir)
            
            # Generate report files
            if project.report:
                self.report_file_generator.generate_report_files(project.report, output_dir)
            
            # Generate metadata files
            self.metadata_file_generator.generate_metadata_files(project, output_dir)
            
            self.logger.info(f"Successfully generated Power BI project at: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate Power BI project: {e}")
            return False
            
    def generate_from_cognos_report(self, cognos_report: CognosReportStructure, 
                                    data_model: DataModel, output_path: str) -> bool:
        """Generate complete Power BI project from Cognos report structure
        
        Args:
            cognos_report: Cognos report structure
            data_model: Data model object
            output_path: Output directory path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Store the report specification in the data model for LLM context
            if hasattr(cognos_report, 'report_spec'):
                self.logger.info(f"Adding report_spec to data_model for LLM context")
                # Add report_spec to each table's metadata for use in M-query generation
                for table in data_model.tables:
                    if not hasattr(table, 'metadata'):
                        table.metadata = {}
                    table.metadata['report_spec'] = cognos_report.report_spec
            else:
                self.logger.info(f"No report_spec available in cognos_report")
            
            # Generate project structure
            project = PowerBIProject(
                name=cognos_report.name,
                data_model=data_model,
                report=None  # Will be created below
            )
            
            # Generate project file
            self.project_file_generator.generate_project_file(project, output_dir)
            
            # Generate model files with report spec context
            self.model_file_generator.generate_model_files(
                data_model, 
                output_dir, 
                cognos_report.report_spec if hasattr(cognos_report, 'report_spec') else None
            )
            
            # Generate enhanced report files with visual containers
            self._generate_enhanced_report_files(cognos_report, data_model, output_dir)
            
            # Generate metadata files
            self.metadata_file_generator.generate_metadata_files(project, output_dir)
            
            # Generate static resources
            self._generate_static_resources(output_dir)
            
            # Generate documentation
            self.documentation_generator.generate_migration_report(project, output_dir)
            
            self.logger.info(f"Successfully generated complete Power BI project from Cognos report at: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate Power BI project from Cognos report: {e}")
            return False
            
    def _generate_enhanced_report_files(self, cognos_report: CognosReportStructure, 
                                       data_model: DataModel, output_dir: Path) -> Path:
        """Generate enhanced report files with visual containers
        
        Args:
            cognos_report: Cognos report structure
            data_model: Data model object
            output_dir: Output directory path
            
        Returns:
            Path to the report directory
        """
        report_dir = output_dir / 'Report'
        report_dir.mkdir(exist_ok=True)
        
        # Create a Report object from the Cognos report structure
        report = Report(
            id=cognos_report.report_id if hasattr(cognos_report, 'report_id') else f"report_{cognos_report.name.lower().replace(' ', '_')}",
            name=cognos_report.name,
            sections=[]
        )
        
        # Generate report.json
        self._generate_enhanced_report_json(cognos_report, report_dir)
        
        # Generate report.config.json
        self._generate_enhanced_report_config(cognos_report, report_dir)
        
        # Generate report sections with visual containers
        self._generate_enhanced_report_sections(cognos_report, data_model, report_dir)
        
        # Generate report.metadata.json and report.settings.json
        self.report_file_generator._generate_report_metadata_file(report, report_dir)
        self.report_file_generator._generate_report_settings_file(report, report_dir)
        
        self.logger.info(f"Generated enhanced report files in: {report_dir}")
        return report_dir
    
    def _generate_enhanced_report_json(self, cognos_report: CognosReportStructure, report_dir: Path):
        """Generate enhanced report.json file
        
        Args:
            cognos_report: Cognos report structure
            report_dir: Report directory path
        """
        # Build sections list
        sections = []
        if hasattr(cognos_report, 'pages') and cognos_report.pages:
            for i, page in enumerate(cognos_report.pages):
                section_id = self._sanitize_filename(page.name) if hasattr(page, 'name') else f"section{i+1}"
                section = {
                    'id': section_id,
                    'name': page.name if hasattr(page, 'name') else f"Page {i+1}",
                    'displayName': page.display_name if hasattr(page, 'display_name') else page.name if hasattr(page, 'name') else f"Page {i+1}",
                    'filters': [],
                    'config': {}
                }
                sections.append(section)
        else:
            # Create a default section
            sections.append({
                'id': 'section1',
                'name': 'Page 1',
                'displayName': 'Page 1',
                'filters': [],
                'config': {}
            })
        
        context = {
            'report_id': cognos_report.report_id if hasattr(cognos_report, 'report_id') else f"report_{cognos_report.name.lower().replace(' ', '_')}",
            'report_name': cognos_report.name,
            'sections': sections
        }
        
        content = self.template_engine.render('report', context)
        
        report_file = report_dir / 'report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated enhanced report file: {report_file}")
    
    def _generate_enhanced_report_config(self, cognos_report: CognosReportStructure, report_dir: Path):
        """Generate enhanced config.json file
        
        Args:
            cognos_report: Cognos report structure
            report_dir: Report directory path
        """
        context = {
            'report_id': cognos_report.report_id if hasattr(cognos_report, 'report_id') else f"report_{cognos_report.name.lower().replace(' ', '_')}",
            'report_name': cognos_report.name
        }
        
        content = self.template_engine.render('report_config', context)
        
        config_file = report_dir / 'report.config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated enhanced report config file: {config_file}")
    
    def _generate_enhanced_report_sections(self, cognos_report: CognosReportStructure, 
                                          data_model: DataModel, report_dir: Path):
        """Generate enhanced report section files with visual containers
        
        Args:
            cognos_report: Cognos report structure
            data_model: Data model object
            report_dir: Report directory path
        """
        sections_dir = report_dir / 'sections'
        sections_dir.mkdir(exist_ok=True)
        
        # Generate section files for each page
        if hasattr(cognos_report, 'pages') and cognos_report.pages:
            for i, page in enumerate(cognos_report.pages):
                # Build context for page
                context = self._build_enhanced_page_context(page)
                
                # Add visuals if available
                if hasattr(page, 'visuals') and page.visuals:
                    visuals = []
                    for j, visual in enumerate(page.visuals):
                        try:
                            # Generate visual container
                            visual_container = self.visual_generator.generate_visual_container(
                                visual, data_model, f"visual{j}"
                            )
                            
                            # Add visual to context
                            visuals.append({
                                'id': visual_container.id,
                                'type': visual_container.type,
                                'name': visual_container.name,
                                'layout': visual_container.layout,
                                'config': visual_container.config
                            })
                        except Exception as e:
                            self.logger.error(f"Failed to generate visual container for {visual.name if hasattr(visual, 'name') else f'visual{j}'}: {e}")
                    
                    context['visuals'] = visuals
                
                # Render section template
                content = self.template_engine.render('report_section', context)
                
                # Write section file
                section_id = self._sanitize_filename(page.name) if hasattr(page, 'name') else f"section{i+1}"
                section_file = sections_dir / f"{section_id}.json"
                with open(section_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                self.logger.info(f"Generated enhanced section file: {section_file}")
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
                
            self.logger.info(f"Generated default section file: {section_file}")
    
    def _build_enhanced_page_context(self, page) -> Dict[str, Any]:
        """Build enhanced context for page template
        
        Args:
            page: Page object
            
        Returns:
            Context dictionary
        """
        # Get page properties
        page_id = self._sanitize_filename(page.name) if hasattr(page, 'name') else "section1"
        page_name = page.name if hasattr(page, 'name') else "Page 1"
        page_display_name = page.display_name if hasattr(page, 'display_name') else page_name
        
        # Build context
        context = {
            'section_id': page_id,
            'section_name': page_name,
            'section_display_name': page_display_name,
            'visuals': []
        }
        
        return context
    
    def _generate_static_resources(self, output_dir: Path):
        """Generate static resources directory
        
        Args:
            output_dir: Output directory path
        """
        # Create static resources directory
        static_dir = output_dir / 'Report' / 'StaticResources' / 'SharedResources' / 'BaseThemes'
        static_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate CY23SU04.json file
        # Provide a default empty layout to satisfy the template requirements
        context = {
            'layout': {},  # Add the missing layout variable
            'version': '1.0.0'
        }
        
        try:
            content = self.template_engine.render('diagram_layout', context)
            
            layout_file = static_dir / 'CY23SU04.json'
            with open(layout_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.logger.info(f"Generated static resources: {layout_file}")
        except Exception as e:
            self.logger.error(f"Failed to generate diagram layout: {e}")
            # Create an empty file as fallback
            layout_file = static_dir / 'CY23SU04.json'
            with open(layout_file, 'w', encoding='utf-8') as f:
                f.write('{}')
            self.logger.warning(f"Created empty diagram layout file as fallback: {layout_file}")
            # This is not a critical error, so we don't want to fail the entire process
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscore
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        # Ensure filename is not empty
        if not filename:
            filename = 'unnamed'
            
        return filename


# Export the orchestrator as PowerBIProjectGenerator for backward compatibility
PowerBIProjectGenerator = PowerBIProjectOrchestrator

# Export the DocumentationGenerator class directly
# No need to reassign it as it's already imported and exported correctly
