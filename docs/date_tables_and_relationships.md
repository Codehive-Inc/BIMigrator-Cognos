# Date Tables and Relationships in BIMigrator-Cognos

This document provides guidance on adding local date time tables and creating relationships with date columns in the BIMigrator-Cognos system.

## Table of Contents
- [Introduction](#introduction)
- [Adding a Local Date Time Table](#adding-a-local-date-time-table)
  - [Date Table Structure](#date-table-structure)
  - [Date Table Template](#date-table-template)
  - [Adding a Date Table Programmatically](#adding-a-date-table-programmatically)
- [Creating Date Relationships](#creating-date-relationships)
  - [Date Relationship Structure](#date-relationship-structure)
  - [Adding Date Relationships Programmatically](#adding-date-relationships-programmatically)
- [Best Practices](#best-practices)

## Introduction

Date tables are essential components in Power BI models that enable time intelligence functions and date-based filtering. The BIMigrator-Cognos system supports automatic generation of date tables and relationships between date columns and these date tables.

> **Note:** The recommended approach is to use a central date table for the entire model rather than local date tables for each source table. For details on the central date table implementation, see [Central Date Table Implementation](central_date_table_implementation.md).

## Adding a Local Date Time Table

### Date Table Structure

A date table in Power BI typically includes:
- A primary date column
- Year, quarter, month, and day columns
- A date hierarchy
- Appropriate data categories for each column

### Date Table Template

The BIMigrator-Cognos system uses a template-based approach for generating date tables. The template is located at:

```
cognos_migrator/templates/DateTableTemplate.tmdl
```

This template defines a standard date table with the following components:
- Date column (primary date column)
- Year, Month, Quarter, and Day columns with appropriate data categories
- A date hierarchy with Year, Quarter, Month, and Day levels
- A calculated partition that generates date values

### Adding a Date Table Programmatically

To add a date table to your data model, follow these steps:

1. Create a date table definition dictionary:

```python
date_table = {
    'name': 'DateTableName',
    'template_content': date_table_content  # Content from DateTableTemplate.tmdl
}
```

2. Add the date table to your data model:

```python
if not hasattr(data_model, 'date_tables'):
    data_model.date_tables = []
data_model.date_tables.append(date_table)
```

3. The `ModelFileGenerator` will automatically generate the date table files when you call:

```python
model_file_generator.generate_model_files(data_model, output_dir)
```

### Example: Adding a Custom Date Range

To customize the date range for your date table, modify the partition source in the template:

```
partition DateTableName = calculated
    mode: import
    source = Calendar(Date(2015,1,1), Date(2025,12,31))
```

## Creating Date Relationships

### Date Relationship Structure

A date relationship connects a date column in a fact table to the primary date column in a date table. This enables time intelligence functions and date-based filtering.

### Adding Date Relationships Programmatically

To create a relationship between a date column and a date table:

1. Create a relationship object:

```python
from cognos_migrator.models import Relationship

relationship = Relationship(
    id='RelationshipID',
    from_table='FactTableName',
    from_column='DateColumnName',
    to_table='DateTableName',
    to_column='Date',
    from_cardinality='many',
    to_cardinality='one',
    cross_filtering_behavior='bothDirections',
    is_active=True,
    join_on_date_behavior='datePartOnly'  # Important for date relationships
)
```

2. Add the relationship to your data model:

```python
data_model.relationships.append(relationship)
```

3. The `ModelFileGenerator` will automatically generate the relationships file when you call:

```python
model_file_generator.generate_model_files(data_model, output_dir)
```

### Important Parameters for Date Relationships

- `join_on_date_behavior`: Set to `'datePartOnly'` for date relationships to ignore time components
- `cross_filtering_behavior`: Usually set to `'bothDirections'` for date relationships
- `from_cardinality`: Usually set to `'many'` (fact table side)
- `to_cardinality`: Usually set to `'one'` (date table side)

## Best Practices

1. **Use a Single Date Table**: When possible, use a single date table for all date relationships to ensure consistent date filtering.

2. **Set Appropriate Date Ranges**: Configure your date table to cover all dates in your data, plus some buffer for future dates.

3. **Mark as Date Table**: Ensure your date table has the `__PBI_TemplateDateTable = true` annotation.

4. **Use Date Part Only Joining**: For date columns that include time components, use `join_on_date_behavior='datePartOnly'` to ensure proper joining.

5. **Create Active Relationships**: Set `is_active=True` for date relationships that should be used by default in visuals.

6. **Set Proper Cardinality**: Date relationships are typically many-to-one (many fact records to one date).

7. **Enable Both Directions Filtering**: Set `cross_filtering_behavior='bothDirections'` to allow filtering in both directions.
