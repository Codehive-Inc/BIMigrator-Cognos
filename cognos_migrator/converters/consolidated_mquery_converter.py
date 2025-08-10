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
        # De-duplicate column names while preserving order
        unique_columns = list(dict.fromkeys([col.name for col in table.columns]))

        if not unique_columns:
            self.logger.warning(f"No columns to select for table '{table.name}'.")
            return f"-- No columns found for table {table.name}"

        from_clause = f'"{table.name}"'
        select_columns_str = ", ".join([f'"{col}"' for col in unique_columns])

        # Construct a clean, single-line SQL string
        sql_query = f"SELECT {select_columns_str} FROM {from_clause}"
        return sql_query

    def _build_consolidated_m_query(self, sql_query: str, table: Table, table_metadata: Optional[Dict]) -> str:
        """
        Builds the M-query from the targeted SQL, including transformations,
        with correct indentation for TMDL.
        """
        escaped_sql_query = sql_query.replace('"', '""')

        # Base steps for the M-query
        steps = [
            f'Source = Sql.Database(#"DB Server", #"DB Name")',
            f'ExecuteQuery = Value.NativeQuery(Source, "{escaped_sql_query}", null, [EnableFolding=true])',
            f'#"Removed Errors" = Table.RemoveRowsWithErrors(ExecuteQuery)'
        ]
        last_step_name = '#"Removed Errors"'

        # Build type transformations if metadata is available
        type_transformations = []
        if table_metadata and 'columns' in table_metadata:
            for col in table_metadata['columns']:
                col_name = col.get('name')
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
            transformations_list_str = ", ".join(type_transformations)
            type_step_str = f'#"Changed Type" = Table.TransformColumnTypes({last_step_name}, {{{transformations_list_str}}})'
            steps.append(type_step_str)
            last_step_name = '#"Changed Type"'

        # Join the steps with the correct indentation for the let expression
        steps_str = (",\n" + " " * 20).join(steps)

        # Use a simple f-string with hardcoded spaces to guarantee the correct final format.
        m_query = f"""
                let
                    {steps_str}
                in
                    {last_step_name}"""
        return m_query

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