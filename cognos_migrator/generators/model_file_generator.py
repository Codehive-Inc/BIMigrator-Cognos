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


class ModelFileGenerator:
    """Generator for Power BI model files (database.tmdl, tables/*.tmdl, etc.)"""
    
    def __init__(self, template_engine: TemplateEngine, mquery_converter: Optional[MQueryConverter] = None):
        """
        Initialize the model file generator
        
        Args:
            template_engine: Template engine for rendering templates
            mquery_converter: Optional MQueryConverter for generating M-queries
        """
        self.template_engine = template_engine
        self.mquery_converter = mquery_converter
        self.logger = logging.getLogger(__name__)
    
    def generate_model_files(self, data_model: DataModel, output_dir: Path, report_spec: Optional[str] = None) -> Path:
        """
        Generate model files (database, tables, relationships)
        
        Args:
            data_model: Data model object
            output_dir: Output directory
            report_spec: Optional report specification XML
            
        Returns:
            Path to the model directory
        """
        model_dir = output_dir / 'Model'
        model_dir.mkdir(exist_ok=True)
        
        # Generate database.tmdl
        self._generate_database_file(data_model, model_dir)
        
        # Generate table files
        self._generate_table_files(data_model.tables, model_dir, report_spec)
        
        # Generate relationships file
        if data_model.relationships:
            self._generate_relationships_file(data_model.relationships, model_dir)
        
        # Generate model.tmdl
        self._generate_model_file(data_model, model_dir)
        
        # Generate culture.tmdl
        self._generate_culture_file(data_model, model_dir)
        
        # Generate expressions.tmdl
        self._generate_expressions_file(data_model, model_dir)
        
        self.logger.info(f"Generated model files in: {model_dir}")
        return model_dir
    
    def _generate_database_file(self, data_model: DataModel, model_dir: Path):
        """Generate database.tmdl file"""
        context = {
            'name': data_model.name,
            'compatibility_level': data_model.compatibility_level,
            'model_name': data_model.name
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
    
    def _generate_table_files(self, tables: List[Table], model_dir: Path, report_spec: Optional[str] = None):
        """Generate table/*.tmdl files"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        # Get extracted directory if applicable
        extracted_dir = get_extracted_dir(model_dir)
        
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
                
                # Build table context with the data items
                context = self._build_table_context(table, report_spec, data_items, extracted_dir)
                
                # Render table template
                content = self.template_engine.render('table', context)

                # Write table file
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
                    table_json = {
                        "source_name": table.name,
                        "name": table.name,
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
                    
                    # Save as table_[TableName].json
                    save_json_to_extracted_dir(extracted_dir, f"table_{table.name}.json", table_json)
                    
                    # Also save as table.json for the first table
                    if tables.index(table) == 0:
                        save_json_to_extracted_dir(extracted_dir, "table.json", table_json)
                
                self.logger.info(f"Generated table file: {table_file}")
                
            except Exception as e:
                self.logger.error(f"Error generating table file for {table.name}: {e}")
                
                # Create a minimal table file with error information
                error_content = f"table '{table.name}'\n\n"
                
                # Add columns if available
                if hasattr(table, 'columns') and table.columns:
                    for column in table.columns:
                        error_content += f"\n    column '{column.name}'\n"
                        error_content += f"        dataType: {column.data_type.value if hasattr(column.data_type, 'value') else 'string'}\n"
                        error_content += f"        summarizeBy: none\n"
                        error_content += f"        sourceColumn: {column.name}\n\n"
                        error_content += f"        annotation SummarizationSetBy = User\n\n"
                
                # Add partition with error information
                error_content += f"\n\n\n    partition '{table.name}-partition' = m\n"
                error_content += f"        mode: import\n"
                error_content += f"        source = \n"
                error_content += f"            // ERROR: Failed to generate M-query for {table.name}\n"
                error_content += f"// {str(e)}\n"
                error_content += f"let\n\t\t\t\tSource = Table.FromRows({{}})\n\t\t\tin\n\t\t\t\tSource\n"
                error_content += f"        \n\n\n\n"
                error_content += f"    annotation PBI_ResultType = Table\n"
                
                # Write error table file
                table_file = tables_dir / f"{table.name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(error_content)
                    
                self.logger.warning(f"Generated error table file for {table.name}: {table_file}")
    
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None, data_items: Optional[List[Dict]] = None, extracted_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Build context for table template"""
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
        else:
            # If no data items, use the table columns
            for col in table.columns:
                column_name = col.name
                is_calculation = hasattr(col, 'expression') and bool(getattr(col, 'expression', None))
                source_column = column_name
                
                # For calculated columns, use FormulaDax from calculations.json if available
                if is_calculation and column_name in calculations_map:
                    source_column = calculations_map[column_name]
                    self.logger.info(f"Using FormulaDax as source_column for calculated column {column_name}: {source_column[:50]}...")
                
                column = {
                    'name': column_name,
                    'source_name': column_name,
                    'datatype': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type).lower(),
                    'source_column': source_column,
                    'is_calculated': is_calculation,
                    'summarize_by': getattr(col, 'summarize_by', 'none'),
                    'is_hidden': getattr(col, 'is_hidden', False),
                    'annotations': {'SummarizationSetBy': 'Automatic'}
                }
                columns.append(column)
            
        # Build M expression for table partition
        try:
            m_expression = self._build_m_expression(table, report_spec)
        except Exception as e:
            self.logger.error(f"Error building M-expression for table {table.name}: {e}")
            m_expression = f"// ERROR: {str(e)}\nlet\n\t\t\t\tSource = Table.FromRows({{}})\n\t\t\tin\n\t\t\t\tSource"
        
        context = {
            'table_name': table.name,
            'source_name': table.name,
            'columns': columns,
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
    
    def _generate_model_file(self, data_model: DataModel, model_dir: Path):
        """Generate model.tmdl file"""
        context = {
            'model_name': data_model.name,
            'culture': data_model.culture or 'en-US'
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
        version = getattr(data_model, 'version', '1.0') if hasattr(data_model, 'version') else '1.0'
        
        context = {
            'culture': data_model.culture or 'en-US',
            'version': version
        }
        
        content = self.template_engine.render('culture', context)
        
        culture_file = model_dir / 'cultures' / 'culture.tmdl'
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
