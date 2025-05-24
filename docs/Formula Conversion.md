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

1. **Dependency Resolution**
   ```python
   # Find dependencies in the formula
   deps = re.findall(r'\[Calculation_\d+\]', calc_info.formula)
   
   # Build dependency information
   dependencies = []
   for dep in deps:
       if dep in calculations:
           dep_info = calculations[dep]
           dependencies.append({
               "caption": dep_info["FormulaCaptionTableau"],
               "formula": dep_info["FormulaTableau"],
               "dax": dep_info["FormulaDax"],
               "tableau_name": dep_info["TableauName"]
           })
   ```
   - Dependencies are extracted from the formula using regex
   - Each dependency's information is collected for conversion
   - Dependencies are ordered to ensure proper resolution

2. **Pre-processing**
   ```python
   payload = {
       "tableau_formula": formula,
       "table_name": table_name,
       "column_mappings": {},
       "dependencies": dependencies
   }
   ```
   - The formula is extracted from the Tableau workbook
   - Table context is provided for proper column references
   - Dependencies are included for proper resolution
   - Column mappings can be provided for custom name translations

3. **API Request**
   - The formula and its dependencies are sent to the FastAPI service
   - The service uses the FormulaResolver to handle dependencies
   - The LLM converts the formula considering the dependency context
   - The response includes the DAX expression and any warnings/errors

4. **Post-processing**
   - Dependencies are replaced with their DAX expressions or PowerBI names
   - HTML entities in the response are decoded
   - Error handling is added for failed conversions
   - The result is formatted for TMDL output

### 4. Formula Resolution

The FastAPI service uses an agentic formula resolver to handle complex dependencies:

1. **FormulaResolver Class**
   - Manages a graph of calculation dependencies
   - Tracks converted formulas and their relationships
   - Ensures proper ordering of formula conversions

2. **Dependency Resolution**
   ```python
   def resolve_calculation_chain(self, calc_name: str):
       chain = []
       visited = set()
       
       def resolve_deps(name):
           if name in visited:
               return
           visited.add(name)
           node = self.calculations[name]
           deps = self.extract_dependencies(node.formula)
           node.dependencies = deps
           for dep in deps:
               if dep in self.calculations:
                   resolve_deps(dep)
           chain.append(node)
   ```
   - Recursively resolves dependencies
   - Handles circular dependencies
   - Builds a conversion chain

3. **LLM Integration**
   - The resolver works with an LLM to convert formulas
   - Dependencies are provided as context
   - The LLM understands the relationship between calculations

### 5. Calculation Tracking

The migration tool tracks all calculations and their conversions in a JSON file for monitoring and debugging purposes.

1. **Storage Format**
   ```json
   {
     "calculations": [
       {
         "TableName": "Sales",
         "FormulaCaptionTableau": "Total Sales",
         "CalculationName": "Calculation_123",
         "TableauCalculationName": "Calculation_123",
         "FormulaExpressionTableau": "SUM([Sales])",
         "FormulaTypeTableau": "measure",
         "PowerBIName": "Total Sales",
         "DAXExpression": "SUM('Sales'[Sales])",
         "ConversionStatus": "Converted"
       }
     ]
   }
   ```

2. **Tracked Information**
   - `TableName`: Source table containing the calculation
   - `FormulaCaptionTableau`: Display name in Tableau
   - `CalculationName`: Original calculation name from Tableau XML
   - `TableauCalculationName`: Calculation name (for backward compatibility)
   - `FormulaExpressionTableau`: Original Tableau formula
   - `FormulaTypeTableau`: Type (measure/calculated_column)
   - `PowerBIName`: Name in Power BI
   - `DAXExpression`: Converted DAX expression
   - `ConversionStatus`: Current status (Pending/Converted)

3. **Location**
   The calculations are stored in `extracted/calculations.json` under the output directory.

### 5. Special Cases

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
