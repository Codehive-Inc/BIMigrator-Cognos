# Tableau to DAX Formula Conversion

This document explains how the BIMigrator converts Tableau formulas to DAX expressions during the migration process.

## Overview

The formula conversion process is handled by two main components:
1. The `CalculationConverter` class in the BIMigrator
2. The FastAPI service that performs the actual conversion

## Conversion Process

### 1. Formula Extraction
- Formulas are extracted from Tableau workbooks in the following locations:
  - Calculated fields in datasources
  - Calculated columns in tables
  - Measures with aggregations
  - Custom SQL expressions

### 2. Formula Classification
The system classifies formulas into different types:

1. **Calculated Columns**
   - Regular calculated fields marked as dimensions
   - Stored with the table and computed for each row
   - Example: `[Sales Amount] * [Tax Rate]`

2. **Measures**
   - Calculated fields marked as measures
   - Aggregations over the entire table
   - Examples:
     - `SUM([Sales Amount])`
     - `AVG([Price])`

3. **Simple Aggregations**
   - Basic aggregations of columns
   - Automatically converted to DAX aggregation functions
   - Examples:
     - `SUM` → `SUM()`
     - `AVG` → `AVERAGE()`
     - `COUNT` → `COUNT()`

### 3. Conversion Flow

1. **Pre-processing**
   ```python
   payload = {
       "tableau_formula": calc_info.formula,
       "table_name": table_name,
       "column_mappings": {}
   }
   ```
   - The formula is extracted from the Tableau workbook
   - Table context is provided for proper column references
   - Column mappings can be provided for custom name translations

2. **API Request**
   - The formula is sent to the FastAPI service
   - The service uses advanced NLP to convert the formula
   - The response includes the DAX expression and any warnings/errors

3. **Post-processing**
   - HTML entities in the response are decoded
   - Error handling is added for failed conversions
   - The result is formatted for TMDL output

### 4. Special Cases

1. **Automatic Measure Detection**
   - If a formula starts with common aggregation functions (SUM, AVERAGE, COUNT, MIN, MAX), it's treated as a measure
   - Example: `SUM([Sales])` → `SUM('Sales Table'[Sales])`

2. **Implicit Aggregations**
   - For numeric columns without explicit aggregation, SUM is added by default
   - Example: `[Sales]` in a measure context → `SUM('Sales Table'[Sales])`

3. **Calculated Columns**
   - Formulas without aggregation are treated as calculated columns
   - They're stored in the table's column definitions
   - Example: `[Price] * [Quantity]` → Same expression but with proper table references

### 5. Error Handling

When conversion fails:
```dax
/* ERROR: Could not convert Tableau formula: <original_formula> */
/* Error details: <error_message> */
ERROR("Conversion failed")
```

## Common Conversions

| Tableau Formula | DAX Expression |
|----------------|----------------|
| `SUM([Sales])` | `SUM('Sales'[Sales])` |
| `[Price] * [Quantity]` | `'Sales'[Price] * 'Sales'[Quantity]` |
| `IF [Sales] > 1000 THEN "High" ELSE "Low" END` | `IF('Sales'[Sales] > 1000, "High", "Low")` |
| `RUNNING_SUM([Sales])` | `SUMX(FILTER(ALL('Sales'), 'Sales'[Date] <= MAX('Sales'[Date])), 'Sales'[Sales])` |

## Configuration

The conversion service can be configured in the config file:
```yaml
api_settings:
  base_url: http://localhost:8000
  timeout_seconds: 30
```

## Limitations

1. Some complex Tableau functions may not have direct DAX equivalents
2. Custom functions need special handling
3. Table calculations require careful mapping to DAX window functions
4. Level of Detail (LOD) expressions need special attention

## Best Practices

1. Always provide proper table context for formulas
2. Use column mappings for renamed fields
3. Test conversions with sample data
4. Review generated DAX for performance optimization
5. Keep track of failed conversions for manual review
