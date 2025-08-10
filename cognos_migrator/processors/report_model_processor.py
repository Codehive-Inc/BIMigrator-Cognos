import json
from pathlib import Path
from typing import List, Dict, Any

from cognos_migrator.models import DataModel, Table, Column

class ReportModelProcessor:
    def __init__(self, extracted_dir: Path):
        self.extracted_dir = extracted_dir
        self.report_queries_path = self.extracted_dir / "report_queries.json"

    def process(self) -> DataModel:
        queries = self._load_report_queries()
        tables = self._create_tables_from_queries(queries)
        return DataModel(name="ReportDataModel", tables=tables)

    def _load_report_queries(self) -> List[Dict[str, Any]]:
        if not self.report_queries_path.exists():
            raise FileNotFoundError(f"{self.report_queries_path} not found.")
        with open(self.report_queries_path, 'r') as f:
            return json.load(f)

    def _create_tables_from_queries(self, queries: List[Dict[str, Any]]) -> List[Table]:
        tables = []
        for query in queries:
            columns = self._create_columns_from_data_items(query.get("data_items", []))
            table = Table(
                name=query.get("name"),
                columns=columns,
                description=f"Table created from query: {query.get('name')}",
                metadata={"original_query_name": query.get("name")}
            )
            tables.append(table)
        return tables

    def _create_columns_from_data_items(self, data_items: List[Dict[str, Any]]) -> List[Column]:
        columns = []
        for item in data_items:
            column = Column(
                name=item.get("name"),
                data_type="string",  # Placeholder, will need type mapping
                source_column=item.get("expression")
            )
            columns.append(column)
        return columns 