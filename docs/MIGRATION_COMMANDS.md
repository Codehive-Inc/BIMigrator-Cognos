# Cognos to Power BI Migration Commands

This document provides instructions for running different types of migrations using the BIMigrator-Cognos tool.

## Prerequisites

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Ensure the DAX LLM API is running (default: http://localhost:8080)
   - You can set a custom URL using the environment variable: `export DAX_API_URL=http://your-dax-api-url`

## Direct Python Usage

You can use the migration functions directly in Python without needing a separate script. Here are examples of how to use each function:

### 0. Migrate a Cognos Package

Migrates a Cognos package (FM model) to Power BI format.

```python
from cognos_migrator.migrations.package import migrate_package_with_explicit_session

result = migrate_package_with_explicit_session(
    package_path="/path/to/package.xml",  # Path to the FM model XML file
    output_path="/path/to/output",
    cognos_url="http://cognos-url/api/v1",
    session_key="CAM session-key-value",
    auth_key="IBM-BA-Authorization"  # Optional
)

print(f"Package migration successful: {result}")
```

### 1. Migrate a Cognos Module

Migrates a Cognos module (package) to Power BI format.

```python
from cognos_migrator.migrations.module import migrate_module_with_explicit_session

result = migrate_module_with_explicit_session(
    module_id="/path/to/module.xml",
    output_path="/path/to/output",
    cognos_url="http://cognos-url/api/v1",
    session_key="CAM session-key-value",
    folder_id=None,  # Optional
    cpf_file_path=None,  # Optional
    auth_key="IBM-BA-Authorization"  # Optional
)

print(f"Migration successful: {result}")
```

### 2. Migrate a Cognos Module with Specific Reports

Migrates a Cognos module with specific reports instead of requiring a folder.

```python
from cognos_migrator.migrations.module import migrate_module_with_reports_explicit_session

result = migrate_module_with_reports_explicit_session(
    module_id="/path/to/module.xml",
    output_path="/path/to/output",
    cognos_url="http://cognos-url/api/v1",
    session_key="CAM session-key-value",
    report_ids=["report_id1", "report_id2"],  # Optional
    cpf_file_path=None,  # Optional
    auth_key="IBM-BA-Authorization"  # Optional
)

print(f"Migration successful: {result}")
```

### 3. Migrate a Single Cognos Report

Migrates a single Cognos report to Power BI format.

```python
from cognos_migrator.migrations.report import migrate_single_report_with_explicit_session

result = migrate_single_report_with_explicit_session(
    report_id="report_id",
    output_path="/path/to/output",
    cognos_url="http://cognos-url/api/v1",
    session_key="CAM session-key-value",
    cpf_file_path=None,  # Optional
    auth_key="IBM-BA-Authorization"  # Optional
)

print(f"Migration successful: {result}")
```

### 4. Post-Process a Migrated Module

Post-processes a migrated module, consolidating tables into model.tmdl.

```python
from cognos_migrator.main import post_process_module_with_explicit_session

result = post_process_module_with_explicit_session(
    module_id="module_id",
    output_path="/path/to/output",
    cognos_url="http://cognos-url/api/v1",
    session_key="CAM session-key-value",
    successful_report_ids=["report_id1", "report_id2"],  # Optional
    auth_key="IBM-BA-Authorization"  # Optional
)

print(f"Post-processing successful: {result}")
```

## Command-Line Examples

You can also run these functions directly from the command line using Python's `-c` option:

### Example: Migrating the Energy Share Package

```bash
python -c "from cognos_migrator.migrations.module import migrate_module_with_explicit_session; print(migrate_module_with_explicit_session('./examples/packages/FM Models/Energy_Share.xml', './output/output_energy_share_test', 'http://20.244.32.126:9300/api/v1', 'CAM MTsxMDE6ZGJiODNkYzktOWUzZS04ZGVmLTFmMTAtNjE0ODk4ZGU2ZGRhOjIwODUxMjA4MzE7MDszOzA7'))"
```

## Enhanced M-Query Generation

The migration now uses the enhanced DAX LLM API for M-Query generation with the following improvements:

1. **Structured Source Information**:
   - Source type detection (SQL Server, Cognos FM, etc.)
   - Connection details extraction

2. **Report Logic Extraction**:
   - Filters from report specifications
   - Calculated columns and measures

3. **Relationship Information**:
   - Table relationships with join types

4. **Enhanced Options**:
   - Query folding preference: `BestEffort` (default)
   - Error handling strategy: `RemoveErrors` (default)
   - Documentation comments: Enabled by default

5. **Validation and Explanation**:
   - M-Query validation
   - Explanation of generated queries
   - Fallback to basic endpoint if enhanced endpoint fails

## Testing the Enhanced M-Query Generation

To test the enhanced M-Query generation with a specific table:

```python
from cognos_migrator.converters.mquery_converter import MQueryConverter
from cognos_migrator.llm_service import LLMServiceClient
from cognos_migrator.models import Table, Column, DataType

# Create a test table
table = Table(
    name="SalesData",
    columns=[
        Column(name="OrderID", data_type=DataType.INTEGER),
        Column(name="CustomerID", data_type=DataType.INTEGER),
        Column(name="ProductID", data_type=DataType.INTEGER),
        Column(name="OrderDate", data_type=DataType.DATETIME),
        Column(name="Quantity", data_type=DataType.INTEGER),
        Column(name="UnitPrice", data_type=DataType.DECIMAL),
    ],
    source_query="SELECT * FROM Sales.Orders WHERE OrderDate > '2023-01-01'",
    database_type="SqlServer",
    database_name="SalesDB",
    schema_name="Sales"
)

# Create LLM service client and M-Query converter
llm_client = LLMServiceClient(api_url="http://localhost:8080")
mquery_converter = MQueryConverter(llm_client)

# Generate M-Query
m_query = mquery_converter.convert_to_m_query(table)
print(m_query)
```

## Troubleshooting

If you encounter issues with the migration:

1. Check the logs for detailed error messages
2. Verify that the Cognos session key is valid
3. Ensure the DAX LLM API is running and accessible
4. Check that the module or report IDs are correct
5. Verify that the output directory exists and is writable
