# M-Query Converters

This directory contains converters for transforming Cognos elements to Power BI equivalents, with a specific focus on M-query generation.

## M-Query Converter Architecture

The M-query converter system has been designed to support different migration types in the BIMigrator-Cognos system:

1. **BaseMQueryConverter** - Abstract base class that defines the interface and common functionality for all M-query converters
2. **ReportMQueryConverter** - Specialized converter for report migrations that reads from "report_queries.json"
3. **PackageMQueryConverter** - Specialized converter for package migrations that reads from package metadata files
4. **MQueryConverter** - Legacy converter (maintained for backward compatibility)

## Usage

### Report Migration

For report migrations, use the `ReportMQueryConverter`:

```python
from cognos_migrator.converters import ReportMQueryConverter

# Initialize with output path to access extracted report queries
converter = ReportMQueryConverter(output_path="/path/to/output")

# Convert table to M-query
m_query = converter.convert_to_m_query(table, report_spec)
```

### Package Migration

For package migrations, use the `PackageMQueryConverter`:

```python
from cognos_migrator.converters import PackageMQueryConverter

# Initialize with output path to access extracted package metadata
converter = PackageMQueryConverter(output_path="/path/to/output")

# Convert table to M-query
m_query = converter.convert_to_m_query(table, package_spec)
```

## Implementation Details

### Report M-Query Generation

The report M-query converter:
- Reads from "report_queries.json" in the extracted directory
- Extracts SELECT, FROM, and WHERE clauses from report queries
- Builds SQL queries from the extracted information
- Converts SQL to M-query format

### Package M-Query Generation

The package M-query converter:
- Reads from "query_subjects.json" and "query_items.json" in the extracted directory
- Uses table source_query if available
- Otherwise builds SQL from package metadata
- Converts SQL to M-query format

## Extension

To add support for additional migration types:
1. Create a new class that inherits from `BaseMQueryConverter`
2. Implement the `convert_to_m_query` method
3. Add any specialized methods needed for that migration type
4. Update the `__init__.py` file to expose the new converter
