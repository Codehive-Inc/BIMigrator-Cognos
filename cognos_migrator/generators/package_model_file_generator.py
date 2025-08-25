"""
Package Model file generator for Power BI projects from Cognos Framework Manager packages.

This generator is specifically designed for package migrations and handles:
- Package schema (query subjects) instead of report data items
- Broader table definitions from FM packages
- Package-specific M-query generation
- No report_data_items.json dependency
"""
import logging
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .utils import get_extracted_dir, save_json_to_extracted_dir
from ..models import DataModel, Table, Relationship
from ..converters import MQueryConverter
from ..utils.datatype_mapper import map_cognos_to_powerbi_datatype
from .template_engine import TemplateEngine


class PackageModelFileGenerator:
    """Generator for Power BI model files from Cognos Framework Manager packages"""
    
    def __init__(self, template_engine: TemplateEngine, mquery_converter: Optional[MQueryConverter] = None, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the package model file generator
        
        Args:
            template_engine: Template engine for rendering templates
            mquery_converter: Optional MQueryConverter for generating M-queries (should be PackageMQueryConverter)
            settings: Optional settings dictionary from settings.json
        """
        self.template_engine = template_engine
        self.mquery_converter = mquery_converter
        self.settings = settings or {}
        self.logger = logging.getLogger(__name__)
    
    def generate_model_files(self, data_model: DataModel, output_dir: Path, package_spec: Optional[str] = None, project_metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Generate model files for Power BI template from package data
        
        Args:
            data_model: Data model from package extraction
            output_dir: Output directory for model files
            package_spec: Package specification (not used for packages, for compatibility)
            project_metadata: Optional project metadata (can contain package_info)
        """
        model_dir = output_dir / 'Model'
        model_dir.mkdir(exist_ok=True)
        
        # PACKAGE DEBUG: Log the data model tables at the start of generation
        table_names = [table.name for table in data_model.tables]
        self.logger.info(f"PACKAGE DEBUG: PackageModelFileGenerator received data_model with {len(data_model.tables)} tables")
        self.logger.info(f"PACKAGE DEBUG: Table names at start of generation: {table_names}")
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        # Extract package info from project_metadata if available
        package_info = project_metadata.get('package_info', {}) if project_metadata else {}
        
        # Use package name for naming
        package_name = package_info.get('name') if package_info else data_model.name
        
        # Generate database.tmdl
        self._generate_database_file(data_model, model_dir, package_name)
        
        # Generate table files (package-specific approach)
        if not self.mquery_converter:
            from ..converters import PackageMQueryConverter
            self.mquery_converter = PackageMQueryConverter(output_path=str(output_dir.parent))
        self._generate_package_table_files(data_model.tables, model_dir, package_info)
        
        # Process staging tables AFTER normal table files are generated
        # This allows the staging table handler to read the original M-queries from JSON files
        if self.settings and self.settings.get('staging_tables', {}).get('enabled', False):
            from .staging_table_handler import StagingTableHandler
            self.logger.info(f"Processing staging tables after JSON generation with settings: {self.settings}")
            
            staging_handler = StagingTableHandler(self.settings, extracted_dir, self.mquery_converter)
            data_model = staging_handler.process_data_model(data_model)
            self.logger.info(f"After staging table processing, data model has {len(data_model.tables)} tables")
            self.logger.info(f"Tables after staging: {[t.name for t in data_model.tables]}")
            
            # Regenerate table files with staging table modifications
            self.logger.info("Regenerating table files with staging table modifications")
            
            # Force regeneration of fact table JSON files to include composite keys
            extracted_dir = get_extracted_dir(model_dir)
            if extracted_dir:
                # Remove existing fact table JSON files to force regeneration
                for table in data_model.tables:
                    if not table.name.startswith('Dim_'):  # Only remove fact tables
                        json_file = extracted_dir / f"table_{table.name}.json"
                        if json_file.exists():
                            json_file.unlink()
                            self.logger.info(f"Removed existing JSON file to force regeneration: {json_file}")
            

            self._generate_package_table_files(data_model.tables, model_dir, package_info)
        else:
            self.logger.info("Staging tables not enabled in settings, skipping staging table processing")
        
        # Generate date table files if they exist
        if hasattr(data_model, 'date_tables') and data_model.date_tables:
            self._generate_date_table_files(data_model.date_tables, model_dir)
            self.logger.info(f"Generated {len(data_model.date_tables)} date table files")
        
        # Generate relationships file
        if data_model.relationships:
            self._generate_relationships_file(data_model, model_dir)
        
        # Generate model.tmdl
        self._generate_model_file(data_model, model_dir, package_name)
        
        # Generate culture.tmdl
        self._generate_culture_file(data_model, model_dir)
        
        # Generate expressions.tmdl
        self._generate_expressions_file(data_model, model_dir)
        
        self.logger.info(f"Generated package model files in: {model_dir}")
        return model_dir
    
    def _generate_database_file(self, data_model: DataModel, model_dir: Path, package_name: Optional[str] = None):
        """Generate database.tmdl file for package"""
        database_name = package_name or data_model.name
        self.logger.info(f"Using package name '{database_name}' for database naming")
            
        context = {
            'name': database_name,
            'compatibility_level': data_model.compatibility_level,
            'model_name': database_name
        }
        
        content = self.template_engine.render('database', context)
        
        database_file = model_dir / 'database.tmdl'
        with open(database_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            database_json = {
                "name": data_model.name
            }
            save_json_to_extracted_dir(extracted_dir, "database.json", database_json)
            
        self.logger.info(f"Generated package database file: {database_file}")
    
    def _generate_package_table_files(self, tables: List[Table], model_dir: Path, package_info: Optional[Dict[str, Any]] = None):
        """Generate table/*.tmdl files for packages using JSON-first approach"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        # Phase 1: Generate table JSON files first (package-specific)
        self._generate_package_table_json_files(tables, extracted_dir, package_info)
        
        # Phase 2: Generate TMDL files from finalized JSON files
        self._generate_package_tmdl_from_json(tables, tables_dir, extracted_dir)
    
    def _generate_package_table_json_files(self, tables: List[Table], extracted_dir: Path, package_info: Optional[Dict[str, Any]] = None):
        """Generate table JSON files for packages (no report_data_items.json dependency)"""
        if not extracted_dir:
            self.logger.warning("No extracted directory available, skipping JSON generation")
            return
            
        self.logger.info("Phase 1: Generating package table JSON files")
        
        # Load query subjects information if available
        query_subjects_data = {}
        if extracted_dir:
            query_subjects_file = extracted_dir / "query_subjects.json"
            if query_subjects_file.exists():
                try:
                    with open(query_subjects_file, 'r', encoding='utf-8') as f:
                        query_subjects_list = json.load(f)
                        # Convert list to dictionary for easier lookup
                        for qs in query_subjects_list:
                            query_subjects_data[qs.get('name')] = qs
                    self.logger.info(f"Loaded {len(query_subjects_data)} query subjects for package table generation")
                except Exception as e:
                    self.logger.warning(f"Error loading query subjects from {query_subjects_file}: {e}")
        
        # Generate JSON files for each table
        for table in tables:
            table_name = table.name
            
            # Check if JSON file already exists
            table_json_file = extracted_dir / f"table_{table_name}.json"
            if table_json_file.exists():
                self.logger.info(f"Package table JSON file already exists, skipping generation: {table_json_file}")
                continue
            
            try:
                self.logger.info(f"Generating JSON file for package table {table.name}")
                
                # Get query subject data for this table
                qs_data = query_subjects_data.get(table.name, {})
                
                # Generate M-query for the table using package converter
                m_query = None
                if table.m_query:
                    self.logger.info(f"Using pre-generated M-query for package table {table.name}")
                    m_query = table.m_query
                else:
                    try:
                        self.logger.info(f"Generating M-query for package table {table.name}")
                        m_query = self._build_package_m_expression(table)
                        self.logger.info(f"Successfully generated M-query for package table {table.name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to generate M-query for package table {table.name}: {e}")
                
                # Generate table JSON using package-specific logic
                self._generate_single_package_table_json(table, table_name, qs_data, extracted_dir, m_query)
                
            except Exception as e:
                self.logger.error(f"Error generating JSON file for package table {table.name}: {e}")
    
    def _generate_single_package_table_json(self, table: Table, table_name: str, qs_data: Dict[str, Any], extracted_dir: Path, m_query: Optional[str]):
        """Generate JSON file for a single package table"""
        # Load calculations if available (packages can have calculated columns too)
        calculations_map = {}
        calculations_file = extracted_dir / "calculations.json"
        if calculations_file.exists():
            try:
                with open(calculations_file, 'r', encoding='utf-8') as f:
                    calculations_data = json.load(f)
                    for calc in calculations_data.get('calculations', []):
                        if calc.get('TableName') == table.name and calc.get('FormulaDax'):
                            calculations_map[calc.get('CognosName')] = calc.get('FormulaDax')
                self.logger.info(f"Loaded {len(calculations_map)} calculations for package table {table.name}")
            except Exception as e:
                self.logger.warning(f"Failed to load calculations for package table {table.name}: {e}")

        # Create a JSON representation of the package table
        table_json = {
            "source_name": table.name,
            "name": table_name,
            "lineage_tag": getattr(table, 'lineage_tag', None),
            "description": getattr(table, 'description', f"Package table from query subject: {table.name}"),
            "is_hidden": getattr(table, 'is_hidden', False),
            "columns": []
        }

        # Use table columns (from package schema) with deduplication
        # First, deduplicate table columns by column name (case-insensitive)
        unique_columns = {}
        duplicate_columns = []
        
        for col in table.columns:
            column_name = col.name
            column_name_lower = column_name.lower()
            
            if column_name_lower not in unique_columns:
                unique_columns[column_name_lower] = col
            else:
                duplicate_columns.append(column_name)
        
        # Log information about duplicates
        if duplicate_columns:
            self.logger.info(f"Found {len(duplicate_columns)} duplicate column names in table {table.name}")
            self.logger.info(f"Duplicate column names: {duplicate_columns}")
            self.logger.info(f"Using only unique column names for package JSON generation")
        
        # Process deduplicated columns
        for col in unique_columns.values():
            is_calculated = hasattr(col, 'expression') and bool(getattr(col, 'expression', None))
            
            # Use DAX formula for calculated columns if available
            source_column = getattr(col, 'source_column', col.name)
            if is_calculated and col.name in calculations_map:
                source_column = calculations_map[col.name]
                self.logger.info(f"Package JSON: Using FormulaDax as source_column for calculated column {col.name}: {source_column[:30]}...")
            
            column_json = {
                "source_name": col.name,
                "datatype": col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type).lower(),
                "format_string": getattr(col, 'format_string', None),
                "lineage_tag": getattr(col, 'lineage_tag', None),
                "source_column": source_column,
                "description": getattr(col, 'description', None),
                "is_hidden": getattr(col, 'is_hidden', False),
                "summarize_by": getattr(col, 'summarize_by', 'none'),
                "data_category": getattr(col, 'data_category', None),
                "is_calculated": is_calculated,
                "is_data_type_inferred": True,
                "annotations": {
                    "SummarizationSetBy": "Automatic"
                }
            }
            table_json["columns"].append(column_json)
        
        # Add partition information to the table JSON
        if m_query:
            table_json["hierarchies"] = []
            table_json["partitions"] = [
                {
                    "name": table.name,
                    "source_type": "m",
                    "mode": self._get_partition_mode(),
                    "expression": m_query
                }
            ]
            table_json["has_widget_serialization"] = False
            table_json["visual_type"] = None
            table_json["column_settings"] = None
            
            self.logger.info(f"Added M-query partition information to package table {table.name} JSON")
        
        # Save as table_[TableName].json
        save_json_to_extracted_dir(extracted_dir, f"table_{table_name}.json", table_json)
        self.logger.info(f"Generated package table JSON file: table_{table_name}.json")
    
    def _generate_package_tmdl_from_json(self, tables: List[Table], tables_dir: Path, extracted_dir: Path):
        """Generate TMDL files from finalized JSON files for package tables"""
        if not extracted_dir:
            self.logger.warning("No extracted directory available, cannot generate TMDL from JSON")
            return
            
        self.logger.info("Phase 2: Generating package TMDL files from JSON")
        
        for table in tables:
            table_name = table.name
            
            try:
                # Read finalized table JSON
                table_json_file = extracted_dir / f"table_{table_name}.json"
                if not table_json_file.exists():
                    self.logger.warning(f"Package table JSON file not found: {table_json_file}, skipping TMDL generation")
                    continue
                
                with open(table_json_file, 'r', encoding='utf-8') as f:
                    table_json = json.load(f)
                
                # Build context from JSON data
                context = self._build_package_table_context_from_json(table_json, table_name)
                
                # Render table template
                content = self.template_engine.render('table', context)

                # Log the M-query being written to the TMDL file
                if 'm_expression' in context and context['m_expression']:
                    self.logger.info(f"[PACKAGE MQUERY] M-query being written to TMDL for table {table_name}: {context['m_expression'][:200]}...")
                
                # Write table file
                table_file = tables_dir / f"{table_name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.logger.info(f"Generated package TMDL file from JSON: {table_file}")
                
            except Exception as e:
                self.logger.error(f"Error generating TMDL file for package table {table_name}: {e}")
                
                # Create a minimal error table file
                error_content = f"table '{table_name}'\n\n"
                error_content += f"    column 'Error'\n"
                error_content += f"        dataType: string\n"
                error_content += f"        summarizeBy: none\n"
                error_content += f"        sourceColumn: Error\n\n"
                error_content += f"        annotation SummarizationSetBy = User\n\n"
                error_content += f"\n\n\n    partition '{table_name}-partition' = m\n"
                error_content += f"        mode: import\n"
                error_content += f"        source = \n"
                error_content += f"            // ERROR: Failed to generate TMDL from JSON for package table {table_name}\n"
                error_content += f"            // {str(e)}\n"
                error_content += f"            let\n\t\t\t\t\tSource = Table.FromRows({{}})\n\t\t\t\tin\n\t\t\t\t\tSource\n"
                error_content += f"        \n\n\n\n"
                error_content += f"    annotation PBI_ResultType = Table\n"
                
                # Write error table file
                table_file = tables_dir / f"{table_name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(error_content)
                    
                self.logger.warning(f"Generated error TMDL file for package table {table_name}: {table_file}")
    
    def _build_package_table_context_from_json(self, table_json: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Build context for table template from finalized JSON data (package version)"""
        self.logger.info(f"Building package table context from JSON for table: {table_name}")
        
        # Extract columns from JSON
        columns = []
        for col_json in table_json.get('columns', []):
            # Use 'name' field from JSON, fallback to 'source_name' if available, then 'Column'
            column_name = col_json.get('name', col_json.get('source_name', 'Column'))
            source_column = col_json.get('sourceColumn', col_json.get('source_column', column_name))
            
            column = {
                'name': column_name,
                'source_name': column_name,
                'datatype': col_json.get('dataType', col_json.get('datatype', 'string')),
                'source_column': source_column,
                'is_calculated': col_json.get('is_calculated', False),
                'summarize_by': col_json.get('summarizeBy', col_json.get('summarize_by', 'none')),
                'is_hidden': col_json.get('is_hidden', False),
                'annotations': col_json.get('annotations', {'SummarizationSetBy': 'Automatic'})
            }
            columns.append(column)
        
        # Extract partition information from JSON
        partitions = []
        for partition_json in table_json.get('partitions', []):
            partition = {
                'name': partition_json.get('name', table_name),
                'source_type': partition_json.get('source_type', 'm'),
                'mode': partition_json.get('mode', self._get_partition_mode()),
                'expression': partition_json.get('expression', '')
            }
            partitions.append(partition)
        
        # Extract M-expression from first partition if available
        m_expression = ''
        if partitions:
            m_expression = partitions[0].get('expression', '')
        
        # Check if table name has spaces or special characters
        has_spaces_or_special_chars = ' ' in table_name or re.search(r'[^a-zA-Z0-9_]', table_name) is not None
        
        context = {
            'name': table_name,
            'table_name': table_name,
            'source_name': table_json.get('source_name', table_name),
            'columns': columns,
            'measures': table_json.get('measures', []),
            'partitions': partitions,
            'partition_name': f"{table_name}-partition",
            'm_expression': m_expression,
            'has_spaces_or_special_chars': has_spaces_or_special_chars
        }
        
        self.logger.info(f"Built context from JSON for package table {table_name}: {len(columns)} columns, {len(partitions)} partitions")
        return context
    
    def _get_partition_mode(self) -> str:
        """Get partition mode from staging table settings."""
        # Use settings passed to constructor, fall back to file if not available
        if hasattr(self, 'settings') and self.settings:
            staging_settings = self.settings.get('staging_tables', {})
            data_load_mode = staging_settings.get('data_load_mode', 'import')
            return 'directQuery' if data_load_mode == 'direct_query' else 'import'
        
        # Fall back to reading from settings.json file
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
            staging_settings = settings.get('staging_tables', {})
            data_load_mode = staging_settings.get('data_load_mode', 'import')
            return 'directQuery' if data_load_mode == 'direct_query' else 'import'
        except (FileNotFoundError, json.JSONDecodeError):
            return 'import'
    
    def _build_package_m_expression(self, table: Table) -> str:
        """Build M expression for package table partition"""
        self.logger.info(f"[PACKAGE MQUERY] Building M-expression for package table: {table.name}")
        
        if not self.mquery_converter:
            error_msg = f"M-query converter is not configured but required for M-query generation for package table {table.name}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use the PackageMQueryConverter to generate the M-query
        self.logger.info(f"[PACKAGE MQUERY] Generating M-query for package table {table.name} using package M-query converter")
        m_query = self.mquery_converter.convert_to_m_query(table)
        self.logger.info(f"[PACKAGE MQUERY] Generated M-query for package table {table.name}: {m_query[:200]}...")
        return m_query
    
    # Reuse relationship, model, culture, date table, and expressions generation from base generator
    def _generate_relationships_file(self, data_model: DataModel, model_dir: Path):
        """Generate relationships file for package data model"""
        # Import and reuse the implementation from ModelFileGenerator
        from .model_file_generator import ModelFileGenerator
        temp_generator = ModelFileGenerator(self.template_engine, self.mquery_converter)
        return temp_generator._generate_relationships_file(data_model, model_dir)
    
    def _generate_model_file(self, data_model: DataModel, model_dir: Path, package_name: Optional[str] = None):
        """Generate model.tmdl file for package"""
        from .model_file_generator import ModelFileGenerator
        temp_generator = ModelFileGenerator(self.template_engine, self.mquery_converter)
        return temp_generator._generate_model_file(data_model, model_dir, package_name)
    
    def _generate_culture_file(self, data_model: DataModel, model_dir: Path):
        """Generate culture.tmdl file for package"""
        from .model_file_generator import ModelFileGenerator
        temp_generator = ModelFileGenerator(self.template_engine, self.mquery_converter)
        return temp_generator._generate_culture_file(data_model, model_dir)
    
    def _generate_date_table_files(self, date_tables: List[Dict], model_dir: Path):
        """Generate date table files for package"""
        from .model_file_generator import ModelFileGenerator
        temp_generator = ModelFileGenerator(self.template_engine, self.mquery_converter)
        return temp_generator._generate_date_table_files(date_tables, model_dir)
    
    def _generate_expressions_file(self, data_model: DataModel, model_dir: Path):
        """Generate expressions.tmdl file for package"""
        from .model_file_generator import ModelFileGenerator
        temp_generator = ModelFileGenerator(self.template_engine, self.mquery_converter)
        return temp_generator._generate_expressions_file(data_model, model_dir) 