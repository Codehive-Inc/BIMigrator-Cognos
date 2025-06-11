"""
Power BI project file generators using Jinja2 templating
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

import jinja2

from ..models import (
    DataModel, Table, Column, Relationship, Measure, 
    Report, ReportPage, PowerBIProject, DataType
)
from ..config import MigrationConfig
from ..visual_generator import VisualContainerGenerator, PowerBIVisualContainer
from ..report_parser import CognosReportStructure, CognosVisual


class TemplateEngine:
    """Jinja2 template engine wrapper (migrated from PyBars3)"""
    
    def __init__(self, template_directory: str):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Template directory passed to TemplateEngine: {template_directory}")
        
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent
        
        # Try different template directory paths, prioritizing the config value
        template_paths = [
            Path(template_directory),  # Absolute path as specified in config
            project_root / template_directory,  # Relative to project root
        ]
        
        # Log the paths we're checking
        for path in template_paths:
            self.logger.debug(f"Checking template path: {path}, exists: {path.exists()}")
        
        # Use the first path that exists
        template_path = None
        for path in template_paths:
            if path.exists():
                template_path = path
                break
        
        if not template_path:
            raise FileNotFoundError(f"Template directory not found: {template_directory}. Please check your configuration.")
            
        self.template_directory = template_path
        self.logger.info(f"Using template directory: {self.template_directory}")
        
        
        
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_directory)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.templates = {}
        self.logger = logging.getLogger(__name__)
        self._load_templates()
    
    def _load_templates(self):
        """Load all template files"""
        if not self.template_directory.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_directory}")
        
        template_files = {
            'database': 'database.tmdl',
            'table': 'Table.tmdl',
            'relationship': 'relationship.tmdl',
            'model': 'model.tmdl',
            'culture': 'culture.tmdl',
            'expressions': 'expressions.tmdl',
            'pbixproj': 'pbixproj.json',
            'report_config': 'report.config.json',
            'report': 'report.json',
            'report_metadata': 'report.metadata.json',
            'report_settings': 'report.settings.json',
            'report_section': 'report.section.json',
            'diagram_layout': 'diagram.layout.json',
            'version': 'version.txt'
        }
        
        for template_name, filename in template_files.items():
            try:
                self.templates[template_name] = self.env.get_template(filename)
                self.logger.debug(f"Loaded template: {template_name}")
            except jinja2.TemplateNotFound:
                self.logger.warning(f"Template file not found: {filename}")
            except Exception as e:
                self.logger.error(f"Failed to load template {filename}: {e}")
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        try:
            return self.templates[template_name].render(context)
        except Exception as e:
            self.logger.error(f"Failed to render template {template_name}: {e}")
            raise


class PowerBIProjectGenerator:
    """Generates Power BI project files from data models"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.template_engine = TemplateEngine(config.template_directory)
        self.visual_generator = VisualContainerGenerator()
        self.logger = logging.getLogger(__name__)
    
    def generate_project(self, project: PowerBIProject, output_path: str) -> bool:
        """Generate complete Power BI project structure"""
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate project file
            self._generate_project_file(project, output_dir)
            
            # Generate model files
            if project.data_model:
                self._generate_model_files(project.data_model, output_dir)
            
            # Generate report files
            if project.report:
                self._generate_report_files(project.report, output_dir)
            
            # Generate metadata files
            self._generate_metadata_files(project, output_dir)
            
            self.logger.info(f"Successfully generated Power BI project at: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate Power BI project: {e}")
            return False
    
    def generate_from_cognos_report(self, cognos_report: CognosReportStructure, 
                                   data_model: DataModel, output_path: str) -> bool:
        """Generate complete Power BI project from Cognos report structure"""
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate project structure
            project = PowerBIProject(
                name=cognos_report.name,
                data_model=data_model,
                report=None  # Will be created below
            )
            
            # Generate project file
            self._generate_project_file(project, output_dir)
            
            # Generate model files
            self._generate_model_files(data_model, output_dir)
            
            # Generate enhanced report files with visual containers
            self._generate_enhanced_report_files(cognos_report, data_model, output_dir)
            
            # Generate metadata files
            self._generate_metadata_files(project, output_dir)
            
            # Generate static resources
            self._generate_static_resources(output_dir)
            
            self.logger.info(f"Successfully generated complete Power BI project from Cognos report at: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate Power BI project from Cognos report: {e}")
            return False
    
    def _generate_project_file(self, project: PowerBIProject, output_dir: Path):
        """Generate .pbixproj.json file"""
        # Format datetime with timezone information to match Power BI format
        created_formatted = project.created.strftime('%Y-%m-%dT%H:%M:%S.%f0000+00:00')
        last_modified_formatted = project.last_modified.strftime('%Y-%m-%dT%H:%M:%S.%f0000+00:00')
        
        context = {
            'version': project.version,
            'created': created_formatted,
            'last_modified': last_modified_formatted
        }
        
        content = self.template_engine.render('pbixproj', context)
        
        project_file = output_dir / '.pbixproj.json'
        with open(project_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_model_files(self, data_model: DataModel, output_dir: Path):
        """Generate model files (database, tables, relationships)"""
        model_dir = output_dir / 'Model'
        model_dir.mkdir(exist_ok=True)
        
        # Generate database.tmdl
        self._generate_database_file(data_model, model_dir)
        
        # Generate model.tmdl
        self._generate_model_file(data_model, model_dir)
        
        # Generate table files
        self._generate_table_files(data_model.tables, model_dir)
        
        # Generate relationships.tmdl
        if data_model.relationships:
            self._generate_relationships_file(data_model.relationships, model_dir)
        
        # Generate expressions.tmdl
        if data_model.measures:
            self._generate_expressions_file(data_model.measures, model_dir)
        
        # Generate culture files
        self._generate_culture_files(data_model, model_dir)
    
    def _generate_database_file(self, data_model: DataModel, model_dir: Path):
        """Generate database.tmdl file"""
        context = {
            'name': data_model.name,
            'compatibility_level': data_model.compatibility_level
        }
        
        content = self.template_engine.render('database', context)
        
        with open(model_dir / 'database.tmdl', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_model_file(self, data_model: DataModel, model_dir: Path):
        """Generate model.tmdl file"""
        # Get table names for references
        table_names = [table.name for table in data_model.tables]
        
        context = {
            'model_name': data_model.name,
            'default_culture': data_model.culture or 'en-US',
            'compatibility_level': data_model.compatibility_level,
            'culture': data_model.culture or 'en-US',
            'annotations': data_model.annotations,
            'query_order_list': data_model.annotations.get('PBI_QueryOrder', '[]'),
            'time_intelligence_enabled': data_model.annotations.get('__PBI_TimeIntelligenceEnabled', '1'),
            'desktop_version': data_model.annotations.get('PBIDesktopVersion', '2.141.1253.0 (25.03)+74f9999a1e95f78c739f3ea2b96ba340e9ba8729'),
            'tables': table_names
        }
        
        content = self.template_engine.render('model', context)
        
        with open(model_dir / 'model.tmdl', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_table_files(self, tables: List[Table], model_dir: Path):
        """Generate table files"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        for table in tables:
            context = self._build_table_context(table)
            content = self.template_engine.render('table', context)
            
            # Clean filename for filesystem
            safe_filename = self._sanitize_filename(table.name)
            table_file = tables_dir / f'{safe_filename}.tmdl'
            
            with open(table_file, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _build_table_context(self, table: Table) -> Dict[str, Any]:
        """Build context for table template"""
        columns_context = []
        for column in table.columns:
            columns_context.append({
                'source_name': column.name,
                'source_column': column.source_column,
                'datatype': self._map_datatype_to_powerbi(column.data_type),
                'summarize_by': column.summarize_by,
                'format_string': column.format_string,
                'is_hidden': False,  # Default
                'is_calculated': False,  # Default for imported columns
                'is_data_type_inferred': True,
                'annotations': column.annotations
            })
        
        measures_context = []
        # Note: Measures are typically defined at model level, but can be table-specific
        
        partitions_context = []
        if table.source_query:
            partitions_context.append({
                'name': f'{table.name}-partition',
                'source_type': 'm',
                'expression': self._build_m_expression(table)
            })
        
        return {
            'source_name': table.name,
            'is_hidden': False,
            'columns': columns_context,
            'measures': measures_context,
            'hierarchies': [],  # Would be populated if hierarchies exist
            'partitions': partitions_context,
            'has_widget_serialization': False,
            'visual_type': 'Table',
            'column_settings': '[]'
        }
    
    def _build_m_expression(self, table: Table) -> str:
        """Build M expression for table partition"""
        if table.source_query:
            # For SQL queries, wrap in appropriate M function
            return f'let\n\t\t\t\tSource = Sql.Database("server", "database", [Query="{table.source_query}"])\n\t\t\tin\n\t\t\t\t#"Changed Type"'
        else:
            # For other sources, create a basic expression
            return f'let\n\t\t\t\tSource = Table.FromRows({{}})\n\t\t\tin\n\t\t\t\t#"Changed Type"'
    
    def _generate_relationships_file(self, relationships: List[Relationship], model_dir: Path):
        """Generate relationships.tmdl file"""
        relationships_context = []
        for rel in relationships:
            relationships_context.append({
                'name': rel.name,
                'from_table': rel.from_table,
                'from_column': rel.from_column,
                'to_table': rel.to_table,
                'to_column': rel.to_column,
                'cardinality': rel.cardinality,
                'cross_filter_direction': rel.cross_filter_direction,
                'is_active': rel.is_active
            })
        
        context = {
            'relationships': relationships_context
        }
        
        content = self.template_engine.render('relationship', context)
        
        with open(model_dir / 'relationships.tmdl', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_expressions_file(self, measures: List[Measure], model_dir: Path):
        """Generate expressions.tmdl file"""
        measures_context = []
        for measure in measures:
            measures_context.append({
                'name': measure.name,
                'expression': measure.expression,
                'format_string': measure.format_string,
                'is_hidden': measure.is_hidden,
                'folder': measure.folder
            })
        
        context = {
            'measures': measures_context
        }
        
        content = self.template_engine.render('expressions', context)
        
        with open(model_dir / 'expressions.tmdl', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_culture_files(self, data_model: DataModel, model_dir: Path):
        """Generate culture files"""
        cultures_dir = model_dir / 'cultures'
        cultures_dir.mkdir(exist_ok=True)
        
        context = {
            'culture': data_model.culture,
            'name': data_model.name,
            'version': '1.2.0'  # Match example file version
        }
        
        content = self.template_engine.render('culture', context)
        
        culture_file = cultures_dir / f'{data_model.culture}.tmdl'
        with open(culture_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_report_files(self, report: Report, output_dir: Path):
        """Generate report files"""
        report_dir = output_dir / 'Report'
        report_dir.mkdir(exist_ok=True)
        
        # Generate report.json
        self._generate_report_json(report, report_dir)
        
        # Generate config.json
        self._generate_report_config(report, report_dir)
        
        # Generate sections
        self._generate_report_sections(report.pages, report_dir)
    
    def _generate_report_json(self, report: Report, report_dir: Path):
        """Generate report.json file"""
        context = {
            'name': report.name,
            'pages': [self._build_page_context(page) for page in report.pages],
            'config': report.config
        }
        
        content = self.template_engine.render('report', context)
        
        with open(report_dir / 'report.json', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_report_config(self, report: Report, report_dir: Path):
        """Generate config.json file"""
        context = {
            'theme': report.config.get('theme', 'CorporateTheme'),
            'settings': report.settings
        }
        
        content = self.template_engine.render('report_config', context)
        
        with open(report_dir / 'config.json', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_report_sections(self, pages: List[ReportPage], report_dir: Path):
        """Generate report section files"""
        sections_dir = report_dir / 'sections'
        sections_dir.mkdir(exist_ok=True)
        
        for i, page in enumerate(pages):
            section_name = f'{i:03d}_{self._sanitize_filename(page.name)}'
            section_dir = sections_dir / section_name
            section_dir.mkdir(exist_ok=True)
            
            context = self._build_page_context(page)
            content = self.template_engine.render('report_section', context)
            
            with open(section_dir / 'section.json', 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _build_page_context(self, page: ReportPage) -> Dict[str, Any]:
        """Build context for page template"""
        return {
            'name': page.name,
            'display_name': page.display_name,
            'width': page.width,
            'height': page.height,
            'visuals': page.visuals,
            'filters': page.filters,
            'config': page.config,
            'layout': {
                'width': page.width,
                'height': page.height,
                'display_option': 'FitToPage'
            }
        }
    
    def _generate_metadata_files(self, project: PowerBIProject, output_dir: Path):
        """Generate metadata files"""
        # Generate Version.txt - use the template which has the correct Power BI version
        content = self.template_engine.render('version', {})
        with open(output_dir / 'Version.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Generate DiagramLayout.json
        diagram_context = {
            'version': "1.1.0",  # Match example file version
            'nodes': [],
            'relationships': []
        }
        
        content = self.template_engine.render('diagram_layout', diagram_context)
        with open(output_dir / 'DiagramLayout.json', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Generate ReportMetadata.json
        metadata_context = {
            'version': 5,  # Fixed version number as per example
            'file_description': "",  # Empty FileDescription as per example
            'created_from': "Cloud",  # Standard value
            'created_from_release': "2023.08"  # Match example file value
        }
        
        content = self.template_engine.render('report_metadata', metadata_context)
        with open(output_dir / 'ReportMetadata.json', 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Generate ReportSettings.json
        settings_context = {
            'theme': 'CorporateTheme'
        }
        
        content = self.template_engine.render('report_settings', settings_context)
        with open(output_dir / 'ReportSettings.json', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _map_datatype_to_powerbi(self, data_type: DataType) -> str:
        """Map DataType enum to Power BI data type string"""
        mapping = {
            DataType.STRING: 'string',
            DataType.INTEGER: 'int64',
            DataType.DOUBLE: 'double',
            DataType.BOOLEAN: 'boolean',
            DataType.DATE: 'dateTime',
            DataType.DECIMAL: 'decimal'
        }
        return mapping.get(data_type, 'string')
    
    def _generate_enhanced_report_files(self, cognos_report: CognosReportStructure, 
                                       data_model: DataModel, output_dir: Path):
        """Generate enhanced report files with visual containers"""
        report_dir = output_dir / 'Report'
        report_dir.mkdir(exist_ok=True)
        
        # Generate main report.json
        self._generate_enhanced_report_json(cognos_report, report_dir)
        
        # Generate config.json
        self._generate_enhanced_report_config(cognos_report, report_dir)
        
        # Generate sections with visual containers
        self._generate_enhanced_report_sections(cognos_report, data_model, report_dir)
    
    def _generate_enhanced_report_json(self, cognos_report: CognosReportStructure, report_dir: Path):
        """Generate enhanced report.json file"""
        context = {
            'name': cognos_report.name,
            'pages': [self._build_enhanced_page_context(page) for page in cognos_report.pages],
            'config': {
                'theme': 'CorporateTheme',
                'version': '1.0'
            }
        }
        
        content = self.template_engine.render('report', context)
        
        with open(report_dir / 'report.json', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_enhanced_report_config(self, cognos_report: CognosReportStructure, report_dir: Path):
        """Generate enhanced config.json file"""
        context = {
            'theme': 'CorporateTheme',
            'settings': {
                'locale': 'en-US',
                'dateFormat': 'MM/dd/yyyy'
            }
        }
        
        content = self.template_engine.render('report_config', context)
        
        with open(report_dir / 'config.json', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_enhanced_report_sections(self, cognos_report: CognosReportStructure, 
                                          data_model: DataModel, report_dir: Path):
        """Generate enhanced report section files with visual containers"""
        sections_dir = report_dir / 'sections'
        sections_dir.mkdir(exist_ok=True)
        
        # Build table mappings for visual generation
        table_mappings = {table.name: table.name for table in data_model.tables}
        
        for i, page in enumerate(cognos_report.pages):
            section_name = f'{i:03d}_{self._sanitize_filename(page.name)}'
            section_dir = sections_dir / section_name
            section_dir.mkdir(exist_ok=True)
            
            # Generate section.json
            context = self._build_enhanced_page_context(page)
            content = self.template_engine.render('report_section', context)
            
            with open(section_dir / 'section.json', 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Generate filters.json
            filters_context = {
                'filters': page.filters or []
            }
            with open(section_dir / 'filters.json', 'w', encoding='utf-8') as f:
                json.dump(filters_context, f, indent=2)
            
            # Generate config.json for section
            section_config = {
                'name': page.name,
                'displayName': page.name,
                'width': page.width or 1280,
                'height': page.height or 720
            }
            with open(section_dir / 'config.json', 'w', encoding='utf-8') as f:
                json.dump(section_config, f, indent=2)
            
            # Generate visual containers
            if page.visuals:
                visual_containers_dir = section_dir / 'visualContainers'
                visual_containers_dir.mkdir(exist_ok=True)
                
                for j, visual in enumerate(page.visuals):
                    # The visual from report_parser should be compatible with visual_generator
                    # It has all the required attributes: power_bi_type, name, position, fields
                    visual_container = self.visual_generator.generate_visual_container(
                        visual, j, table_mappings
                    )
                    
                    # Create visual container directory
                    container_name = visual_container.config.get('name', visual.name)[:6]
                    visual_dir_name = f'{j:05d}_{visual.power_bi_type.value}_{container_name}'
                    visual_dir = visual_containers_dir / visual_dir_name
                    visual_dir.mkdir(exist_ok=True)
                    
                    # Write visual container files
                    with open(visual_dir / 'visualContainer.json', 'w', encoding='utf-8') as f:
                        json.dump(visual_container.visual_container, f, indent=2)
                    
                    with open(visual_dir / 'config.json', 'w', encoding='utf-8') as f:
                        json.dump(visual_container.config, f, indent=2)
                    
                    if visual_container.query:
                        with open(visual_dir / 'query.json', 'w', encoding='utf-8') as f:
                            json.dump(visual_container.query, f, indent=2)
                    
                    if visual_container.data_transforms:
                        with open(visual_dir / 'dataTransforms.json', 'w', encoding='utf-8') as f:
                            json.dump(visual_container.data_transforms, f, indent=2)
                    
                    with open(visual_dir / 'filters.json', 'w', encoding='utf-8') as f:
                        json.dump(visual_container.filters, f, indent=2)
    
    def _build_enhanced_page_context(self, page) -> Dict[str, Any]:
        """Build enhanced context for page template"""
        return {
            'name': page.name,
            'display_name': page.name,
            'width': page.width or 1280,
            'height': page.height or 720,
            'visuals': [self._build_visual_summary(v) for v in (page.visuals or [])],
            'filters': page.filters or [],
            'layout': {
                'width': page.width or 1280,
                'height': page.height or 720,
                'display_option': 'FitToPage'
            },
            'config': {
                'theme': 'CorporateTheme',
                'background': '#FFFFFF'
            }
        }
    
    def _build_visual_summary(self, visual) -> Dict[str, Any]:
        """Build summary for visual in page context"""
        return {
            'id': f'visual_{hash(visual.name) % 10000:04d}',
            'type': visual.power_bi_type.value,
            'name': visual.name,
            'x': visual.position.get('x', 0),
            'y': visual.position.get('y', 0),
            'width': visual.position.get('width', 200),
            'height': visual.position.get('height', 200),
            'properties': visual.properties or {}
        }
    
    def _generate_static_resources(self, output_dir: Path):
        """Generate static resources directory"""
        static_dir = output_dir / 'StaticResources'
        static_dir.mkdir(exist_ok=True)
        
        # Create SharedResources directory
        shared_dir = static_dir / 'SharedResources'
        shared_dir.mkdir(exist_ok=True)
        
        # Create BaseThemes directory
        themes_dir = shared_dir / 'BaseThemes'
        themes_dir.mkdir(exist_ok=True)
        
        # Generate default theme
        default_theme = {
            "name": "CorporateTheme",
            "dataColors": [
                "#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", 
                "#744EC2", "#D9B300", "#D64550", "#197278", "#1AAB40"
            ],
            "background": "#FFFFFF",
            "foreground": "#000000",
            "tableAccent": "#118DFF"
        }
        
        with open(themes_dir / 'CorporateTheme.json', 'w', encoding='utf-8') as f:
            json.dump(default_theme, f, indent=2)
        
        # Create RegisteredResources directory if needed
        registered_dir = static_dir / 'RegisteredResources'
        registered_dir.mkdir(exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename or 'Unnamed'


class DocumentationGenerator:
    """Generates migration documentation"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def generate_migration_report(self, project: PowerBIProject, output_path: str) -> bool:
        """Generate migration documentation"""
        try:
            doc_path = Path(output_path) / 'migration_report.md'
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(self._build_migration_report(project))
            
            self.logger.info(f"Generated migration report: {doc_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration report: {e}")
            return False
    
    def _build_migration_report(self, project: PowerBIProject) -> str:
        """Build migration report content"""
        report = f"""# Power BI Migration Report

## Project Information
- **Name**: {project.name}
- **Version**: {project.version}
- **Created**: {project.created}
- **Last Modified**: {project.last_modified}

## Data Model
"""
        
        if project.data_model:
            report += f"""
### Tables ({len(project.data_model.tables)})
"""
            for table in project.data_model.tables:
                report += f"""
#### {table.name}
- **Columns**: {len(table.columns)}
- **Partition Mode**: {table.partition_mode}
"""
                if table.source_query:
                    report += f"- **Source Query**: Present\n"
        
        if project.report:
            report += f"""
## Report
- **Pages**: {len(project.report.pages)}
"""
            for page in project.report.pages:
                report += f"""
### {page.display_name}
- **Visuals**: {len(page.visuals)}
- **Filters**: {len(page.filters)}
"""
        
        return report
