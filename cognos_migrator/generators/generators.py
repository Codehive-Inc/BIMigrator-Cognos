"""
Power BI project file generators using Jinja2 templating and Handlebars for specific templates
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import re
from datetime import datetime

import jinja2
import pybars

from ..models import (
    DataModel, Table, Column, Relationship, Measure, 
    Report, ReportPage, PowerBIProject, DataType
)
from ..config import MigrationConfig
from ..visual_generator import VisualContainerGenerator, PowerBIVisualContainer
from ..report_parser import CognosReportStructure, CognosVisual


class TemplateEngine:
    """Template engine wrapper supporting both Jinja2 and Handlebars"""
    
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
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_directory)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Initialize Handlebars compiler
        self.handlebars_compiler = pybars.Compiler()
        
        self.templates = {}
        self.handlebars_templates = {}
        self.logger = logging.getLogger(__name__)
        self._load_templates()
    
    def _load_templates(self):
        """Load all template files"""
        if not self.template_directory.exists():
            raise FileNotFoundError(f"Template directory not found: {self.template_directory}")
        
        # Define which templates use which engine
        handlebars_templates = ['table']
        
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
                if template_name in handlebars_templates:
                    # Load as Handlebars template
                    template_path = self.template_directory / filename
                    if template_path.exists():
                        with open(template_path, 'r') as f:
                            template_source = f.read()
                            self.handlebars_templates[template_name] = self.handlebars_compiler.compile(template_source)
                            self.logger.debug(f"Loaded Handlebars template: {template_name}")
                    else:
                        self.logger.warning(f"Handlebars template file not found: {filename}")
                else:
                    # Load as Jinja2 template
                    self.templates[template_name] = self.jinja_env.get_template(filename)
                    self.logger.debug(f"Loaded Jinja2 template: {template_name}")
            except jinja2.TemplateNotFound:
                self.logger.warning(f"Template file not found: {filename}")
            except Exception as e:
                self.logger.error(f"Failed to load template {filename}: {e}")
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context"""
        # Check if it's a Handlebars template
        if template_name in self.handlebars_templates:
            try:
                # Render with Handlebars
                return self.handlebars_templates[template_name](context)
            except Exception as e:
                self.logger.error(f"Failed to render Handlebars template {template_name}: {e}")
                raise
        elif template_name in self.templates:
            try:
                # Render with Jinja2
                return self.templates[template_name].render(context)
            except Exception as e:
                self.logger.error(f"Failed to render Jinja2 template {template_name}: {e}")
                raise
        else:
            raise ValueError(f"Template not found: {template_name}")


class PowerBIProjectGenerator:
    """Generates Power BI project files from data models"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.template_engine = TemplateEngine(config.template_directory)
        self.visual_generator = VisualContainerGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM service client if enabled
        self.llm_service = None
        if hasattr(config, 'llm_service_enabled') and config.llm_service_enabled:
            self.logger.warning("LLM service is enabled for M-query generation")
            from ..llm_service import LLMServiceClient
            self.llm_service = LLMServiceClient(
                base_url=config.llm_service_url,
                api_key=getattr(config, 'llm_service_api_key', None)
            )
            self.logger.warning(f"LLM service client initialized with URL: {config.llm_service_url}")
        else:
            self.logger.info("LLM service is disabled, using default M-query generation")
    
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
            
            # Store the report specification in the data model for LLM context
            if hasattr(cognos_report, 'report_spec'):
                self.logger.warning(f"Adding report_spec to data_model for LLM context")
                # Add report_spec to each table's metadata for use in M-query generation
                for table in data_model.tables:
                    if not hasattr(table, 'metadata'):
                        table.metadata = {}
                    table.metadata['report_spec'] = cognos_report.report_spec
            else:
                self.logger.warning(f"No report_spec available in cognos_report")
            
            # Generate project structure
            project = PowerBIProject(
                name=cognos_report.name,
                data_model=data_model,
                report=None  # Will be created below
            )
            
            # Generate project file
            self._generate_project_file(project, output_dir)
            
            # Generate model files with report spec context
            self._generate_model_files(data_model, output_dir, cognos_report.report_spec if hasattr(cognos_report, 'report_spec') else None)
            
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
    
    def _generate_model_files(self, data_model: DataModel, output_dir: Path, report_spec: Optional[str] = None):
        """Generate model files (database, tables, relationships)"""
        model_dir = output_dir / 'Model'
        model_dir.mkdir(exist_ok=True)
        
        # Generate database.tmdl
        self._generate_database_file(data_model, model_dir)
        
        # Generate model.tmdl
        self._generate_model_file(data_model, model_dir)
        
        # Generate table files with report spec context
        self._generate_table_files(data_model.tables, model_dir, report_spec)
        
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
    
    def _generate_table_files(self, tables: List[Table], model_dir: Path, report_spec: Optional[str] = None):
        """Generate table files"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        for table in tables:
            try:
                # Pass report_spec to _build_table_context
                context = self._build_table_context(table, report_spec)
                content = self.template_engine.render('table', context)
                
                # Clean filename for filesystem
                safe_filename = self._sanitize_filename(table.name)
                table_file = tables_dir / f'{safe_filename}.tmdl'
                
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
            except Exception as e:
                self.logger.error(f"Error generating table file for {table.name}: {e}")
                
                # Create an error table file with error information
                error_context = {
                    'source_name': table.name,
                    'is_hidden': False,
                    'columns': [],
                    'measures': [],
                    'hierarchies': [],
                    'partitions': [{
                        'name': f'{table.name}-partition',
                        'source_type': 'm',
                        'expression': f'// ERROR: Failed to generate M-query for {table.name}\n// {str(e)}\nlet\n\t\t\t\tSource = Table.FromRows({{}})\n\t\t\tin\n\t\t\t\tSource'
                    }],
                    'has_widget_serialization': False,
                    'visual_type': 'Table',
                    'column_settings': '[]',
                    'error': str(e)
                }
                
                # Add columns if available
                if hasattr(table, 'columns'):
                    error_context['columns'] = [{
                        'source_name': col.name,
                        'source_column': col.source_column if hasattr(col, 'source_column') else col.name,
                        'datatype': self._map_datatype_to_powerbi(col.data_type) if hasattr(col, 'data_type') else 'string',
                        'summarize_by': col.summarize_by if hasattr(col, 'summarize_by') else 'none',
                        'format_string': col.format_string if hasattr(col, 'format_string') else None,
                        'is_hidden': False,
                        'is_calculated': False,
                        'is_data_type_inferred': False,
                        'annotations': {'SummarizationSetBy': 'User'}
                    } for col in table.columns]
                
                # Render error table
                error_content = self.template_engine.render('table', error_context)
                
                # Clean filename for filesystem
                safe_filename = self._sanitize_filename(table.name)
                error_table_file = tables_dir / f'{safe_filename}.tmdl'
                
                with open(error_table_file, 'w', encoding='utf-8') as f:
                    f.write(error_content)
    
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None) -> Dict[str, Any]:
        """Build context for table template"""
        columns_context = []
        for column in table.columns:
            # Set default format string for numeric types if not provided
            format_string = column.format_string
            if not format_string and self._map_datatype_to_powerbi(column.data_type) in ['int64', 'double', 'decimal']:
                format_string = '0'
                
            columns_context.append({
                'source_name': column.name,
                'source_column': column.source_column,
                'datatype': self._map_datatype_to_powerbi(column.data_type),
                'summarize_by': column.summarize_by,
                'format_string': format_string,
                'is_hidden': False,  # Default
                'is_calculated': False,  # Default for imported columns
                'is_data_type_inferred': False,  # Match example file (no isDataTypeInferred)
                'annotations': {'SummarizationSetBy': 'User'}  # Match example file
            })
        
        measures_context = []
        # Note: Measures are typically defined at model level, but can be table-specific
        
        partitions_context = []
        if table.source_query:
            # Get report_spec from table metadata if available and not provided directly
            table_report_spec = None
            if report_spec:
                table_report_spec = report_spec
            elif hasattr(table, 'metadata') and table.metadata and 'report_spec' in table.metadata:
                table_report_spec = table.metadata['report_spec']
                
            self.logger.warning(f"Using report_spec for table {table.name}: {table_report_spec is not None}")
            
            partitions_context.append({
                'name': f'{table.name}-partition',
                'source_type': 'm',
                'expression': self._build_m_expression(table, table_report_spec)
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
    
    def _build_m_expression(self, table: Table, report_spec: Optional[str] = None, data_sample: Optional[Dict] = None) -> str:
        """Build M expression for table partition using LLM service"""
        self.logger.info(f"Building M-expression for table: {table.name}")
        
        # Check if table has source_query
        if hasattr(table, 'source_query'):
            self.logger.info(f"Table {table.name} has source query: {table.source_query[:50] if table.source_query else 'None'}...")
        else:
            self.logger.info(f"Table {table.name} does not have source_query attribute")
        
        if not self.llm_service:
            error_msg = f"LLM service is not configured but required for M-query generation for table {table.name}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Prepare context for LLM service
        context = {
            'table_name': table.name,
            'columns': [{
                'name': col.name,
                'data_type': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type),
                'description': col.description if hasattr(col, 'description') else None
            } for col in table.columns],
            'source_query': table.source_query,
        }
        
        # Add report specification if available
        if report_spec:
            # Extract relevant parts of the report spec to keep context size manageable
            context['report_spec'] = self._extract_relevant_report_spec(report_spec, table.name)
        
        # Add data sample if available
        if data_sample:
            context['data_sample'] = data_sample
        
        # Call LLM service to generate optimized M-query
        self.logger.warning(f"Generating optimized M-query for table {table.name} using LLM service")
        m_query = self.llm_service.generate_m_query(context)
        
        # Clean the M-query by removing comments
        cleaned_m_query = self._clean_m_query(m_query)
        self.logger.warning(f"Cleaned M-query for table {table.name}")
        return cleaned_m_query
        
    def _clean_m_query(self, m_query: str) -> str:
        """Clean M-query by removing comments and fixing formatting"""
        try:
            # Log original query for debugging
            self.logger.debug(f"Original M-query before cleaning: {m_query}")
            
            # Remove the leading 'm' if present (sometimes added by LLM)
            if m_query.startswith('m '):
                m_query = m_query[2:]
            
            # Parse the query to identify key components
            if 'let' in m_query and 'in' in m_query:
                # Extract the parts between let and in
                let_part = m_query.split('let')[1].split('in')[0]
                in_part = m_query.split('in')[1].strip()
                
                # Process the let part to remove comments but keep code
                cleaned_let_part = ""
                for line in let_part.split(','):
                    # Remove comments (text after // or / /)
                    code_part = re.sub(r'(/ /|//).*?(?=,|$)', '', line).strip()
                    if code_part:
                        cleaned_let_part += code_part + ", "
                
                # Remove trailing comma if present
                cleaned_let_part = cleaned_let_part.rstrip(', ')
                
                # Clean the in part
                cleaned_in_part = re.sub(r'(/ /|//).*', '', in_part).strip()
                
                # Reconstruct the query
                m_query = f"let {cleaned_let_part} in {cleaned_in_part}"
            
                # Now extract the steps and format them properly
                steps = []
                for step in m_query.split('let')[1].split('in')[0].split(','):
                    step = step.strip()
                    if step:
                        steps.append(step)
                
                # Format the final M-query with proper indentation for TMDL
                formatted_query = "let\n"
                
                # Process each step
                for i, step in enumerate(steps):
                    if '=' in step:
                        parts = step.split('=', 1)
                        step_name = parts[0].strip()
                        step_content = parts[1].strip()
                        
                        # Handle SQL queries - keep them on one line
                        if 'Value.NativeQuery' in step_content or 'Sql.Database' in step_content:
                            # Ensure SQL query is on one line
                            sql_pattern = r'"([^"]*?)"'
                            sql_queries = re.findall(sql_pattern, step_content)
                            for sql in sql_queries:
                                cleaned_sql = sql.replace('\n', ' ').replace('\r', '')
                                step_content = step_content.replace(f'"{sql}"', f'"{cleaned_sql}"')
                        
                        # Handle parameter arrays - keep them on one line
                        if '{{' in step_content and '}}' in step_content:
                            # Ensure parameter arrays are on one line
                            step_content = re.sub(r'\s+', ' ', step_content)
                        
                        formatted_query += f"\t\t\t\t{step_name} = {step_content}"
                        if i < len(steps) - 1:
                            formatted_query += ",\n"
                    else:
                        formatted_query += f"\t\t\t\t{step}"
                        if i < len(steps) - 1:
                            formatted_query += ",\n"
                
                # Add the 'in' part
                formatted_query += "\n\t\t\tin\n\t\t\t\t" + cleaned_in_part
                
                self.logger.debug(f"Cleaned M-query: {formatted_query}")
                return formatted_query
            else:
                # If the query doesn't have let/in structure, just return it as is
                self.logger.debug(f"Cleaned M-query (unchanged): {m_query}")
                return m_query
        except Exception as e:
            self.logger.warning(f"Error cleaning M-query: {e}")
            return m_query
    
    def _extract_relevant_report_spec(self, report_spec: str, table_name: str) -> str:
        """Extract relevant parts of the report specification for the given table"""
        try:
            # This is a simplified implementation - in a real-world scenario,
            # you would parse the XML and extract only the relevant parts
            # related to the table structure, data items, and calculations
            import re
            import xml.etree.ElementTree as ET
            
            # Find data items related to the table
            root = ET.fromstring(report_spec)
            data_items = root.findall('.//dataItem')
            relevant_items = []
            
            for item in data_items:
                # Check if the data item is related to the table
                # This is a simplified check - you would need to adapt this
                # based on your actual Cognos report structure
                if table_name.lower() in ET.tostring(item, encoding='unicode').lower():
                    relevant_items.append(ET.tostring(item, encoding='unicode'))
            
            return '\n'.join(relevant_items)
        except Exception as e:
            self.logger.warning(f"Failed to extract relevant report spec: {e}")
            return ""
    
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
