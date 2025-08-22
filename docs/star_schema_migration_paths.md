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
└── staging_tables.model_handling = "star_schema" → **STAR SCHEMA PROCESSING**
    ├── data_load_mode = "import" → **IMPORT MODE PATH**
    ├── data_load_mode = "direct_query" → **DIRECTQUERY MODE PATH**
    └── data_load_mode = other → **FALLBACK TO IMPORT** (with warning)
```

## Execution Paths

### Path 1: Star Schema + Import Mode

**Configuration:**
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

**Execution Flow:**
1. **Entry Point**: `StagingTableHandler.process_data_model()`
2. **Handler Selection**: `_process_star_schema()` → `StarSchemaHandler.process_import_mode()`
3. **Relationship Loading**:
   - **Primary**: Load SQL relationships from `sql_filtered_relationships.json` (accurate join keys)
   - **Fallback**: Use basic relationships from `relationships.json` (generic "STOP" keys)
4. **Complex Relationship Identification**: Find relationships that need dimension tables
5. **Relationship Grouping**: Group relationships by connected table pairs
6. **Dimension Table Creation**:
   - Create `Dim_` prefixed tables (e.g., `Dim_ITEM_SITE_EXTRACT_STORAGE_LOCATION`)
   - Combine columns from related tables using composite keys
   - Generate M-queries with `Table.Combine` and `Table.Distinct` operations
7. **Partition Mode**: `mode: import` (data loaded into Power BI model)
8. **M-Query Structure**:
   ```m
   partition Dim_TABLE1_TABLE2 = m
   mode: import
   source = 
       let
           Source1 = TABLE1,
           Source2 = TABLE2,
           Combined = Table.Combine({Source1, Source2}),
           Distinct = Table.Distinct(Combined, {"composite_key_columns"}),
           AddedCompositeKey = Table.AddColumn(Distinct, "TABLE1_TABLE2_Key", 
               each [COLUMN1] & "_" & [COLUMN2])
       in
           AddedCompositeKey
   ```

### Path 2: Star Schema + DirectQuery Mode

**Configuration:**
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

**Execution Flow:**
1. **Entry Point**: `StagingTableHandler.process_data_model()`
2. **Handler Selection**: `_process_star_schema()` → `StarSchemaHandler.process_direct_query_mode()`
3. **Processing Strategy**: 
   - **Current Implementation**: Calls `process_import_mode()` then updates partition mode
   - **Future Enhancement**: Will use native SQL optimizations (see TODO comments)
4. **Dimension Table Creation**: Same as import mode (steps 3-6 above)
5. **Partition Mode Override**: All `Dim_` tables get `partition_mode = "directQuery"`
6. **M-Query Structure**: Same M-query as import mode, but with different partition mode:
   ```m
   partition Dim_TABLE1_TABLE2 = m
   mode: directQuery  // ← Key difference
   source = 
       let
           // Same Power Query operations as import mode
           // Future: Will be replaced with native SQL for better performance
       in
           AddedCompositeKey
   ```

**Future DirectQuery Optimizations (Planned):**
- Native SQL JOINs instead of `Table.Combine`
- SQL-based composite key creation (`CONCAT` or `||`)
- `UNION ALL` SQL instead of `Table.Combine`
- SQL CTEs for complex dimension logic
- Minimized Power Query transformations for query folding

## Code Flow Analysis

### Main Orchestration
```
StagingTableHandler.process_data_model()
├── Check: staging_tables.enabled && model_handling != "none"
├── Route to: _process_star_schema()
└── Delegate to: StarSchemaHandler.process_import_mode() OR process_direct_query_mode()
```

### Star Schema Handler Methods
```
StarSchemaHandler
├── process_import_mode()
│   ├── Load relationships (SQL preferred, basic fallback)
│   ├── Identify complex relationships
│   ├── Group relationships by table pairs
│   ├── Create dimension tables with composite keys
│   └── Generate M-queries with Power Query operations
│
└── process_direct_query_mode()
    ├── Call process_import_mode() (reuse logic)
    ├── Override partition_mode = "directQuery" for all Dim_ tables
    └── Log mode changes
```

### Relationship Processing Priority
1. **SQL Relationships** (`sql_filtered_relationships.json`):
   - Accurate join keys and types
   - Explicit JOIN types (INNER, LEFT OUTER, RIGHT OUTER)
   - Composite key information
   
2. **Basic Relationships** (`relationships.json`):
   - Generic "STOP" join keys
   - Default to INNER JOIN
   - Limited metadata

## Generated Artifacts

### Dimension Tables
- **Naming**: `{naming_prefix}{TABLE1}_{TABLE2}` (e.g., `Dim_ITEM_SITE_EXTRACT_STORAGE_LOCATION`)
- **Columns**: Combined columns from both source tables + composite key column
- **Composite Key**: `{TABLE1}_{TABLE2}_Key` with format `"value1_value2_value3"`

### M-Query Patterns

**Import Mode M-Query:**
```m
let
    Source1 = ITEM_SITE_EXTRACT,
    Source2 = STORAGE_LOCATION,
    Combined = Table.Combine({Source1, Source2}),
    Distinct = Table.Distinct(Combined, {"SITE_NUMBER", "ITEM_NUMBER"}),
    AddedCompositeKey = Table.AddColumn(Distinct, "ITEM_SITE_EXTRACT_STORAGE_LOCATION_Key", 
        each [SITE_NUMBER] & "_" & [ITEM_NUMBER])
in
    AddedCompositeKey
```

**DirectQuery Mode M-Query:**
```m
// Same Power Query operations as import mode
// Partition mode set to directQuery for query folding
// Future: Will use native SQL for better performance
```

## Configuration Examples

### Example 1: Basic Star Schema with Import
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
**Result**: Creates dimension tables with `mode: import`, data loaded into model

### Example 2: Star Schema with DirectQuery
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
**Result**: Creates dimension tables with `mode: directQuery`, queries pushed to source

### Example 3: Custom Prefix
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "Staging_",
    "data_load_mode": "import",
    "model_handling": "star_schema"
  }
}
```
**Result**: Creates `Staging_TABLE1_TABLE2` dimension tables

### Example 4: Disabled Processing
```json
{
  "staging_tables": {
    "enabled": false,
    "model_handling": "star_schema"
  }
}
```
**Result**: No processing, returns original data model

## Troubleshooting Guide

### Common Issues

1. **No Dimension Tables Created**
   - **Cause**: No complex relationships found
   - **Check**: Verify relationships exist in source data
   - **Log**: Look for "No complex relationships found" message

2. **Generic "STOP" Join Keys**
   - **Cause**: Using basic relationships instead of SQL relationships
   - **Fix**: Ensure `sql_filtered_relationships.json` exists and is valid
   - **Check**: Look for "Using SQL relationships" vs "Using basic relationships" logs

3. **Mode Still Shows Import in DirectQuery**
   - **Cause**: Template caching or partition mode not properly set
   - **Check**: Verify `partition_mode` is set to "directQuery" in table objects
   - **Log**: Look for "Set dimension table X to directQuery mode" messages

4. **Processing Errors**
   - **Cause**: Invalid relationships or missing source tables
   - **Result**: Falls back to original data model
   - **Check**: Review error logs for specific failure reasons

### Debug Logging
Enable detailed logging to trace execution:
```python
logging.getLogger('StarSchemaHandler').setLevel(logging.DEBUG)
```

Key log messages to watch for:
- `"Processing data model with 'star_schema' + 'import/direct_query' approach"`
- `"Using SQL relationships"` vs `"Using basic relationships"`
- `"Identified X complex relationships that need staging tables"`
- `"Created dimension table: Dim_TABLE1_TABLE2"`
- `"Set dimension table X to directQuery mode"`

## Performance Considerations

### Import Mode
- **Pros**: Full Power Query transformation capabilities
- **Cons**: Data loaded into model, increases model size
- **Best For**: Small to medium datasets, complex transformations

### DirectQuery Mode  
- **Pros**: Queries pushed to source, smaller model size
- **Cons**: Limited transformation capabilities, network latency
- **Best For**: Large datasets, real-time data requirements

### Future DirectQuery Optimizations
The current DirectQuery implementation reuses import mode logic. Planned optimizations include:
- Native SQL generation for better query folding
- Reduced Power Query transformations
- SQL-based composite key creation
- Optimized relationship handling

## Related Documentation
- [Merged Tables Migration Paths](merged_tables_migration_paths.md) - Alternative to star schema
- [Base Handler Documentation](base_handler.md) - Common functionality
- [M-Query Generation Guide](mquery_generation.md) - M-query patterns and best practices