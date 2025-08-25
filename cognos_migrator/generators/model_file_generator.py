"""
Model file generator for Power BI projects.
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
from .staging_table_handler import StagingTableHandler


class ModelFileGenerator:
    """Generator for Power BI model files (database.tmdl, tables/*.tmdl, etc.)"""
    
    def __init__(self, template_engine: TemplateEngine, mquery_converter: Optional[MQueryConverter] = None, settings: Optional[Dict[str, Any]] = None):
        """Initialize the model file generator"""
        self.template_engine = template_engine
        self.mquery_converter = mquery_converter
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        
        # Store settings for later use in staging table handler
        self.staging_settings = settings

    def generate_model_files(self, data_model: DataModel, output_dir: Path, report_spec: Optional[str] = None, project_metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Generate model files for Power BI template"""
        self.logger.info(f"Generating model files for {data_model.name}")
        
        # Process data model through staging table handler if enabled
        if self.staging_settings and self.staging_settings.get('staging_tables', {}).get('enabled', False):
            from .staging_table_handler import StagingTableHandler
            self.logger.info("Processing data model through staging table handler")
            
            # Get extracted directory if applicable
            extracted_dir = get_extracted_dir(output_dir / 'Model')
            
            staging_table_handler = StagingTableHandler(self.staging_settings, extracted_dir)
            data_model = staging_table_handler.process_data_model(data_model)
            self.logger.info(f"Data model processed: {len(data_model.tables)} tables, {len(data_model.relationships)} relationships")
        
        model_dir = output_dir / 'Model'
        model_dir.mkdir(exist_ok=True)
        
        # FILTERING DEBUG: Log the data model tables at the start of generation
        table_names = [table.name for table in data_model.tables]
        self.logger.info(f"FILTERING DEBUG: ModelFileGenerator received data_model with {len(data_model.tables)} tables")
        self.logger.info(f"FILTERING DEBUG: Table names at start of generation: {table_names}")
        
        # Check if table filtering settings are available in data_model
        if hasattr(data_model, 'table_filtering'):
            self.logger.info(f"FILTERING DEBUG: Data model has table_filtering attribute: {data_model.table_filtering}")
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        # Try to get report name from report_details.json once
        report_name = None
        if extracted_dir:
            report_details_file = extracted_dir / "report_details.json"
            if report_details_file.exists():
                try:
                    with open(report_details_file, 'r', encoding='utf-8') as f:
                        report_details = json.load(f)
                        report_name = report_details.get('name')
                        if report_name:
                            self.logger.info(f"Using report name '{report_name}' from report_details.json for naming")
                except Exception as e:
                    self.logger.warning(f"Error loading report details from {report_details_file}: {e}")
        
        # Generate database.tmdl
        self._generate_database_file(data_model, model_dir, report_name)
        
        # Generate table files
        if not self.mquery_converter:
            self.mquery_converter = MQueryConverter(output_path=str(output_dir.parent))
        self._generate_table_files(data_model.tables, model_dir, report_spec, report_name, project_metadata)
        
        # Generate date table files if they exist
        if hasattr(data_model, 'date_tables') and data_model.date_tables:
            self._generate_date_table_files(data_model.date_tables, model_dir)
            self.logger.info(f"Generated {len(data_model.date_tables)} date table files")
        
        # Generate relationships file
        if data_model.relationships:
            self._generate_relationships_file(data_model, model_dir)
        
        # Generate model.tmdl
        self._generate_model_file(data_model, model_dir, report_name)
        
        # Generate culture.tmdl
        self._generate_culture_file(data_model, model_dir)
        
        # Generate expressions.tmdl
        self._generate_expressions_file(data_model, model_dir)
        
        self.logger.info(f"Generated model files in: {model_dir}")
        return model_dir
    
    def _generate_database_file(self, data_model: DataModel, model_dir: Path, report_name: Optional[str] = None):
        """Generate database.tmdl file"""
        # Use report name for database name if available
        database_name = data_model.name
        if report_name:
            database_name = report_name
            self.logger.info(f"Using report name '{report_name}' for database naming")
            
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
            # Save database info as JSON
            database_json = {
                "name": data_model.name
            }
            save_json_to_extracted_dir(extracted_dir, "database.json", database_json)
            
        self.logger.info(f"Generated database file: {database_file}")
    
    def _generate_table_files(self, tables: List[Table], model_dir: Path, report_spec: Optional[str] = None, report_name: Optional[str] = None, project_metadata: Optional[Dict[str, Any]] = None):
        """Generate table/*.tmdl files using JSON-first approach"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        # Phase 1: Generate table JSON files first (if not already generated)
        self._generate_report_table_json_files_if_needed(tables, extracted_dir, report_spec, report_name, project_metadata)
        
        # Phase 2: Generate TMDL files from finalized JSON files
        self._generate_report_tmdl_from_json(tables, tables_dir, extracted_dir, report_name)
    
    def _generate_report_table_json_files_if_needed(self, tables: List[Table], extracted_dir: Path, report_spec: Optional[str] = None, report_name: Optional[str] = None, project_metadata: Optional[Dict[str, Any]] = None):
        """Generate table JSON files for reports if they don't already exist"""
        if not extracted_dir:
            self.logger.warning("No extracted directory available, skipping JSON generation")
            return
            
        self.logger.info("Phase 1: Generating/verifying report table JSON files")
        
        all_data_items = []
        if extracted_dir:
            data_items_file = extracted_dir / "report_data_items.json"
            if data_items_file.exists():
                try:
                    with open(data_items_file, 'r', encoding='utf-8') as f:
                        all_data_items = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Error loading data items from {data_items_file}: {e}")

        data_items_by_query = {}
        for item in all_data_items:
            query_name = item.get("queryName")
            if query_name:
                if query_name not in data_items_by_query:
                    data_items_by_query[query_name] = []
                data_items_by_query[query_name].append(item)

        if report_name:
            self.logger.info(f"Using report name '{report_name}' for table naming")

        # Generate JSON files for each table if they don't exist
        for table in tables:
            # Use report name for table naming if available and if table name is 'Data'
            table_name = table.name
            if report_name and table.name == "Data":
                # Replace spaces with underscores and remove special characters
                safe_report_name = re.sub(r'[^\w\s]', '', report_name).replace(' ', '_')
                table_name = safe_report_name
                self.logger.info(f"Using report name '{report_name}' for table naming instead of '{table.name}'")
            
            # Check if JSON file already exists
            table_json_file = extracted_dir / f"table_{table_name}.json"
            if table_json_file.exists():
                self.logger.info(f"Report table JSON file already exists, skipping generation: {table_json_file}")
                continue
            
            try:
                self.logger.info(f"Generating JSON file for report table {table.name}")
                
                # Try to read data items from report_data_items.json
                original_query_name = table.metadata.get("original_query_name", table.name)
                table_data_items = data_items_by_query.get(original_query_name, [])
                
                # Update table.columns with data_items
                if table_data_items:
                    self.logger.info(f"Updating table {table.name} columns with {len(table_data_items)} data items")
                    # Create new Column objects from data items
                    from cognos_migrator.models import Column, DataType
                    
                    # First, deduplicate data items by column name (case-insensitive)
                    unique_items = {}
                    duplicate_items = []
                    
                    for item in table_data_items:
                        column_name = item.get('name', 'Column')
                        column_name_lower = column_name.lower()
                        
                        if column_name_lower not in unique_items:
                            unique_items[column_name_lower] = item
                        else:
                            duplicate_items.append(column_name)
                    
                    # Log information about duplicates
                    if duplicate_items:
                        self.logger.info(f"Found {len(duplicate_items)} duplicate column names in data items for table {table.name}")
                        self.logger.info(f"Duplicate column names: {duplicate_items}")
                        self.logger.info(f"Using only unique column names for JSON generation")
                    
                    # Create columns from deduplicated items
                    updated_columns = []
                    for item in unique_items.values():
                        column_name = item.get('name', 'Column')
                        # Map Cognos data type to Power BI data type
                        data_type_str, _ = map_cognos_to_powerbi_datatype(item, self.logger)
                        try:
                            # Try to convert string data type to enum
                            data_type_enum = DataType[data_type_str.upper()]
                        except (KeyError, AttributeError):
                            # Default to STRING if conversion fails
                            data_type_enum = DataType.STRING
                        # Create column object with required source_column parameter
                        column = Column(name=column_name, data_type=data_type_enum, source_column=column_name)
                        updated_columns.append(column)
                    
                    # Update the table's columns
                    table.columns = updated_columns
                    self.logger.info(f"Updated table {table.name} columns: {', '.join([col.name for col in table.columns])}")
                else:
                    self.logger.warning(f"No data items found for table {table.name}, using default columns")
                
                # Generate M-query for the table
                m_query = None
                if table.m_query:
                    self.logger.info(f"Using pre-generated M-query for table {table.name}")
                    m_query = table.m_query
                else:
                    try:
                        self.logger.info(f"Generating M-query for table {table.name}")
                        m_query = self._build_m_expression(table, report_spec)
                        self.logger.info(f"Successfully generated M-query for table {table.name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to generate M-query for table {table.name}: {e}")
                
                # Generate table JSON using existing logic
                self._generate_single_report_table_json(table, table_name, table_data_items, extracted_dir, m_query, project_metadata)
                
            except Exception as e:
                self.logger.error(f"Error generating JSON file for report table {table.name}: {e}")
    
    def _generate_single_report_table_json(self, table: Table, table_name: str, table_data_items: List[Dict], extracted_dir: Path, m_query: Optional[str], project_metadata: Optional[Dict[str, Any]] = None):
        """Generate JSON file for a single report table"""
        # Load calculations if available to update source_column for calculated fields
        calculations_map = {}
        calculations_file = extracted_dir / "calculations.json"
        if calculations_file.exists():
            try:
                with open(calculations_file, 'r', encoding='utf-8') as f:
                    calculations_data = json.load(f)
                    for calc in calculations_data.get('calculations', []):
                        if calc.get('TableName') == table.name and calc.get('FormulaDax'):
                            calculations_map[calc.get('CognosName')] = calc.get('FormulaDax')
                self.logger.info(f"Loaded {len(calculations_map)} calculations for table {table.name} from {calculations_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load calculations from {calculations_file}: {e}")

        # Create a JSON representation of the table
        table_json = {
            "source_name": table.name,
            "name": table_name,
            "lineage_tag": getattr(table, 'lineage_tag', None),
            "description": getattr(table, 'description', f"Table from federated relation: {table.name}"),
            "is_hidden": getattr(table, 'is_hidden', False),
            "columns": []
        }

        # If we have data items, use them as columns
        if table_data_items:
            # First, deduplicate data items by column name (case-insensitive)
            unique_items = {}
            duplicate_items = []
            
            for item in table_data_items:
                column_name = item.get('name', 'Column')
                column_name_lower = column_name.lower()
                
                if column_name_lower not in unique_items:
                    unique_items[column_name_lower] = item
                else:
                    duplicate_items.append(column_name)
            
            # Log information about duplicates
            if duplicate_items:
                self.logger.info(f"Found {len(duplicate_items)} duplicate column names in data items for table JSON generation")
                self.logger.info(f"Duplicate column names: {duplicate_items}")
                self.logger.info(f"Using only unique column names for table JSON generation")
            
            # Use deduplicated items
            for item in unique_items.values():
                # Use the comprehensive mapping function to get both data type and summarize_by
                data_type, summarize_by = map_cognos_to_powerbi_datatype(item, self.logger)
                
                # Log the data type mapping for debugging
                self.logger.debug(f"JSON: Mapped to Power BI dataType={data_type}, summarize_by={summarize_by} for {item.get('name')}")
                
                column_name = item.get('name', 'Column')
                is_calculation = item.get('type') == 'calculation'
                
                # Use DAX formula for calculated columns if available
                source_column = column_name
                if is_calculation and column_name in calculations_map:
                    source_column = calculations_map[column_name]
                    self.logger.info(f"JSON: Using FormulaDax as source_column for calculated column {column_name}: {source_column[:30]}...")
                
                column_json = {
                    "source_name": column_name,
                    "datatype": data_type,
                    "format_string": None,
                    "lineage_tag": None,
                    "source_column": source_column,
                    "description": None,
                    "is_hidden": False,
                    "summarize_by": summarize_by,
                    "data_category": None,
                    "is_calculated": is_calculation,
                    "is_data_type_inferred": True,
                    "annotations": {
                        "SummarizationSetBy": "Automatic"
                    }
                }
                table_json["columns"].append(column_json)
        else:
            # If no data items, use the table columns
            for col in table.columns:
                is_calculated = hasattr(col, 'expression') and bool(getattr(col, 'expression', None))
                
                # Use DAX formula for calculated columns if available
                source_column = getattr(col, 'source_column', col.name)
                if is_calculated and col.name in calculations_map:
                    source_column = calculations_map[col.name]
                    self.logger.info(f"JSON: Using FormulaDax as source_column for calculated column {col.name}: {source_column[:30]}...")
                
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
        
        # Add partition information to the table JSON using the already generated M-query
        if m_query:
            # Add hierarchies and partitions fields if they don't exist
            if "hierarchies" not in table_json:
                table_json["hierarchies"] = []
            
            # Add partition information
            table_json["partitions"] = [
                {
                    "name": table.name,
                    "source_type": "m",
                    "mode": self._get_partition_mode(),
                    "expression": m_query
                }
            ]
            
            # Add other required fields
            table_json["has_widget_serialization"] = False
            table_json["visual_type"] = None
            table_json["column_settings"] = None
            
            self.logger.info(f"Added M-query partition information to table {table.name} JSON")
        
        # Save as table_[TableName].json using the renamed table name
        save_json_to_extracted_dir(extracted_dir, f"table_{table_name}.json", table_json)
        self.logger.info(f"Generated report table JSON file: table_{table_name}.json")
    
    def _generate_report_tmdl_from_json(self, tables: List[Table], tables_dir: Path, extracted_dir: Path, report_name: Optional[str] = None):
        """Generate TMDL files from finalized JSON files for report tables"""
        if not extracted_dir:
            self.logger.warning("No extracted directory available, cannot generate TMDL from JSON")
            return
            
        self.logger.info("Phase 2: Generating report TMDL files from JSON")
        
        for table in tables:
            # Use report name for table naming if available and if table name is 'Data'
            table_name = table.name
            if report_name and table.name == "Data":
                # Replace spaces with underscores and remove special characters
                safe_report_name = re.sub(r'[^\w\s]', '', report_name).replace(' ', '_')
                table_name = safe_report_name
                self.logger.info(f"Using report name '{report_name}' for table naming instead of '{table.name}'")
            
            try:
                # Read finalized table JSON
                table_json_file = extracted_dir / f"table_{table_name}.json"
                if not table_json_file.exists():
                    self.logger.warning(f"Report table JSON file not found: {table_json_file}, skipping TMDL generation")
                    continue
                
                with open(table_json_file, 'r', encoding='utf-8') as f:
                    table_json = json.load(f)
                
                # Build context from JSON data
                context = self._build_report_table_context_from_json(table_json, table_name)
                
                # Render table template
                content = self.template_engine.render('table', context)

                # Log the M-query being written to the TMDL file
                if 'm_expression' in context and context['m_expression']:
                    self.logger.info(f"[MQUERY_TRACKING] M-query being written to TMDL for table {table_name}: {context['m_expression'][:200]}...")
                
                # Write table file
                table_file = tables_dir / f"{table_name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.logger.info(f"Generated report TMDL file from JSON: {table_file}")
                
            except Exception as e:
                self.logger.error(f"Error generating TMDL file for report table {table_name}: {e}")
                
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
                error_content += f"            // ERROR: Failed to generate TMDL from JSON for report table {table_name}\n"
                error_content += f"            // {str(e)}\n"
                error_content += f"            let\n\t\t\t\t\tSource = Table.FromRows({{}})\n\t\t\t\tin\n\t\t\t\t\tSource\n"
                error_content += f"        \n\n\n\n"
                error_content += f"    annotation PBI_ResultType = Table\n"
                
                # Write error table file
                table_file = tables_dir / f"{table_name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(error_content)
                    
                self.logger.warning(f"Generated error TMDL file for report table {table_name}: {table_file}")
    
    def _build_report_table_context_from_json(self, table_json: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Build context for table template from finalized JSON data (report version)"""
        self.logger.info(f"Building report table context from JSON for table: {table_name}")
        
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
        
        self.logger.info(f"Built context from JSON for report table {table_name}: {len(columns)} columns, {len(partitions)} partitions")
        return context
    
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None, data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, m_query: Optional[str] = None, report_name: Optional[str] = None, project_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build context for table template"""
        # Use report name for table name if available and if table name is 'Data'
        table_name = table.name
        if report_name and table.name == "Data":
            # Replace spaces with underscores and remove special characters
            safe_report_name = re.sub(r'[^\w\s]', '', report_name).replace(' ', '_')
            table_name = safe_report_name
            self.logger.info(f"Using report name '{report_name}' for table name instead of '{table.name}'")
        
        columns = []
        
        if extracted_dir:
            self.logger.info(f"Using extracted directory: {extracted_dir}")
        else:
            self.logger.warning(f"No extracted directory provided for table {table.name}")
        
        # Load calculations if available to update source_column for calculated fields
        calculations_map = {}
        if extracted_dir and extracted_dir.exists():
            calculations_file = extracted_dir / "calculations.json"
            if calculations_file.exists():
                try:
                    with open(calculations_file, 'r', encoding='utf-8') as f:
                        calculations_data = json.load(f)
                        for calc in calculations_data.get('calculations', []):
                            if calc.get('TableName') == table.name and calc.get('FormulaDax'):
                                calculations_map[calc.get('CognosName')] = calc.get('FormulaDax')
                    self.logger.info(f"Loaded {len(calculations_map)} calculations for table {table.name} from {calculations_file}")
                except Exception as e:
                    self.logger.warning(f"Error loading calculations for table {table.name} from {calculations_file}: {e}")
        else:
            self.logger.warning(f"Cannot load calculations: extracted_dir is not valid: {extracted_dir}")
        
        # If data_items is not provided, try to get them from the extracted directory
        if data_items is None:
            data_items = []
            # Try to read data items from report_data_items.json
            if extracted_dir and extracted_dir.exists():
                data_items_file = extracted_dir / "report_data_items.json"
                if data_items_file.exists():
                    try:
                        with open(data_items_file, 'r', encoding='utf-8') as f:
                            data_items = json.load(f)
                        self.logger.info(f"Loaded {len(data_items)} data items for table context from {data_items_file}")
                    except Exception as e:
                        self.logger.warning(f"Error loading data items for table context from {data_items_file}: {e}")
            else:
                self.logger.warning(f"Cannot load data items: extracted_dir is not valid: {extracted_dir}")
        
        # IMPROVED DEDUPLICATION: Always deduplicate columns regardless of source
        # First, deduplicate data items by column name (case-insensitive) if we have data items
        unique_items = {}
        duplicate_items = []
        
        if data_items:
            for item in data_items:
                column_name = item.get('name', 'Column')
                column_name_lower = column_name.lower()
                
                if column_name_lower not in unique_items:
                    unique_items[column_name_lower] = item
                else:
                    duplicate_items.append(column_name)
            
            # Log information about duplicates
            if duplicate_items:
                self.logger.info(f"Found {len(duplicate_items)} duplicate column names in data items for TMDL template generation")
                self.logger.info(f"Duplicate column names: {duplicate_items}")
                self.logger.info(f"Using only unique column names for TMDL template generation")
            
            # Use deduplicated items
            for item in unique_items.values():
                # Use the comprehensive mapping function to get both data type and summarize_by
                data_type, summarize_by = map_cognos_to_powerbi_datatype(item, self.logger)
                
                # Log the data type mapping for debugging
                self.logger.debug(f"TMDL: Mapped to Power BI dataType={data_type}, summarize_by={summarize_by} for {item.get('name')}")
                
                # Determine the appropriate SummarizationSetBy annotation value
                summarization_set_by = 'User' if summarize_by != 'none' else 'Automatic'
                
                column_name = item.get('name', 'Column')
                is_calculation = item.get('type') == 'calculation'
                source_column = column_name
                
                # For calculated columns, use FormulaDax from calculations.json if available
                if is_calculation and column_name in calculations_map:
                    source_column = calculations_map[column_name]
                    self.logger.info(f"Using FormulaDax as source_column for calculated column {column_name}: {source_column[:50]}...")
                
                column = {
                    'name': column_name,
                    'source_name': column_name,
                    'datatype': data_type,
                    'source_column': source_column,
                    'is_calculated': is_calculation,
                    'summarize_by': summarize_by,
                    'is_hidden': False,
                    'annotations': {'SummarizationSetBy': summarization_set_by}
                }
                columns.append(column)
        elif table.columns:
            # If no data items, use the table columns but still deduplicate
            # Create a dictionary to track unique columns by name (case-insensitive)
            unique_columns = {}
            duplicate_cols = []
            
            for col in table.columns:
                column_name = col.name
                column_name_lower = column_name.lower()
                
                if column_name_lower not in unique_columns:
                    unique_columns[column_name_lower] = col
                else:
                    duplicate_cols.append(column_name)
            
            # Log information about duplicates
            if duplicate_cols:
                self.logger.info(f"Found {len(duplicate_cols)} duplicate column names in table.columns for {table.name}")
                self.logger.info(f"Duplicate column names: {duplicate_cols}")
                self.logger.info(f"Using only unique column names for TMDL template generation")
            
            # Use deduplicated columns
            for col in unique_columns.values():
                from cognos_migrator.models import DataType
                column_name = col.name
                is_calculation = hasattr(col, 'expression') and bool(getattr(col, 'expression', None))
                source_column = column_name
                is_datetime = col.data_type == DataType.DATE

                # For calculated columns, use FormulaDax from calculations.json if available
                if is_calculation and column_name in calculations_map:
                    source_column = calculations_map[column_name]
                    self.logger.info(f"Using FormulaDax as source_column for calculated column {column_name}: {source_column[:50]}...")
                # Always respect the is_calculation flag - don't override it based on expression content
                
                column = {
                    'name': column_name,
                    'source_name': column_name,
                    'datatype': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type).lower(),
                    'source_column': source_column,
                    'is_calculated': is_calculation,
                    'summarize_by': getattr(col, 'summarize_by', 'none'),
                    'is_hidden': getattr(col, 'is_hidden', False),
                    'annotations': {'SummarizationSetBy': 'Automatic'},
                    'is_datetime': is_datetime
                }

                if is_datetime and hasattr(col, 'metadata') and 'relationship_info' in col.metadata:
                    column['relationship_info'] = col.metadata['relationship_info']

                columns.append(column)
            
        # Use the provided M-query or generate it if not provided
        if m_query is not None:
            self.logger.info(f"[MQUERY_TRACKING] Using pre-generated M-query for table {table.name}: {m_query[:200]}...")
            m_expression = m_query
        else:
            # Fallback to generating M-query if not provided
            try:
                self.logger.warning(f"[MQUERY_TRACKING] No pre-generated M-query provided for table {table.name}, generating now")
                m_expression = self._build_m_expression(table, report_spec)
                self.logger.info(f"[MQUERY_TRACKING] Generated M-query in _build_table_context for table {table.name}: {m_expression[:200]}...")
            except Exception as e:
                self.logger.error(f"[MQUERY_TRACKING] Error building M-expression for table {table.name}: {e}")
                m_expression = f"// ERROR: {str(e)}\nlet\n\t\t\t\tSource = Table.FromRows({{}})\n\t\t\t\tin\n\t\t\t\tSource"
        
        # Add partition information to the context
        partitions = []
        
        # Skip partition preparation for module migrations
        is_module_migration = project_metadata.get('is_module_migration', False) if project_metadata else False
        if is_module_migration:
            self.logger.info(f"[MQUERY_TRACKING] Skipping partition preparation for module migration: {table_name}")
        elif m_expression:
            self.logger.info(f"[MQUERY_TRACKING] Adding M-query to partition for table {table_name}: {m_expression[:200]}...")
            partitions.append({
                'name': table_name,
                'source_type': 'm',
                'mode': self._get_partition_mode(),
                'expression': m_expression
            })
        
        # Check if table name has spaces or special characters
        has_spaces_or_special_chars = ' ' in table_name or re.search(r'[^a-zA-Z0-9_]', table_name) is not None
        
        context = {
            'name': table_name,
            'table_name': table_name,
            'source_name': table_name,
            'columns': columns,
            'measures': table.measures if hasattr(table, 'measures') else [],
            'partitions': partitions,
            'partition_name': f"{table_name}-partition",
            'm_expression': m_expression,
            'has_spaces_or_special_chars': has_spaces_or_special_chars
        }
        
        return context
    
    def _build_m_expression(self, table: Table, report_spec: Optional[str] = None) -> str:
        """Build M expression for table partition using MQueryConverter"""
        self.logger.info(f"[MQUERY_TRACKING] Building M-expression for table: {table.name}")
        
        # Check data load mode from settings
        data_load_mode = self._get_data_load_mode()
        self.logger.info(f"[MQUERY_TRACKING] Using data load mode: {data_load_mode}")
        
        if data_load_mode == 'direct_query':
            return self._build_direct_query_expression(table, report_spec)
        else:
            return self._build_import_mode_expression(table, report_spec)
    
    def _get_data_load_mode(self) -> str:
        """Get data load mode from staging table settings."""
        # Use settings passed to constructor, fall back to file if not available
        if hasattr(self, 'settings') and self.settings:
            staging_settings = self.settings.get('staging_tables', {})
            return staging_settings.get('data_load_mode', 'import')
        
        # No fallback loading - settings should be passed from entry point
        self.logger.error("ModelFileGenerator: No settings provided! Settings should be passed from entry point.")
        return 'import'  # Safe default
    
    def _build_direct_query_expression(self, table: Table, report_spec: Optional[str] = None) -> str:
        """Build M expression for DirectQuery mode - simplified for direct database access"""
        self.logger.info(f"[MQUERY_TRACKING] Building DirectQuery M-expression for table: {table.name}")
        
        # For DirectQuery, we create a simple SQL-based M expression
        # This will be optimized later with proper SQL generation
        table_name = table.name
        
        # Simple DirectQuery M expression template
        m_expression = f'''let
    Source = Sql.Database("localhost", "database_name", [Query="SELECT * FROM {table_name}"])
in
    Source'''
        
        self.logger.info(f"[MQUERY_TRACKING] Generated DirectQuery M-expression for table {table.name}")
        return m_expression
    
    def _build_import_mode_expression(self, table: Table, report_spec: Optional[str] = None) -> str:
        """Build M expression for Import mode using MQueryConverter"""
        self.logger.info(f"[MQUERY_TRACKING] Building Import mode M-expression for table: {table.name}")
        
        # Check if table has source_query
        if hasattr(table, 'source_query'):
            self.logger.info(f"[MQUERY_TRACKING] Table {table.name} has source query: {table.source_query[:100] if table.source_query else 'None'}...")
        else:
            self.logger.info(f"[MQUERY_TRACKING] Table {table.name} does not have source_query attribute")
        
        if not self.mquery_converter:
            error_msg = f"M-query converter is not configured but required for M-query generation for table {table.name}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use the MQueryConverter to generate the M-query
        self.logger.info(f"[MQUERY_TRACKING] Generating optimized M-query for table {table.name} using M-query converter")
        m_query = self.mquery_converter.convert_to_m_query(table, report_spec)
        self.logger.info(f"[MQUERY_TRACKING] Generated M-query for table {table.name}: {m_query[:200]}...")
        return m_query
    
    def _get_partition_mode(self) -> str:
        """Get partition mode from staging table settings."""
        data_load_mode = self._get_data_load_mode()
        return 'directQuery' if data_load_mode == 'direct_query' else 'import'
    
    def _generate_relationships_file(self, data_model: DataModel, model_dir: Path):
        """Generate relationships file for the data model"""
        self.logger.info(f"Generating relationships file for {len(data_model.relationships)} relationships")
        
        # Create a mapping of model tables to their source tables
        model_to_source_table = {}
        # Create a mapping of source table names (with prefix) to table file names (without prefix)
        source_table_to_file_name = {}
        
        for table in data_model.tables:
            # Map model tables to source tables
            if not table.metadata.get('is_source_table') and table.metadata.get('original_source_table'):
                model_to_source_table[table.name] = table.metadata.get('original_source_table')
                self.logger.info(f"Mapping model table {table.name} to source table {table.metadata.get('original_source_table')}")
            
            # Create mapping from source table names (with prefix) to table file names (without prefix)
            if table.metadata.get('is_source_table'):
                # The table file name is the table.name (without prefix)
                # The source table name might be in the SQL or metadata
                source_name = table.name  # Default to the table name
                
                # Check if we can extract a source name from SQL
                if table.source_query:
                    match = re.search(r'from\s+\[?[\w\.]+\]?\.([\w]+)', table.source_query, re.IGNORECASE)
                    if match:
                        extracted_name = match.group(1)
                        if extracted_name != table.name:
                            source_name = extracted_name
                            self.logger.info(f"Extracted source name {source_name} from SQL for table {table.name}")
                
                # Map the source table name to the file name
                source_table_to_file_name[source_name] = table.name
                self.logger.info(f"Mapping source table {source_name} to file name {table.name}")
        
        # Prepare relationships data for template rendering
        relationships_context = []
        # Track unique relationships to avoid duplicates
        unique_relationships = set()
        
        for rel in data_model.relationships:
            # Map model tables to source tables in relationships
            from_table = rel.from_table
            to_table = rel.to_table
            
            # If from_table is a model table, use its source table instead
            if from_table in model_to_source_table:
                self.logger.info(f"Replacing model table {from_table} with source table {model_to_source_table[from_table]} in relationship")
                from_table = model_to_source_table[from_table]
            
            # If to_table is a model table, use its source table instead
            if to_table in model_to_source_table:
                self.logger.info(f"Replacing model table {to_table} with source table {model_to_source_table[to_table]} in relationship")
                to_table = model_to_source_table[to_table]
            
            # Now map source table names to file names for consistency
            if from_table in source_table_to_file_name:
                self.logger.info(f"Mapping source table {from_table} to file name {source_table_to_file_name[from_table]} in relationship")
                from_table = source_table_to_file_name[from_table]
                
            if to_table in source_table_to_file_name:
                self.logger.info(f"Mapping source table {to_table} to file name {source_table_to_file_name[to_table]} in relationship")
                to_table = source_table_to_file_name[to_table]
            
            # Determine which cardinality to use (fromCardinality or toCardinality)
            cardinality_type = 'fromCardinality'
            cardinality_value = rel.from_cardinality
            
            # If to_cardinality is explicitly set, use that instead
            if rel.to_cardinality is not None:
                cardinality_type = 'toCardinality'
                cardinality_value = rel.to_cardinality
            
            # Format table names according to TMDL rules
            # Table names with spaces need to be quoted
            from_table_formatted = f"'{from_table}'" if ' ' in from_table else from_table
            to_table_formatted = f"'{to_table}'" if ' ' in to_table else to_table
            
            # Extract just the column names without table prefixes
            from_column = rel.from_column
            to_column = rel.to_column
            
            # If column already includes table name, extract just the column part
            if from_column and '.' in from_column:
                parts = from_column.split('.')
                from_column = parts[-1]  # Take the last part after the last dot
                
            if to_column and '.' in to_column:
                parts = to_column.split('.')
                to_column = parts[-1]  # Take the last part after the last dot
            
            # Format column names - if they contain spaces, they need to be quoted
            from_column_formatted = f"'{from_column}'" if ' ' in from_column else from_column
            to_column_formatted = f"'{to_column}'" if ' ' in to_column else to_column
            
            # Create a unique signature for this relationship to avoid duplicates
            # Use the actual table and column names for the signature
            rel_signature = f"{from_table}.{from_column}:{to_table}.{to_column}"
            
            # Skip if we've already processed this relationship
            if rel_signature in unique_relationships:
                self.logger.info(f"Skipping duplicate relationship: {rel_signature}")
                continue
                
            # Add to our tracking set
            unique_relationships.add(rel_signature)
            
            # Determine which cardinality to use (fromCardinality or toCardinality)
            cardinality_type = 'fromCardinality'
            cardinality_value = rel.from_cardinality
            
            # If to_cardinality is explicitly set, use that instead
            if rel.to_cardinality is not None:
                cardinality_type = 'toCardinality'
                cardinality_value = rel.to_cardinality
            
            relationship_data = {
                'id': rel.id,
                'from_table': from_table_formatted,
                'from_column': from_column_formatted,
                'to_table': to_table_formatted,
                'to_column': to_column_formatted,
                'cardinality_type': cardinality_type,
                'cardinality_value': cardinality_value,
                'cross_filtering_behavior': rel.cross_filtering_behavior,
                'is_active': rel.is_active,
                'join_on_date_behavior': rel.join_on_date_behavior
            }
            relationships_context.append(relationship_data)
        
        self.logger.info(f"Filtered {len(data_model.relationships)} relationships to {len(relationships_context)} unique relationships")
        
        # Create context for template rendering
        context = {
            'relationships': relationships_context
        }
        
        # Generate relationships file using template engine
        content = self.template_engine.render('relationship', context)
        relationships_file = model_dir / 'relationships.tmdl'
        with open(relationships_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            # Save relationships as JSON
            relationships_json = []
            for rel in relationships_context:
                rel_json = {
                    "id": rel['id'],
                    "fromTable": rel['from_table'].strip("'"),  # Remove quotes if present
                    "fromColumn": rel['from_column'].strip("'"),  # Remove quotes if present
                    "toTable": rel['to_table'].strip("'"),  # Remove quotes if present
                    "toColumn": rel['to_column'].strip("'"),  # Remove quotes if present
                    "isActive": rel['is_active']
                }
                
                # Add cardinality
                if rel['cardinality_type'] == 'toCardinality':
                    rel_json["toCardinality"] = rel['cardinality_value']
                else:
                    rel_json["fromCardinality"] = rel['cardinality_value']
                    
                # Add cross filtering behavior
                rel_json["crossFilteringBehavior"] = rel['cross_filtering_behavior']
                
                # Add join on date behavior if present
                if rel['join_on_date_behavior']:
                    rel_json["joinOnDateBehavior"] = rel['join_on_date_behavior']
                    
                relationships_json.append(rel_json)
                
            with open(extracted_dir / 'relationships.json', 'w', encoding='utf-8') as f:
                json.dump(relationships_json, f, indent=2)
            
        self.logger.info(f"Generated relationships file: {relationships_file}")
    
    def _generate_model_file(self, data_model: DataModel, model_dir: Path, report_name: Optional[str] = None):
        """Generate model.tmdl file"""
        self.logger.info(f"Generating model file")
        
        # Create a mapping of model tables to their source tables
        model_to_source_table = {}
        source_tables = set()
        
        # Identify source tables and model tables
        for table in data_model.tables:
            if table.metadata.get('is_source_table'):
                source_tables.add(table.name)
                self.logger.info(f"Identified source table for model: {table.name}")
            elif table.metadata.get('original_source_table'):
                model_to_source_table[table.name] = table.metadata.get('original_source_table')
                self.logger.info(f"Identified model table: {table.name} referencing {table.metadata.get('original_source_table')}")
        
        # Filter tables to only include source tables
        filtered_tables = [table for table in data_model.tables if table.metadata.get('is_source_table')]
        self.logger.info(f"Filtered {len(data_model.tables)} tables to {len(filtered_tables)} source tables for model file")
        
        # Create context for template rendering
        context = {
            'model_name': report_name or 'Model',
            'tables': [table.name for table in filtered_tables],
            'default_culture': 'en-US',  # Add default culture value
            'time_intelligence_enabled': 'true',  # Add time intelligence value
            'desktop_version': '2.118.1063.0 (23.06)'  # Add desktop version value
        }
        
        # Generate model file
        content = self.template_engine.render('model', context)
        model_file = model_dir / 'model.tmdl'
        with open(model_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated model file: {model_file}")
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            model_json = {
                "name": report_name or 'Model',
                "tables": [table.name for table in filtered_tables],
                "culture": "en-US"  # Add culture to JSON as well
            }
            save_json_to_extracted_dir(extracted_dir, "model.json", model_json)
    
    def _generate_culture_file(self, data_model: DataModel, model_dir: Path):
        """Generate culture.tmdl file"""
        # Get the version from data_model if available, otherwise use a default version
        version = getattr(data_model, 'version', '1.0.0') if hasattr(data_model, 'version') else '1.0.0'
        
        context = {
            'culture': data_model.culture or 'en-US',
            'version': version
        }
        
        content = self.template_engine.render('culture', context)
        
        culture_code = data_model.culture or 'en-US'
        culture_file = model_dir / 'cultures' / f'{culture_code}.tmdl'
        culture_file.parent.mkdir(exist_ok=True)
        with open(culture_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            # Save culture info as JSON
            culture_json = {
                "culture": data_model.culture or 'en-US'
            }
            save_json_to_extracted_dir(extracted_dir, "culture.json", culture_json)
            
        self.logger.info(f"Generated culture file: {culture_file}")
    
    def _generate_date_table_files(self, date_tables: List[Dict], model_dir: Path):
        """Generate date table files
        
        Args:
            date_tables: List of date table dictionaries
            model_dir: Directory to write the files to
        """
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        for date_table in date_tables:
            # Get the date table name and content
            date_table_name = date_table['name']
            date_table_content = date_table['template_content']
            
            # Write the date table file
            date_table_file = tables_dir / f"{date_table_name}.tmdl"
            with open(date_table_file, 'w', encoding='utf-8') as f:
                f.write(date_table_content)
            
            self.logger.info(f"Generated date table file: {date_table_file}")
            
            # Save to extracted directory if applicable
            if extracted_dir:
                # Create a basic JSON representation of the date table
                date_table_json = {
                    "name": date_table_name,
                    "source_name": date_table_name,
                    "description": f"Date table for {date_table_name}",
                    "is_hidden": False,
                    "columns": [
                        {
                            "source_name": "Date",
                            "datatype": "dateTime",
                            "format_string": "General Date",
                            "lineage_tag": None,
                            "source_column": "Date",
                            "summarize_by": "none"
                        },
                        {
                            "source_name": "Year",
                            "datatype": "int64",
                            "format_string": "0",
                            "lineage_tag": None,
                            "source_column": "Year",
                            "summarize_by": "none"
                        },
                        {
                            "source_name": "Month",
                            "datatype": "int64",
                            "format_string": "0",
                            "lineage_tag": None,
                            "source_column": "Month",
                            "summarize_by": "none"
                        },
                        {
                            "source_name": "MonthName",
                            "datatype": "string",
                            "format_string": None,
                            "lineage_tag": None,
                            "source_column": "MonthName",
                            "summarize_by": "none"
                        },
                        {
                            "source_name": "Day",
                            "datatype": "int64",
                            "format_string": "0",
                            "lineage_tag": None,
                            "source_column": "Day",
                            "summarize_by": "none"
                        }
                    ],
                    "partitions": [
                        {
                            "name": date_table_name,
                            "source_type": "calculated",
                            "expression": f"CALENDAR(DATE(2015, 1, 1), DATE(2025, 12, 31))"
                        }
                    ]
                }
                
                # Save as table_[TableName].json
                save_json_to_extracted_dir(extracted_dir, f"table_{date_table_name}.json", date_table_json)
                self.logger.info(f"Saved date table JSON to extracted directory: table_{date_table_name}.json")
                
                # Also save the date table definition as a separate JSON file
                save_json_to_extracted_dir(extracted_dir, f"date_table_{date_table_name}.json", date_table)
                self.logger.info(f"Saved date table definition to extracted directory: date_table_{date_table_name}.json")
    
    def _generate_expressions_file(self, data_model: DataModel, model_dir: Path):
        """Generate expressions.tmdl file"""
        # Skip if no expressions or expressions attribute doesn't exist
        if not hasattr(data_model, 'expressions') or not data_model.expressions:
            return
        
        context = {}
        
        content = self.template_engine.render('expressions', context)
        
        expressions_file = model_dir / 'expressions.tmdl'
        with open(expressions_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            # Save version info as JSON
            version = getattr(data_model, 'version', '1.0') if hasattr(data_model, 'version') else '1.0'
            version_json = {
                "version": version
            }
            save_json_to_extracted_dir(extracted_dir, "version.json", version_json)
            
        self.logger.info(f"Generated expressions file: {expressions_file}")