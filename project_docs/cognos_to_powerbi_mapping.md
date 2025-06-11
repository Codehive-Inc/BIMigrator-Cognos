# Cognos Analytics to Power BI Data Mapping

## Executive Summary
This document provides a comprehensive mapping between Cognos Analytics API data points and Power BI project structure requirements. Based on analysis of the PUAT DataLoad Analysis PowerBI project, bimigrator templates, and Cognos Analytics REST API capabilities.

## 1. High-Level Component Mapping

| Cognos Component | Cognos API Endpoint | Power BI Component | Power BI File |
|-----------------|-------------------|------------------|--------------|
| Data Module | `/modules/{id}` | Data Model | `Model/database.tmdl`, `Model/model.tmdl` |
| Module Tables | `/modules/{id}/metadata` | Tables | `Model/tables/*.tmdl` |
| Module Relationships | `/modules/{id}/metadata` | Relationships | `Model/relationships.tmdl` |
| Data Sources | `/datasources/{id}` | Data Sources/Partitions | Within table `.tmdl` files |
| Reports | `/content/{id}` | Reports | `Report/report.json` |
| Report Pages | Within report spec | Report Sections | `Report/sections/*/section.json` |
| Calculations | Module metadata | Measures/Calculated Columns | Within table `.tmdl` files |
| Filters | Report specification | Report/Visual Filters | `filters.json` files |
| Visualizations | Report specification | Visual Containers | `visualContainers/*/visualContainer.json` |

## 2. Data Model Mapping

### 2.1 Database and Model Configuration

| Cognos Data | Cognos API Field | Power BI Field | Power BI Location |
|------------|-----------------|----------------|------------------|
| Module Name | `module.name` | `name` | `database.tmdl` |
| Module ID | `module.id` | Internal reference | Model metadata |
| Module Version | `module.version` | `compatibility_level` | `database.tmdl` |
| Default Locale | `module.defaultLocale` | `culture` | `model.tmdl`, `cultures/*.tmdl` |
| Creation Date | `module.createdDate` | Annotations | `model.tmdl` |

### 2.2 Table Structure Mapping

| Cognos Data | Cognos API Field | Power BI Field | Power BI Template Variable |
|------------|-----------------|----------------|-------------------------|
| Query Subject | `table.name` | Table name | `source_name` |
| Table Label | `table.label` | Display name | `source_name` |
| Table Type | `table.type` | Table mode | `mode` |
| Hidden Flag | `table.isHidden` | Is Hidden | `is_hidden` |
| SQL Query | `table.expression` | M Query | `partitions[].expression` |

### 2.3 Column Mapping

| Cognos Data | Cognos API Field | Power BI Field | Power BI Template Variable |
|------------|-----------------|----------------|-------------------------|
| Query Item | `column.name` | Column name | `columns[].source_name` |
| Data Type | `column.dataType` | Data type | `columns[].datatype` |
| Format | `column.format` | Format string | `columns[].format_string` |
| Aggregation | `column.aggregate` | Summarize by | `columns[].summarize_by` |
| Usage | `column.usage` | Data category | `columns[].data_category` |
| Expression | `column.expression` | DAX expression | `columns[].expression` |
| Hidden | `column.isHidden` | Is Hidden | `columns[].is_hidden` |

### 2.4 Data Type Conversion

| Cognos Data Type | Power BI Data Type |
|-----------------|-------------------|
| `varchar`/`char` | `string` |
| `integer`/`smallint` | `int64` |
| `decimal`/`numeric` | `double` |
| `date` | `dateTime` |
| `timestamp` | `dateTime` |
| `boolean` | `boolean` |
| `blob`/`clob` | `string` |

## 3. Relationship Mapping

| Cognos Data | Cognos API Field | Power BI Field | Power BI Location |
|------------|-----------------|----------------|------------------|
| Relationship ID | `relationship.id` | `id` | `relationships.tmdl` |
| From Table | `relationship.fromEnd.table` | `from_table` | `relationships.tmdl` |
| From Column | `relationship.fromEnd.column` | `from_column` | `relationships.tmdl` |
| To Table | `relationship.toEnd.table` | `to_table` | `relationships.tmdl` |
| To Column | `relationship.toEnd.column` | `to_column` | `relationships.tmdl` |
| Cardinality | `relationship.cardinality` | `cardinality` | `relationships.tmdl` |
| Cross Filter | `relationship.crossFilter` | `cross_filter_behavior` | `relationships.tmdl` |

## 4. Calculation and Measure Mapping

| Cognos Type | Cognos Location | Power BI Type | Power BI Location |
|------------|----------------|--------------|------------------|
| Calculated Column | Module metadata | Calculated Column | Table `.tmdl` - `columns[]` |
| Stand-alone Calculation | Module metadata | Measure | Table `.tmdl` - `measures[]` |
| Aggregation Rule | Column metadata | Summarization | Column `summarize_by` |
| Filter Expression | Report spec | DAX Filter | Measure expression |

### 4.1 Expression Conversion Examples

| Cognos Expression Type | Example | Power BI DAX Equivalent |
|----------------------|---------|------------------------|
| Simple Sum | `total([Sales])` | `SUM([Sales])` |
| Conditional | `if ([Status] = 'Active') then ([Amount]) else (0)` | `IF([Status] = "Active", [Amount], 0)` |
| Date Calculation | `_year([Date])` | `YEAR([Date])` |
| Running Total | `running-total([Sales])` | `CALCULATE(SUM([Sales]), FILTER(ALL(Table), Table[Date] <= MAX(Table[Date])))` |

## 5. Report Structure Mapping

### 5.1 Report Configuration

| Cognos Data | Cognos Location | Power BI Field | Power BI Location |
|------------|----------------|----------------|------------------|
| Report Name | `content.name` | Report name | `report.json` |
| Report ID | `content.id` | Report ID | `report.json` |
| Theme | Report metadata | Theme | `config.json` |
| Page Size | Page properties | Canvas settings | `section.json` |

### 5.2 Visualization Mapping

| Cognos Visual | Power BI Visual | Key Properties to Map |
|--------------|-----------------|---------------------|
| List | Table | Columns, sorting, formatting |
| Crosstab | Matrix | Rows, columns, values, subtotals |
| Chart (Column) | Clustered Column Chart | Axis, values, legend, data labels |
| Chart (Line) | Line Chart | Axis, values, legend, markers |
| Chart (Pie) | Pie Chart | Values, details, labels |
| Chart (Combination) | Line and Clustered Column | Multiple y-axes, series types |
| Map | Map Visual | Location, size, color saturation |

## 6. Data Source and Connection Mapping

| Cognos Data | Cognos API Field | Power BI Field | Power BI Location |
|------------|-----------------|----------------|------------------|
| Connection Name | `datasource.name` | Source name | Partition expression |
| Connection Type | `datasource.type` | Provider type | Partition source type |
| Connection String | `datasource.connectionString` | Connection details | Partition expression |
| Schema | `datasource.schema` | Database/Schema | Within M query |
| Credentials | Stored separately | Not migrated | Manual setup required |

## 7. Query and Data Access Mapping

### 7.1 Query Types

| Cognos Query Type | Power BI Equivalent | Implementation |
|------------------|-------------------|----------------|
| SQL Query | Native Query | M query with `Value.NativeQuery()` |
| MDX Query | DAX Query | Convert to DAX table expressions |
| Module Query | Direct Query | Reference table from model |

### 7.2 M Query Generation Template

```powerquery
let
    Source = Sql.Database("server", "database"),
    Query = Value.NativeQuery(Source, "SELECT * FROM table WHERE condition")
in
    Query
```

## 8. Metadata and Annotations

| Cognos Metadata | Power BI Location | Purpose |
|----------------|------------------|---------|
| Object Description | Annotations | Documentation |
| Business Terms | Display names | User-friendly names |
| Security Rules | Row-level security | Access control |
| Lineage Info | Extended properties | Audit trail |

## 9. Migration Considerations

### 9.1 Features Requiring Manual Intervention

| Cognos Feature | Reason | Recommended Action |
|---------------|--------|-------------------|
| Prompts/Parameters | Different implementation | Convert to Power BI parameters |
| Conditional Formatting | Different syntax | Recreate using Power BI rules |
| Complex Security | Platform-specific | Rebuild RLS in Power BI |
| Stored Procedures | May not be supported | Convert to views or M queries |

### 9.2 Data Not Available via API

| Required Data | Current Limitation | Workaround |
|--------------|-------------------|------------|
| Detailed visual properties | Not in API response | Use default templates |
| Custom SQL functions | Embedded in reports | Parse from report spec |
| Conditional styles | Report-specific | Apply standard formatting |
| Drill-through paths | Complex navigation | Simplified implementation |

## 10. Implementation Priority

### Phase 1: Core Data Model (Currently Implemented)
- ✅ Module to Table mapping
- ✅ Basic column properties
- ✅ Simple relationships
- ✅ Basic measures

### Phase 2: Advanced Features (To Be Implemented)
- ⏳ Complex calculations and DAX conversion
- ⏳ Hierarchies and drill-downs
- ⏳ Advanced relationship properties
- ⏳ Time intelligence

### Phase 3: Report Migration (Future)
- ⏳ Page layout reconstruction
- ⏳ Visual type mapping
- ⏳ Filter and slicer conversion
- ⏳ Interaction behaviors

## 11. API Endpoint Usage Guide

### Essential API Calls for Migration

1. **Get Module Structure**
   ```
   GET /api/v1/modules/{moduleId}
   GET /api/v1/modules/{moduleId}/metadata
   ```

2. **Get Data Sources**
   ```
   GET /api/v1/datasources
   GET /api/v1/datasources/{id}
   ```

3. **Get Report Content**
   ```
   GET /api/v1/content/{reportId}
   GET /api/v1/content/{reportId}/specifications
   ```

4. **Navigate Folders**
   ```
   GET /api/v1/content?type=folder
   GET /api/v1/content/{folderId}/children
   ```

## 12. Template Variable Reference

### Core Variables for Power BI Generation

```python
{
    # Database/Model
    "name": "Database Name",
    "model_name": "Model", 
    "compatibility_level": 1567,
    "default_culture": "en-US",
    
    # Table
    "source_name": "TableName",
    "columns": [...],
    "measures": [...],
    "partitions": [...],
    
    # Relationships
    "relationships": [...],
    
    # Report
    "report_id": "unique_id",
    "sections": [...]
}
```

This mapping provides the foundation for converting Cognos Analytics content to Power BI format, identifying what can be automated and what requires manual intervention or default values.