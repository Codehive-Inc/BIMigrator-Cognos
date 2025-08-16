import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import re

from cognos_migrator.models import DataModel, Table, Column
from cognos_migrator.utils.date_table_utils import create_central_date_table, create_date_relationships

class ReportModelProcessor:
    def __init__(self, extracted_dir: Path, logger=None):
        self.extracted_dir = extracted_dir
        self.report_queries_path = self.extracted_dir / "report_queries.json"
        self.logger = logger or logging.getLogger(__name__)

    def process(self) -> DataModel:
        queries = self._load_report_queries()
        tables = self._create_tables_from_source_tables(queries)
        data_model = DataModel(name="ReportDataModel", tables=tables)
        
        # Create a central date table for the report data model
        create_central_date_table(data_model, self.logger)
        
        # Create relationships between datetime columns and the central date table
        for table in tables:
            create_date_relationships(table, data_model, self.logger)
            
        return data_model

    def _load_report_queries(self) -> List[Dict[str, Any]]:
        if not self.report_queries_path.exists():
            raise FileNotFoundError(f"{self.report_queries_path} not found.")
        with open(self.report_queries_path, 'r') as f:
            return json.load(f)

    def _extract_source_table_from_expression(self, expression: str) -> str:
        """Extracts the source table name from a column expression."""
        if not expression or '.' not in expression:
            return None
        # This regex looks for a pattern like [Namespace].[TableName] and extracts TableName.
        match = re.match(r'^\[[^\]]+\]\.\[([^\]]+)\]', expression)
        if match:
            return match.group(1)
        # Handle cases that are not in the standard format (e.g., calculated columns)
        return None

    def _create_tables_from_source_tables(self, queries: List[Dict[str, Any]]) -> List[Table]:
        """Creates a list of tables, with each table corresponding to a unique source."""
        tables_dict: Dict[str, Table] = {}
        
        for query in queries:
            original_query_name = query.get("name")
            for item in query.get("data_items", []):
                expression = item.get("expression")
                source_table_name = self._extract_source_table_from_expression(expression)
                
                if not source_table_name:
                    continue
                
                if source_table_name not in tables_dict:
                    tables_dict[source_table_name] = Table(
                        name=source_table_name,
                        columns=[],
                        description=f"Table created from source: {source_table_name}",
                        # Add metadata to link back to the original report query
                        metadata={"original_query_name": original_query_name}
                    )
                
                column = Column(
                    name=item.get("name"),
                    data_type="string",
                    source_column=expression
                )
                
                if not any(c.name == column.name for c in tables_dict[source_table_name].columns):
                    tables_dict[source_table_name].columns.append(column)

        return list(tables_dict.values()) 