"""
Consolidated M-Query Converter for the final shared semantic model.
"""
import json
import re
import textwrap
from typing import Dict, Any, Optional

from ..models import Table
from .base_mquery_converter import BaseMQueryConverter
from pathlib import Path


class ConsolidatedMQueryConverter(BaseMQueryConverter):
    """Builds M-queries for the consolidated shared semantic model."""

    def convert_to_m_query(self, table: Table, **kwargs) -> str:
        """
        Converts a consolidated table to a targeted M-query.
        """
        self.logger.info(f"Building consolidated M-query for table: {table.name}")

        table_metadata = self._get_table_metadata(table)
        sql_query = self._build_consolidated_sql(table)

        return self._build_consolidated_m_query(sql_query, table, table_metadata)

    def _build_consolidated_sql(self, table: Table) -> str:
        """
        Builds a targeted SQL SELECT statement from the table's consolidated columns.
        """
        # The `table.columns` list is already the consolidated superset of columns
        # required by all reports.
        required_columns = [col.name for col in table.columns]
        if not required_columns:
            self.logger.warning(f"No columns to select for table '{table.name}'.")
            return f"-- No columns found for table {table.name}"

        # The table name in a consolidated model should directly map to a source table.
        # We assume the FROM clause is simply the table name.
        # A more robust solution might get the full FROM clause from package metadata.
        from_clause = f'"{table.name}"' # Basic assumption

        select_columns = [f'    "{col}"' for col in required_columns]
        sql_query = f"SELECT\n{',\\n'.join(select_columns)}\nFROM\n    {from_clause}"

        return sql_query

    def _build_consolidated_m_query(self, sql_query: str, table: Table, table_metadata: Optional[Dict]) -> str:
        """
        Builds the M-query from the targeted SQL, including transformations.
        """
        final_step = "ExecuteQuery"
        transform_types_section = ""
        type_transformations = []

        required_columns = {col.name for col in table.columns}

        if table_metadata and 'columns' in table_metadata:
            for col in table_metadata['columns']:
                col_name = col.get('name')
                if col_name in required_columns:
                    powerbi_type = col.get('powerbi_datatype', 'string')
                    mquery_type = "type text"
                    if powerbi_type.lower() == 'int64':
                        mquery_type = "Int64.Type"
                    elif powerbi_type.lower() == 'double':
                        mquery_type = "type number"
                    elif powerbi_type.lower() == 'datetime':
                        mquery_type = "type datetime"
                    
                    type_transformations.append(f'{{"{col_name}", {mquery_type}}}')

        if type_transformations:
            transformations_list = ", ".join(type_transformations)
            transform_types_section = f""",
    #"Changed Type" = Table.TransformColumnTypes(ExecuteQuery, {{{transformations_list}}})"""
            final_step = "#\"Changed Type\""

        m_query_template = f'''let
    Source = Sql.Database(#"DB Server", #"DB Name"),
    ExecuteQuery = Value.NativeQuery(Source, "{sql_query.replace('"', '""')}", null, [EnableFolding=true]){transform_types_section}
in
    {final_step}'''
        return textwrap.dedent(m_query_template).strip()

    def _get_table_metadata(self, table: Table) -> Optional[Dict]:
        """Gets table metadata from the extracted package files."""
        # This assumes table metadata is stored in query_subjects.json for packages
        qs_path = Path(self.output_path) / "extracted" / "query_subjects.json"
        if not qs_path.exists():
            return None
        try:
            with open(qs_path, 'r') as f:
                query_subjects = json.load(f)
            return next((qs for qs in query_subjects if qs['name'] == table.name), None)
        except Exception as e:
            self.logger.error(f"Error reading {qs_path}: {e}")
            return None 