"""
Model file generator for Power BI projects.
"""
import logging
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from cognos_migrator.common.websocket_client import logging_helper

from cognos_migrator.generators.utils import get_extracted_dir, save_json_to_extracted_dir

from cognos_migrator.models import DataModel, Table, Relationship
from cognos_migrator.converters import MQueryConverter
from cognos_migrator.utils.datatype_mapper import map_cognos_to_powerbi_datatype
from cognos_migrator.generators.template_engine import TemplateEngine


class ModuleModelFileGenerator:
    """Generator for Power BI model files (database.tmdl, tables/*.tmdl, etc.)"""
    
    def __init__(self, template_engine: TemplateEngine, mquery_converter: Optional[MQueryConverter] = None, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the model file generator
        
        Args:
            template_engine: Template engine for rendering templates
            mquery_converter: Optional MQueryConverter for generating M-queries
            settings: Optional settings dictionary (passed from entry point)
        """
        self.template_engine = template_engine
        self.mquery_converter = mquery_converter
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        
        # Store settings for later use in staging table handler
        self.staging_settings = settings
    
    def generate_model_files(self, data_model: DataModel, output_dir: Path, report_spec: Optional[str] = None) -> Path:
        """Generate model files for Power BI template"""
        
        self.logger.info(f"Generating model files for {data_model.name}")
        
        # Process data model through staging table handler if enabled
        if self.staging_settings and self.staging_settings.get('staging_tables', {}).get('enabled', False):
            from cognos_migrator.generators.staging_table_handler import StagingTableHandler
            self.logger.info("Processing data model through staging table handler")
            
            # Get extracted directory if applicable
            extracted_dir = get_extracted_dir(output_dir / 'Model')
            
            staging_table_handler = StagingTableHandler(self.staging_settings, extracted_dir)
            data_model = staging_table_handler.process_data_model(data_model)
            self.logger.info(f"Data model processed: {len(data_model.tables)} tables, {len(data_model.relationships)} relationships")
        
        model_dir = output_dir / 'Model'
        model_dir.mkdir(exist_ok=True)
        
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
        self._generate_table_files(data_model.tables, model_dir, report_spec, report_name)
        
        # Generate relationships file
        if data_model.relationships:
            self._generate_relationships_file(data_model.relationships, model_dir)
        
        # Generate model.tmdl
        self._generate_model_file(data_model, model_dir, report_name)
        
        # Generate culture.tmdl
        self._generate_culture_file(data_model, model_dir)
        
        # Generate expressions.tmdl
        self._generate_expressions_file(data_model, model_dir)
        
        self.logger.info(f"Generated model files in: {model_dir}")
        logging_helper(message=f"Generated model files in: {model_dir}", message_type="info")
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
    
    def _generate_table_files(self, tables: List[Table], model_dir: Path, report_spec: Optional[str] = None, report_name: Optional[str] = None):
        """Generate table/*.tmdl files"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        if report_name:
            self.logger.info(f"Using report name '{report_name}' for table naming")
            
        for table in tables:
            try:
                self.logger.warning(f"Using report_spec for table {table.name}: {report_spec is not None}")
                
                # Try to read data items from report_data_items.json for both JSON and TMDL files
                data_items = []
                if extracted_dir:
                    data_items_file = extracted_dir / "report_data_items.json"
                    if data_items_file.exists():
                        try:
                            with open(data_items_file, 'r', encoding='utf-8') as f:
                                data_items = json.load(f)
                            self.logger.info(f"Loaded {len(data_items)} data items for table {table.name} from {data_items_file}")
                        except Exception as e:
                            self.logger.warning(f"Error loading data items from {data_items_file}: {e}")
                
                # Update table.columns with data_items before generating M-query
                if data_items:
                    self.logger.info(f"Updating table {table.name} columns with {len(data_items)} data items before M-query generation")
                    # Create new Column objects from data items
                    from cognos_migrator.models import Column, DataType
                    updated_columns = []
                    for item in data_items:
                        column_name = item.get('identifier', 'Column')  # Using 'identifier' field for more accurate column naming
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
                    self.logger.warning(f"No data items found for table {table.name}, using default columns for M-query generation")
                
                # Generate M-query once for both table TMDL and JSON
                m_query = None
                try:
                    self.logger.info(f"Generating M-query for table {table.name} once to reuse")
                    m_query = self._build_m_expression(table, report_spec)
                    self.logger.info(f"Successfully generated M-query for table {table.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to generate M-query for table {table.name}: {e}")
                
                # Build table context with the data items
                context = self._build_table_context(table, report_spec, data_items, extracted_dir, m_query)
                
                # Render table template
                content = self.template_engine.render('table', context)

                # Write table file using the table name (which is already properly set)
                table_file = tables_dir / f"{table.name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Save table information as JSON in extracted directory
                if extracted_dir:

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

                    # Create a JSON representation of the table similar to table_Sheet1.json
                    # Use report name for table name in JSON if available
                    table_name = table.name
                    if report_name and table.name == "Data":
                        # Replace spaces with underscores and remove special characters
                        safe_report_name = re.sub(r'[^\w\s]', '', report_name).replace(' ', '_')
                        table_name = safe_report_name
                    
                    table_json = {
                        "source_name": table.name,
                        "name": table_name,
                        "lineage_tag": getattr(table, 'lineage_tag', None),
                        "description": getattr(table, 'description', f"Table from federated relation: {table.name}"),
                        "is_hidden": getattr(table, 'is_hidden', False),
                        "columns": []
                    }

                    # If we have data items, use them as columns
                    if data_items:
                        for item in data_items:
                            # Use the comprehensive mapping function to get both data type and summarize_by
                            data_type, summarize_by = map_cognos_to_powerbi_datatype(item, self.logger)

                            
                            # Log the data type mapping for debugging
                            self.logger.debug(f"JSON: Mapped to Power BI dataType={data_type}, summarize_by={summarize_by} for {item.get('identifier')}")
                            
                            
                            column_name = item.get('identifier', 'Column')  # Using 'identifier' field for column naming
                            is_calculation = item.get('type') == 'calculation'
                            source_column = item.get('identifier', column_name)  # Use identifier for source_column as well
                            # Use DAX formula for calculated columns if available
                            if is_calculation and column_name in calculations_map:
                                source_column = calculations_map[column_name]
                                self.logger.info(f"JSON: Using FormulaDax as source_column for calculated column {column_name}: {source_column[:30]}...")
                            
                            # Get the identifier directly for source_name
                            source_name = item.get('identifier', column_name)
                            
                            column_json = {
                                "source_name": source_name,  # Use identifier for source_name
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
                            
                            # For table columns, use source_column if available as the source_name
                            source_name = getattr(col, 'source_column', col.name)
                            
                            column_json = {
                                "source_name": source_name,  # Use source_column if available, otherwise col.name
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
                
                self.logger.info(f"Generated table file: {table_file}")
                
            except Exception as e:
                self.logger.error(f"Error generating table file for {table.name}: {e}")
                
                # Create a minimal table file with error information
                # Build content efficiently using list and join
                content_parts = [f"table '{table.name}'\n\n"]
                
                # Add columns if available
                if hasattr(table, 'columns') and table.columns:
                    for column in table.columns:
                        data_type = column.data_type.value if hasattr(column.data_type, 'value') else 'string'
                        content_parts.extend([
                            f"\n    column '{column.name}'\n",
                            f"        dataType: {data_type}\n",
                            "        summarizeBy: none\n",
                            f"        sourceColumn: {column.name}\n\n",
                            "        annotation SummarizationSetBy = User\n\n"
                        ])
                
                error_content = ''.join(content_parts)
                
                # Add partition with error information - use the table name without -partition suffix
                error_content += f"\n\n\n    partition '{table.name}' = m\n"
                error_content += f"        mode: import\n"
                error_content += f"        source = \n"
                # Create a valid M-query with proper indentation that will work with pbi-tools
                # Put the error information in a proper M-query comment
                error_content += f"            let\n"
                error_content += f"                /* ERROR: {str(e).replace('*/', '*\\/').strip()} */\n"
                error_content += f"                Source = Table.FromRows({{}})\n"
                error_content += f"            in\n"
                error_content += f"                Source\n"
                error_content += f"        \n\n\n\n"
                error_content += f"    annotation PBI_ResultType = Table\n"
                
                # Write error table file
                table_file = tables_dir / f"{table.name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(error_content)
                    
                self.logger.warning(f"Generated error table file for {table.name}: {table_file}")
    
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None, data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None, m_query: Optional[str] = None, report_name: Optional[str] = None) -> Dict[str, Any]:
        """Build context for table template"""
        # Table name is already properly set when the table was created
        
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
        
        # If we have data items, use them as columns
        if data_items:
            for item in data_items:
                # Use the comprehensive mapping function to get both data type and summarize_by
                data_type, summarize_by = map_cognos_to_powerbi_datatype(item, self.logger)
                
                # Log the data type mapping for debugging
                self.logger.debug(f"TMDL: Mapped to Power BI dataType={data_type}, summarize_by={summarize_by} for {item.get('identifier')}")
                
                # Determine the appropriate SummarizationSetBy annotation value
                summarization_set_by = 'User' if summarize_by != 'none' else 'Automatic'
                
                column_name = item.get('identifier', 'Column')  # Using 'identifier' field for more accurate column naming
                is_calculation = item.get('type') == 'calculation'
                source_column = item.get('identifier', column_name)  # Use identifier for source_column as well
                
                # For calculated columns, use FormulaDax from calculations.json if available
                if is_calculation and column_name in calculations_map:
                    source_column = calculations_map[column_name]
                    self.logger.info(f"Using FormulaDax as source_column for calculated column {column_name}: {source_column[:50]}...")
                
                # Get the identifier directly from the item for source_name to ensure we use the correct field
                source_name = item.get('identifier', column_name)
                
                column = {
                    'name': column_name,
                    'source_name': source_name,  # Use the identifier directly for source_name
                    'datatype': data_type,
                    'source_column': source_column,
                    'is_calculated': is_calculation,
                    'summarize_by': summarize_by,
                    'is_hidden': False,
                    'annotations': {'SummarizationSetBy': summarization_set_by}
                }
                columns.append(column)
        else:
            # If no data items, use the table columns
            for col in table.columns:
                column_name = col.name
                is_calculation = hasattr(col, 'expression') and bool(getattr(col, 'expression', None))
                source_column = getattr(col, 'source_column', column_name)  # Use source_column attribute if available
                
                # For calculated columns, use FormulaDax from calculations.json if available
                if is_calculation and column_name in calculations_map:
                    source_column = calculations_map[column_name]
                    self.logger.info(f"Using FormulaDax as source_column for calculated column {column_name}: {source_column[:50]}...")
                
                # For table columns, we'll use the raw column name as the source_name
                # This is the equivalent of using the identifier in the data items case
                source_name = getattr(col, 'source_column', column_name)
                
                column = {
                    'name': column_name,
                    'source_name': source_name,  # Use source_column if available, otherwise column_name
                    'datatype': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type).lower(),
                    'source_column': source_column,
                    'is_calculated': is_calculation,
                    'summarize_by': getattr(col, 'summarize_by', 'none'),
                    'is_hidden': getattr(col, 'is_hidden', False),
                    'annotations': {'SummarizationSetBy': 'Automatic'}
                }
                columns.append(column)
            
        # Use the provided M-query or generate it if not provided
        if m_query is not None:
            self.logger.info(f"Using pre-generated M-query for table {table.name}")
            m_expression = m_query
        else:
            # Fallback to generating M-query if not provided
            try:
                self.logger.warning(f"No pre-generated M-query provided for table {table.name}, generating now")
                m_expression = self._build_m_expression(table, report_spec)
            except Exception as e:
                self.logger.error(f"Error building M-expression for table {table.name}: {e}")
                m_expression = f"// ERROR: {str(e)}\nlet\n\t\t\t\tSource = Table.FromRows({{}})\n\t\t\tin\n\t\t\t\tSource"
        
        # Add partition information to the context
        partitions = []
        if m_expression:
            partitions.append({
                'name': table.name,
                'source_type': 'm',
                'expression': m_expression
            })
        
        context = {
            'name': table.name,
            'table_name': table.name,
            'source_name': table.name,
            'columns': columns,
            'partitions': partitions,
            'partition_name': f"{table.name}-partition",
            'm_expression': m_expression
        }
        
        return context
    
    def _build_m_expression(self, table: Table, report_spec: Optional[str] = None) -> str:
        """Build M expression for table partition using MQueryConverter"""
        self.logger.info(f"Building M-expression for table: {table.name}")
        
        # Check if table has source_query
        if hasattr(table, 'source_query'):
            self.logger.info(f"Table {table.name} has source query: {table.source_query[:50] if table.source_query else 'None'}...")
        else:
            self.logger.info(f"Table {table.name} does not have source_query attribute")
        
        if not self.mquery_converter:
            error_msg = f"M-query converter is not configured but required for M-query generation for table {table.name}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        
        # Use the MQueryConverter to generate the M-query
        self.logger.info(f"Generating optimized M-query for table {table.name} using M-query converter")
        return self.mquery_converter.convert_to_m_query(table, report_spec)
    
    def _generate_relationships_file(self, relationships: List[Relationship], model_dir: Path):
        """Generate relationships.tmdl file"""
        relationships_context = []
        for rel in relationships:
            relationships_context.append({
                'id': rel.name,  # Use name as the ID for the template
                'from_table': rel.from_table,
                'from_column': rel.from_column,
                'to_table': rel.to_table,
                'to_column': rel.to_column,
                'cardinality': rel.cardinality,
                'cross_filter_behavior': rel.cross_filter_direction,  # Match template's expected field name
                'is_active': rel.is_active
            })
            
        context = {
            'relationships': relationships_context
        }
        
        content = self.template_engine.render('relationship', context)
        
        relationships_file = model_dir / 'relationships.tmdl'
        with open(relationships_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            # Save relationships info as JSON
            relationship_json = {
                "relationships": relationships_context
            }
            save_json_to_extracted_dir(extracted_dir, "relationship.json", relationship_json)
            
        self.logger.info(f"Generated relationships file: {relationships_file}")
    
    def _generate_model_file(self, data_model: DataModel, model_dir: Path, report_name: Optional[str] = None):
        """Generate model.tmdl file"""
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
        if report_name:
            self.logger.info(f"Using report name '{report_name}' for model naming")
        
        # Use report name for model name if available
        model_name = data_model.name
        if report_name:
            model_name = report_name
        
        # Get table names for references and query order
        table_names = []
        for table in data_model.tables:
            table_name = table.name
            if report_name and table.name == "Data":
                # Replace spaces with underscores and remove special characters
                safe_report_name = re.sub(r'[^\w\s]', '', report_name).replace(' ', '_')
                table_name = safe_report_name
            table_names.append(table_name)
        
        self.logger.info(f"Including table references in model.tmdl: {table_names}")
            
        context = {
            'model_name': model_name,
            'culture': data_model.culture or 'en-US',
            'default_culture': data_model.culture or 'en-US',
            'tables': table_names,
            'time_intelligence_enabled': getattr(data_model, 'time_intelligence_enabled', '0'),
            'desktop_version': getattr(data_model, 'desktop_version', '2.141.1253.0 (25.03)+74f9999a1e95f78c739f3ea2b96ba340e9ba8729')
        }
        
        content = self.template_engine.render('model', context)
        
        model_file = model_dir / 'model.tmdl'
        with open(model_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save to extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        if extracted_dir:
            # Save model info as JSON
            model_json = {
                "name": data_model.name,
                "culture": data_model.culture or 'en-US',
                "compatibility_level": data_model.compatibility_level,
                "default_power_bi_data_source_version": "powerBI_V3"
            }
            save_json_to_extracted_dir(extracted_dir, "model.json", model_json)
            
        self.logger.info(f"Generated model file: {model_file}")
    
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
    
    def _generate_expressions_file(self, data_model: DataModel, model_dir: Path):
        """Generate expressions.tmdl file"""
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
