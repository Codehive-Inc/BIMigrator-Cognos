# Star Schema Migration Paths Documentation

## Overview

This document provides a comprehensive guide to all migration paths available in the **Star Schema** model handling approach. The star schema approach creates dimension tables that consolidate related data from multiple source tables using composite keys.

## Configuration Settings

The migration path is determined by two key settings in `settings.json`:

```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "Dim_",
    "data_load_mode": "import|direct_query", 
    "model_handling": "star_schema"
  }
}
```

## Migration Path Decision Tree

```
settings.json
├── staging_tables.enabled = false → **NO PROCESSING** (return original model)
├── staging_tables.model_handling = "none" → **NO PROCESSING** (return original model)
└── staging_tables.model_handling = "star_schema"
    ├── data_load_mode = "import" → **STAR SCHEMA + IMPORT**
    ├── data_load_mode = "direct_query" → **STAR SCHEMA + DIRECTQUERY**
    └── data_load_mode = <other> → **FALLBACK TO IMPORT** (with warning)
```

## Execution Paths

### 1. Star Schema + Import Mode

**Path**: `StagingTableHandler` → `StarSchemaHandler.process_import_mode()`

**Purpose**: Creates dimension tables optimized for Power BI import mode with Power Query transformations.

**Process Flow**:
1. **Relationship Analysis**
   - Load SQL relationships from `sql_filtered_relationships.json` (preferred)
   - Fallback to basic relationships from data model
   - Identify complex relationships requiring dimension tables

2. **Relationship Grouping**
   - Group relationships by connected table pairs
   - Create dimension table for each relationship group

3. **Dimension Table Creation**
   - **Table Naming**: `{naming_prefix}{from_table}_{to_table}` (e.g., `Dim_ITEM_SITE_EXTRACT_STORAGE_LOCATION`)
   - **Column Selection**: Extract unique columns from both source tables
   - **Composite Key**: Generate composite key column (e.g., `ITEM_NUMBER_SITE_NUMBER_Key`)
   - **M-Query Generation**: Create Power Query with `Table.Combine` + `Table.Distinct`

4. **M-Query Structure (Import Mode)**:
   ```powerquery
   let
       Source1 = Table.SelectColumns(TABLE1, {"COL1", "COL2", ...}),
       Source2 = Table.SelectColumns(TABLE2, {"COL1", "COL2", ...}),
       Combined = Table.Combine({Source1, Source2}),
       Distinct = Table.Distinct(Combined),
       AddedCompositeKey = Table.AddColumn(Distinct, "COMPOSITE_KEY", 
           each [COL1] & "_" & [COL2], type text)
   in
       AddedCompositeKey
   ```

5. **Output**:
   - **Partition Mode**: `import`
   - **Tables**: Original tables + dimension tables with `Dim_` prefix
   - **Relationships**: Updated to use dimension tables as intermediaries

### 2. Star Schema + DirectQuery Mode

**Path**: `StagingTableHandler` → `StarSchemaHandler.process_direct_query_mode()`

**Purpose**: Creates dimension tables optimized for DirectQuery with query folding to the source database.

**Process Flow**:
1. **Reuse Import Logic**: Calls `process_import_mode()` for table structure
2. **Partition Mode Override**: Updates all dimension tables to `partition_mode = "directQuery"`
3. **Future Optimizations** (TODO):
   - Replace Power Query with native SQL JOINs
   - Use SQL `CONCAT` or `||` for composite keys
   - Replace `Table.Combine` with `UNION ALL`
   - Minimize transformations for query folding

**M-Query Structure (Current DirectQuery)**:
```powerquery
let
    // Same Power Query logic as import mode
    // But with partition mode: directQuery for query folding
in
    AddedCompositeKey
```

**Future DirectQuery M-Query (Planned)**:
```powerquery
let
    Source = Oracle.Database("server", [Query="
        SELECT DISTINCT 
            COL1, COL2, ...,
            COL1 || '_' || COL2 AS COMPOSITE_KEY
        FROM (
            SELECT COL1, COL2, ... FROM TABLE1
            UNION ALL
            SELECT COL1, COL2, ... FROM TABLE2
        ) combined_data
        WHERE COL1 IS NOT NULL AND COL2 IS NOT NULL
    "])
in
    Source
```

**Output**:
- **Partition Mode**: `directQuery`
- **Tables**: Original tables + dimension tables with `Dim_` prefix
- **Query Folding**: Optimized for database-side processing

## Key Components

### StagingTableHandler (Orchestrator)
- **File**: `cognos_migrator/generators/staging_table_handler.py`
- **Role**: Main entry point that routes to appropriate handler
- **Decision Logic**: Based on `model_handling` and `data_load_mode` settings

### StarSchemaHandler (Implementation)
- **File**: `cognos_migrator/generators/staging_handlers/star_schema_handler.py`
- **Role**: Implements star schema dimension table creation
- **Key Methods**:
  - `process_import_mode()`: Import-optimized dimension tables
  - `process_direct_query_mode()`: DirectQuery-optimized dimension tables

### BaseHandler (Common Functionality)
- **File**: `cognos_migrator/generators/staging_handlers/base_handler.py`
- **Role**: Shared functionality for all handlers
- **Features**:
  - SQL relationship loading
  - Settings management
  - Common utilities

## Data Sources

### SQL Relationships (Preferred)
- **File**: `test_output/.../extracted/sql_filtered_relationships.json`
- **Content**: Detailed relationship metadata with join types and composite keys
- **Advantages**: Accurate join conditions, proper join types (INNER, LEFT, RIGHT, FULL)

### Basic Relationships (Fallback)
- **File**: Data model relationships
- **Content**: Simple relationship definitions
- **Limitations**: Generic join keys ("STOP"), limited metadata

## Configuration Examples

### Example 1: Star Schema + Import
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "Dim_",
    "data_load_mode": "import",
    "model_handling": "star_schema"
  }
}
```
**Result**: Dimension tables with Power Query transformations, optimized for data import.

### Example 2: Star Schema + DirectQuery
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "Dim_",
    "data_load_mode": "direct_query", 
    "model_handling": "star_schema"
  }
}
```
**Result**: Dimension tables with query folding optimizations, data stays in source database.

### Example 3: Disabled Processing
```json
{
  "staging_tables": {
    "enabled": false,
    "model_handling": "none"
  }
}
```
**Result**: No staging tables created, original model returned unchanged.

## Output Artifacts

### Generated Files
1. **Dimension Table TMDL**: `{table_name}.tmdl` files with M-query definitions
2. **Table JSON**: `table_{table_name}.json` with metadata and partition info
3. **Relationships**: Updated relationship definitions using dimension tables

### Naming Conventions
- **Dimension Tables**: `{naming_prefix}{source_table1}_{source_table2}`
- **Composite Keys**: `{column1}_{column2}_..._Key`
- **M-Query Steps**: Descriptive names like `"Added Composite Key"`

## Performance Considerations

### Import Mode
- **Pros**: Full Power Query transformation capabilities, complex calculations
- **Cons**: Data stored in Power BI model, memory usage, refresh time

### DirectQuery Mode  
- **Pros**: Real-time data, reduced memory usage, query folding to database
- **Cons**: Limited transformations, dependent on source database performance

## Troubleshooting

### Common Issues
1. **No Dimension Tables Created**: Check if complex relationships exist
2. **Generic Join Keys**: Verify SQL relationships are available and loaded
3. **Performance Issues**: Consider switching between import/DirectQuery modes
4. **Memory Issues**: Use DirectQuery for large datasets

### Debug Logging
Enable detailed logging to trace execution:
```python
self.logger.info(f"Processing data model with 'star_schema' + '{data_load_mode}' approach")
```

## Future Enhancements

### DirectQuery Optimizations (Planned)
1. **Native SQL Generation**: Replace Power Query with database-native SQL
2. **Query Folding**: Ensure all operations can be pushed to source database  
3. **Performance Tuning**: Optimize for specific database engines (Oracle, SQL Server, etc.)
4. **Composite Key Optimization**: Use database-specific concatenation functions

### Additional Features (Roadmap)
1. **Custom Naming Patterns**: More flexible dimension table naming
2. **Selective Processing**: Process only specific table relationships
3. **Performance Metrics**: Track dimension table creation performance
4. **Validation**: Verify dimension table correctness and completeness

---

*This documentation covers the complete star schema migration paths as of the current implementation. For merged tables approach, see `merged_tables_migration_paths.md`.*
