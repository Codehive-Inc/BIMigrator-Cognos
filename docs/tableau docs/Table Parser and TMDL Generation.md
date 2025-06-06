# Table Parser and TMDL Generation

This document serves as a developer guide for extracting table information from Tableau workbooks and generating corresponding TMDL files for Power BI.

## Code Structure

### 1. Parser Components

```
src/parsers/
├── table_parser.py          # Main table parsing logic
├── column_parser.py         # Column and measure extraction
└── connections/
    ├── base_connection.py   # Abstract connection class
    ├── connection_factory.py # Connection type resolver
    ├── excel_parser.py      # Excel-specific parsing
    └── sql_parser.py        # SQL-specific parsing
```

### 2. Generator Components

```
src/generators/
├── tmdl_generator.py           # Main TMDL generation
├── table_template_generator.py  # Table TMDL templates
└── m_code_generator.py         # Power Query M code
```

### 3. Helper Components

```
src/helpers/
└── calculation_tracker.py    # Calculation tracking and JSON storage
```

### 4. Key Classes and Methods

#### TableParser
```python
class TableParser:
    def __init__(self, workbook_path: Path, output_dir: Path):
        self.workbook = workbook_path
        self.output_dir = output_dir
        self.calculation_tracker = CalculationTracker(output_dir)

    def extract_all_tables(self) -> List[Table]:
        # Extract tables from workbook
        pass

    def process_datasource(self, datasource: Element) -> Table:
        # Process single datasource
        pass
```

#### ColumnParser
```python
class ColumnParser:
    def extract_columns_and_measures(self, datasource: Element) -> Tuple[List[Column], List[Measure]]:
        # Extract columns and measures
        pass

    def process_calculation(self, calc_field: Element) -> None:
        # Process calculated field
        pass
```

#### ConnectionFactory
```python
class ConnectionFactory:
    @staticmethod
    def create_parser(connection_type: str) -> BaseConnection:
        # Create appropriate connection parser
        pass
```

#### TMDLGenerator
```python
class TMDLGenerator:
    def generate_table_tmdl(self, table: Table) -> str:
        # Generate TMDL for table
        pass

    def generate_relationships_tmdl(self, relationships: List[Relationship]) -> str:
        # Generate TMDL for relationships
        pass
```

### 5. Data Models

#### Table Model
```python
class Table:
    name: str
    source_name: str
    columns: List[Column]
    measures: List[Measure]
    partitions: List[Partition]
    connection: Dict[str, Any]
```

#### Column Model
```python
class Column:
    name: str
    data_type: str
    source_column: str
    is_hidden: bool
    format_string: str
    annotations: Dict[str, str]
```

#### Measure Model
```python
class Measure:
    name: str
    expression: str
    format_string: str
    display_folder: str
```

#### Partition Model
```python
class Partition:
    name: str
    mode: str
    source_type: str
    expression: str
```

## 1. Table Parsing Process

### 1.1 Table Extraction
The `TableParser` extracts table information through these steps:

1. **Datasource Identification**
   - Scans for `<datasource>` elements in the TWB file
   - Filters for primary datasources (`hasconnection='true'`)
   - Supports multiple datasources in a single workbook

2. **Connection Parsing**
   - Uses `ConnectionParserFactory` to create appropriate parser:
     - `ExcelParser`: For Excel file connections
     - `SQLParser`: For SQL database connections
   - Each parser extracts connection-specific details:
     ```json
     {
       "connection_type": "excel",
       "filename": "path/to/file.xlsx",
       "sheet_name": "Sheet1",
       "server": "",
       "database": "",
       "trusted_connection": true
     }
     ```

### 1.2 Column Extraction
Columns are extracted using the `ColumnParser`:

1. **Column Types**
   - Regular columns from source
   - Calculated columns
   - Measures

2. **Column Properties**
   ```json
   {
     "name": "Sales",
     "dataType": "double",
     "sourceColumn": "Sales",
     "formatString": "0.00",
     "isHidden": false,
     "summarizeBy": "sum"
   }
   ```

3. **Calculation Tracking**
   - Tracks all calculations in `calculations.json`
   - Stores original Tableau and converted DAX expressions
   - Maintains calculation names and types

### 1.3 Partition Information
Extracts partition details for each table:

```json
{
  "name": "Sheet1",
  "mode": "import",
  "source": {
    "type": "m",
    "expression": "let\n  Source = Excel.Workbook(...)"
  }
}
```

## 2. TMDL Generation

### 2.1 Table TMDL Structure
The `TableTemplateGenerator` creates TMDL files with:

1. **Table Definition**
   ```json
   {
     "name": "Sales",
     "columns": [...],
     "partitions": [...],
     "measures": [...],
     "annotations": [...]
   }
   ```

2. **M Code Generation**
   - Uses `MCodeGenerator` to create Power Query expressions
   - Handles different source types:
     - Excel: Creates Excel.Workbook() calls
     - SQL: Creates Sql.Database() calls

3. **Measure Generation**
   - Converts Tableau calculations to DAX
   - Handles aggregations and complex expressions
   - Sets appropriate measure properties

### 2.2 Connection Types

1. **Excel Connections**
   - Extracts sheet names and ranges
   - Handles named ranges and tables
   - Supports different Excel versions

2. **SQL Connections**
   - Supports multiple database types
   - Extracts connection strings
   - Handles authentication methods
   - Processes custom SQL queries

### 2.3 Special Cases

1. **Federated Data Sources**
   - Handles multiple connection types
   - Merges data from different sources
   - Preserves relationships

2. **Custom SQL**
   - Processes custom SQL queries
   - Handles parameters and variables
   - Converts to appropriate M expressions

## 3. Output Structure

```
output/
├── <workbook_name>/
│   ├── pbit/
│   │   ├── Model/
│   │   │   ├── tables/
│   │   │   │   └── <table_name>.tmdl
│   │   │   └── relationships.tmdl
│   │   └── Version.txt
│   └── extracted/
│       └── calculations.json
```

## 4. Configuration

The process is controlled by `config/twb-to-pbi.yaml`:

```yaml
Templates:
  mappings:
    table:
      template: templates/table.tmdl.jinja
      output: Model/tables/{name}.tmdl
    relationship:
      template: templates/relationships.tmdl.jinja
      output: Model/relationships.tmdl

Connections:
  excel:
    supported_versions: ["xlsx", "xlsm"]
  sql:
    supported_types: ["sqlserver", "mysql", "postgresql"]
```

## 5. Error Handling

1. **Connection Errors**
   - Invalid connection strings
   - Missing files
   - Authentication failures

2. **Parsing Errors**
   - Invalid XML structure
   - Missing required attributes
   - Unsupported features

3. **Generation Errors**
   - Formula conversion failures
   - Invalid M code generation
   - Template rendering errors
