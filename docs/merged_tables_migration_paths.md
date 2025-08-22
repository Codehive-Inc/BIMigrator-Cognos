# Merged Tables (C_Tables) Migration Paths Documentation

## Overview

This document provides a comprehensive guide to all migration paths available in the **Merged Tables** model handling approach. The merged tables approach creates combination tables (C_tables) that join multiple source tables together using nested joins, rather than creating separate dimension tables like the star schema approach.

## Key Concepts

### C_Tables (Combination Tables)
- **Purpose**: Combine columns from multiple related tables into single tables
- **Naming**: `C_{TABLE1}_{TABLE2}` (e.g., `C_ITEM_SITE_EXTRACT_MATERIAL_CHARGES`)
- **Logic**: Uses `Table.NestedJoin` operations to merge tables based on relationships
- **Deduplication**: Automatically removes duplicate columns when combining tables

### Differences from Star Schema
| Aspect | Star Schema | Merged Tables (C_Tables) |
|--------|-------------|--------------------------|
| **Approach** | Creates dimension tables with composite keys | Creates combination tables with nested joins |
| **Table Names** | `Dim_{TABLE1}_{TABLE2}` | `C_{TABLE1}_{TABLE2}` |
| **M-Query Logic** | `Table.Combine` + `Table.Distinct` | `Table.NestedJoin` + `Table.ExpandTableColumn` |
| **Data Structure** | Consolidated dimension data | Combined source table data |
| **Use Case** | Traditional star schema modeling | Direct table combination scenarios |

## Configuration Settings

The migration path is determined by two key settings in `settings.json`:

```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "C_",
    "data_load_mode": "import|direct_query", 
    "model_handling": "merged_tables"
  }
}
```

## Migration Path Decision Tree

```
settings.json
├── staging_tables.enabled = false → **NO PROCESSING** (return original model)
├── staging_tables.model_handling = "none" → **NO PROCESSING** (return original model)
└── staging_tables.model_handling = "merged_tables" → **MERGED TABLES PROCESSING**
    ├── data_load_mode = "import" → **IMPORT MODE PATH**
    ├── data_load_mode = "direct_query" → **DIRECTQUERY MODE PATH**
    └── data_load_mode = other → **FALLBACK TO IMPORT** (with warning)
```

## Execution Paths

### Path 1: Merged Tables + Import Mode

**Configuration:**
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "C_",
    "data_load_mode": "import",
    "model_handling": "merged_tables"
  }
}
```

**Execution Flow:**
1. **Entry Point**: `StagingTableHandler.process_data_model()`
2. **Handler Selection**: `_process_merged_tables()` → `MergedTablesHandler.process_import_mode()`
3. **Relationship Loading**:
   - **Primary**: Load SQL relationships from `sql_filtered_relationships.json` (accurate join keys)
   - **Fallback**: Use basic relationships from `relationships.json` (generic "STOP" keys)
4. **Complex Relationship Identification**: Find relationships that need combination tables
5. **Relationship Grouping**: Group relationships by connected table pairs
6. **C_Table Creation**:
   - Create `C_` prefixed tables (e.g., `C_ITEM_SITE_EXTRACT_MATERIAL_CHARGES`)
   - Combine columns from both source tables with automatic deduplication
   - Generate M-queries with `Table.NestedJoin` and `Table.ExpandTableColumn` operations
7. **Partition Mode**: `mode: import` (data loaded into Power BI model)
8. **M-Query Structure**:
   ```m
   partition C_TABLE1_TABLE2 = m
   mode: import
   source = 
       let
           Source = Table.NestedJoin(
               TABLE1, 
               {"KEY1", "KEY2"}, 
               TABLE2, 
               {"KEY1", "KEY2"}, 
               "TABLE2_Nested", 
               JoinKind.Inner
           ),
           #"Expanded TABLE2" = Table.ExpandTableColumn(
               Source, 
               "TABLE2_Nested", 
               {"UNIQUE_COL1", "UNIQUE_COL2", "UNIQUE_COL3"}
           )
       in
           #"Expanded TABLE2"
   ```

### Path 2: Merged Tables + DirectQuery Mode

**Configuration:**
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "C_",
    "data_load_mode": "direct_query",
    "model_handling": "merged_tables"
  }
}
```

**Execution Flow:**
1. **Entry Point**: `StagingTableHandler.process_data_model()`
2. **Handler Selection**: `_process_merged_tables()` → `MergedTablesHandler.process_direct_query_mode()`
3. **Processing Strategy**: 
   - **Current Implementation**: Calls `process_import_mode()` then updates partition mode
   - **Future Enhancement**: Will use native SQL JOINs (see TODO comments)
4. **C_Table Creation**: Same as import mode (steps 3-6 above)
5. **Partition Mode Override**: All `C_` tables get `partition_mode = "directQuery"`
6. **M-Query Structure**: Same M-query as import mode, but with different partition mode:
   ```m
   partition C_TABLE1_TABLE2 = m
   mode: directQuery  // ← Key difference
   source = 
       let
           // Same Power Query operations as import mode
           // Future: Will be replaced with native SQL JOINs for better performance
       in
           #"Expanded TABLE2"
   ```

**Future DirectQuery Optimizations (Planned):**
- Native SQL JOINs instead of `Table.NestedJoin`
- Direct SQL column selection instead of `Table.ExpandTableColumn`
- Optimized query folding for better performance
- Minimized Power Query transformations

## Code Flow Analysis

### Main Orchestration
```
StagingTableHandler.process_data_model()
├── Check: staging_tables.enabled && model_handling != "none"
├── Route to: _process_merged_tables()
└── Delegate to: MergedTablesHandler.process_import_mode() OR process_direct_query_mode()
```

### Merged Tables Handler Methods
```
MergedTablesHandler
├── process_import_mode()
│   ├── Load relationships (SQL preferred, basic fallback)
│   ├── Identify complex relationships
│   ├── Group relationships by table pairs
│   ├── Create combination tables (C_tables) with column deduplication
│   └── Generate M-queries with Table.NestedJoin operations
│
└── process_direct_query_mode()
    ├── Call process_import_mode() (reuse logic)
    ├── Override partition_mode = "directQuery" for all C_ tables
    └── Log mode changes
```

### C_Table Creation Process
```
_create_combination_table()
├── Generate table name: C_{TABLE1}_{TABLE2} (sorted alphabetically)
├── Combine columns from both tables:
│   ├── Add all columns from first table
│   └── Add only unique columns from second table (deduplication)
├── Set partition mode based on data_load_mode
└── Return Table object (M-query generated separately)
```

### M-Query Generation Process
```
_generate_nested_join_query()
├── Extract join columns from relationships
├── Build join key arrays for M-query
├── Identify unique columns from second table (with deduplication)
├── Generate Table.NestedJoin operation
└── Generate Table.ExpandTableColumn operation
```

## Column Deduplication Logic

### Problem Solved
The merged tables approach automatically handles column deduplication to prevent duplicate columns in the final C_tables.

### Deduplication Process
1. **Schema Level**: When creating the `Table` object, only unique columns are added
2. **M-Query Level**: The `Table.ExpandTableColumn` only expands unique columns from the nested table
3. **Implementation**:
   ```python
   # Get column names from first table
   from_table_column_names = {col.name for col in from_table.columns}
   
   # Add only unique columns from second table
   unique_to_table_columns = []
   for col in to_table.columns:
       if col.name not in from_table_column_names:
           unique_to_table_columns.append(col.name)
   
   # Remove duplicates from the list itself
   unique_to_table_columns = list(dict.fromkeys(unique_to_table_columns))
   ```

### Before vs After Fix
**Before (Duplicate Columns)**:
```m
Table.ExpandTableColumn(Source, "TABLE2_Nested", 
    {"COL1", "COL2", "COL3", "COL1", "COL2", "COL3"})  // Duplicates!
```

**After (Deduplicated)**:
```m
Table.ExpandTableColumn(Source, "TABLE2_Nested", 
    {"COL1", "COL2", "COL3"})  // Clean, no duplicates
```

## Relationship Processing Priority

### SQL Relationships (Preferred)
- **Source**: `sql_filtered_relationships.json`
- **Advantages**: Accurate join keys, explicit join types, composite key support
- **Join Types**: INNER JOIN, LEFT OUTER JOIN, RIGHT OUTER JOIN, etc.
- **Example**:
  ```json
  {
    "from_table": "ITEM_SITE_EXTRACT",
    "to_table": "MATERIAL_CHARGES", 
    "join_type": "INNER JOIN",
    "join_keys": [
      {"from_column": "SITE_NUMBER", "to_column": "SITE_NUMBER"},
      {"from_column": "ITEM_NUMBER", "to_column": "ITEM_NUMBER"}
    ]
  }
  ```

### Basic Relationships (Fallback)
- **Source**: `relationships.json`
- **Limitations**: Generic "STOP" join keys, default to INNER JOIN
- **Use Case**: When SQL relationships are not available
- **Example**:
  ```json
  {
    "from_table": "ITEM_SITE_EXTRACT",
    "to_table": "MATERIAL_CHARGES",
    "from_column": "STOP",
    "to_column": "STOP"
  }
  ```

## Generated Artifacts

### C_Tables (Combination Tables)
- **Naming**: `C_{TABLE1}_{TABLE2}` (alphabetically sorted, e.g., `C_ITEM_SITE_EXTRACT_MATERIAL_CHARGES`)
- **Columns**: All columns from first table + unique columns from second table
- **No Composite Keys**: Unlike star schema, C_tables don't add composite key columns
- **Relationships**: Maintain original relationships between source tables

### M-Query Patterns

**Import Mode M-Query:**
```m
let
    Source = Table.NestedJoin(
        ITEM_SITE_EXTRACT, 
        {"SITE_NUMBER", "ITEM_NUMBER"}, 
        MATERIAL_CHARGES, 
        {"SITE_NUMBER", "ITEM_NUMBER"}, 
        "MATERIAL_CHARGES_Nested", 
        JoinKind.Inner
    ),
    #"Expanded MATERIAL_CHARGES" = Table.ExpandTableColumn(
        Source, 
        "MATERIAL_CHARGES_Nested", 
        {"CHARGED_DATE", "TIME_ENTERED", "STOREKEEPER_ID", "EMPLOYEE_ID", 
         "ISSUE_TICKET_NUMBER", "TRANSACTION_TYPE", "ADJUSTMENT_TYPE", 
         "QUANTITY", "TRANSACTION_VALUE", "JOB_NUMBER", "PO_NUMBER"}
    )
in
    #"Expanded MATERIAL_CHARGES"
```

**DirectQuery Mode M-Query:**
```m
// Same Power Query operations as import mode
// Partition mode set to directQuery for query folding
// Future: Will use native SQL JOINs for better performance
```

## Configuration Examples

### Example 1: Basic Merged Tables with Import
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "C_",
    "data_load_mode": "import",
    "model_handling": "merged_tables"
  }
}
```
**Result**: Creates C_tables with `mode: import`, data loaded into model

### Example 2: Merged Tables with DirectQuery
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "C_", 
    "data_load_mode": "direct_query",
    "model_handling": "merged_tables"
  }
}
```
**Result**: Creates C_tables with `mode: directQuery`, queries pushed to source

### Example 3: Custom Prefix
```json
{
  "staging_tables": {
    "enabled": true,
    "naming_prefix": "Combined_",
    "data_load_mode": "import",
    "model_handling": "merged_tables"
  }
}
```
**Result**: Creates `Combined_TABLE1_TABLE2` combination tables

### Example 4: Disabled Processing
```json
{
  "staging_tables": {
    "enabled": false,
    "model_handling": "merged_tables"
  }
}
```
**Result**: No processing, returns original data model

## Comparison: Star Schema vs Merged Tables

### When to Use Star Schema
- **Traditional BI modeling** with fact and dimension tables
- **Data warehousing** scenarios with clear dimensional hierarchy
- **Composite key requirements** for dimension tables
- **OLAP cube-style** analysis needs

### When to Use Merged Tables (C_Tables)
- **Direct table combination** scenarios
- **Operational reporting** with joined source tables
- **Simplified data models** without dimensional hierarchy
- **Performance optimization** through pre-joined tables

### Technical Differences

| Feature | Star Schema | Merged Tables |
|---------|-------------|---------------|
| **Table Purpose** | Dimension tables for lookup | Combined operational tables |
| **M-Query Operations** | `Table.Combine` + `Table.Distinct` | `Table.NestedJoin` + `Table.ExpandTableColumn` |
| **Composite Keys** | Yes, added automatically | No, uses original keys |
| **Data Consolidation** | Consolidates related data | Joins related data |
| **Relationship Handling** | Creates new relationships to composite keys | Maintains original relationships |

## Troubleshooting Guide

### Common Issues

1. **No C_Tables Created**
   - **Cause**: No complex relationships found
   - **Check**: Verify relationships exist between source tables
   - **Log**: Look for "No complex relationships found" message

2. **Duplicate Columns in M-Query**
   - **Cause**: Column deduplication not working properly
   - **Fix**: Ensure latest deduplication logic is applied
   - **Check**: Look for duplicate column names in `Table.ExpandTableColumn`

3. **Generic "STOP" Join Keys**
   - **Cause**: Using basic relationships instead of SQL relationships
   - **Fix**: Ensure `sql_filtered_relationships.json` exists and is valid
   - **Check**: Look for "Using SQL relationships" vs "Using basic relationships" logs

4. **Mode Still Shows Import in DirectQuery**
   - **Cause**: Partition mode not properly set or template caching
   - **Check**: Verify `partition_mode` is set to "directQuery" in table objects
   - **Log**: Look for "Set table X to directQuery mode" messages

5. **Missing Columns in C_Tables**
   - **Cause**: Over-aggressive deduplication or relationship issues
   - **Check**: Verify source tables have expected columns
   - **Debug**: Enable debug logging to see column processing

### Debug Logging
Enable detailed logging to trace execution:
```python
logging.getLogger('MergedTablesHandler').setLevel(logging.DEBUG)
```

Key log messages to watch for:
- `"Processing data model with 'merged_tables' + 'import/direct_query' approach for C_tables"`
- `"Using SQL relationships"` vs `"Using basic relationships"`
- `"Identified X complex relationships"`
- `"Created combination table: C_TABLE1_TABLE2"`
- `"DEBUG: Unique columns for TABLE: [...]"`
- `"Set table X to directQuery mode"`

## Performance Considerations

### Import Mode
- **Pros**: Full Power Query transformation capabilities, complex nested joins
- **Cons**: Data loaded into model, increases model size
- **Best For**: Medium datasets, complex table combinations

### DirectQuery Mode  
- **Pros**: Queries pushed to source, smaller model size
- **Cons**: Limited transformation capabilities, nested join complexity
- **Best For**: Large datasets, real-time data requirements

### Future DirectQuery Optimizations
The current DirectQuery implementation reuses import mode logic. Planned optimizations include:
- Native SQL JOINs instead of `Table.NestedJoin`
- Direct SQL column selection instead of `Table.ExpandTableColumn`
- Optimized query folding for better performance
- Reduced Power Query transformation overhead

## Best Practices

### Table Design
1. **Use meaningful prefixes**: Default `C_` clearly identifies combination tables
2. **Monitor column counts**: Large C_tables may impact performance
3. **Consider relationship complexity**: Simple 1:1 or 1:many relationships work best

### Performance Optimization
1. **Prefer SQL relationships**: More accurate and performant than basic relationships
2. **Monitor query folding**: Ensure DirectQuery operations fold properly
3. **Limit nested operations**: Complex nested joins may not fold well

### Maintenance
1. **Regular relationship audits**: Ensure relationships remain valid
2. **Monitor duplicate columns**: Watch for deduplication issues
3. **Test both modes**: Validate import and DirectQuery performance

## Related Documentation
- [Star Schema Migration Paths](star_schema_migration_paths.md) - Alternative dimensional modeling approach
- [Base Handler Documentation](base_handler.md) - Common functionality shared by all handlers
- [Migration Summary](migration_summary.md) - Overall implementation status and future enhancements
