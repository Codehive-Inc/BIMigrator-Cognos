"""
Model file generator for Power BI projects.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..models import DataModel, Table, Relationship
from ..converters import MQueryConverter
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
            
        self.logger.info(f"Generated database file: {database_file}")
    
    def _generate_table_files(self, tables: List[Table], model_dir: Path, report_spec: Optional[str] = None):
        """Generate table/*.tmdl files"""
        tables_dir = model_dir / 'tables'
        tables_dir.mkdir(exist_ok=True)
        
        for table in tables:
            try:
                self.logger.warning(f"Using report_spec for table {table.name}: {report_spec is not None}")
                
                # Build table context
                context = self._build_table_context(table, report_spec)
                
                # Render table template
                content = self.template_engine.render('table', context)
                
                # Write table file
                table_file = tables_dir / f"{table.name}.tmdl"
                with open(table_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
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
    
    def _build_table_context(self, table: Table, report_spec: Optional[str] = None) -> Dict[str, Any]:
        """Build context for table template"""
        columns = []
        for col in table.columns:
            column = {
                'name': col.name,
                'data_type': col.data_type.value if hasattr(col.data_type, 'value') else str(col.data_type),
                'source_column': col.name
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
            
        self.logger.info(f"Generated model file: {model_file}")
    
    def _generate_culture_file(self, data_model: DataModel, model_dir: Path):
        """Generate culture.tmdl file"""
        context = {
            'culture': data_model.culture or 'en-US'
        }
        
        content = self.template_engine.render('culture', context)
        
        culture_file = model_dir / 'cultures' / 'culture.tmdl'
        culture_file.parent.mkdir(exist_ok=True)
        with open(culture_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated culture file: {culture_file}")
    
    def _generate_expressions_file(self, data_model: DataModel, model_dir: Path):
        """Generate expressions.tmdl file"""
        context = {}
        
        content = self.template_engine.render('expressions', context)
        
        expressions_file = model_dir / 'expressions.tmdl'
        with open(expressions_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        self.logger.info(f"Generated expressions file: {expressions_file}")
