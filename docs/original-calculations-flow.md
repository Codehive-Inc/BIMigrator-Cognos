# Calculations.json Flow Documentation

## Overview

The `calculations.json` file is a critical component in the BIMigrator-Cognos migration process that stores extracted calculations (measures) from Cognos reports and modules. These calculations are later converted to Power BI DAX measures during the PBIT file generation.

## File Structure

The `calculations.json` file contains an array of calculation objects with the following structure:

```json
[
  {
    "name": "Total Revenue",
    "expression": "[Sales Query].[Revenue]",
    "aggregate_function": "total",
    "solve_order": null,
    "type": "calculation"
  }
]
```

## Generation Flow

### 1. Individual Report Migration

When migrating a single Cognos report:

```
cognos_migrator/migrator.py (line ~1169)
├── Extracts calculations from report specification
├── Processes each calculation's expression and metadata
└── Writes to: output/<migration_id>/report_<report_id>/extracted/calculations.json
```

**Location**: `output/<migration_id>/report_<report_id>/extracted/calculations.json`
**Contains**: Calculations specific to that individual report

### 2. Module Migration with Associated Reports

When migrating a Cognos module that has associated reports:

```
cognos_migrator/module_migrator.py
├── Step 1: Migrate each associated report individually
│   └── Each creates: output/<migration_id>/report_<report_id>/extracted/calculations.json
│
└── Step 2: Collect and combine all report calculations
    └── module_expression_extractor.py::collect_report_calculations()
        ├── Reads each report's calculations.json
        ├── Combines them into a single collection
        └── Writes to: output/<migration_id>/extracted/calculations.json
```

**Locations**:
- Individual reports: `output/<migration_id>/report_<report_id>/extracted/calculations.json`
- Combined module level: `output/<migration_id>/extracted/calculations.json`

## Consumption in PBIT Generation

### Model File Generation

The calculations are consumed during Power BI model generation:

```
generators/model_file_generator.py (line 495)
├── Loads calculations.json from extracted_dir
├── For each calculation:
│   ├── Determines the target table
│   ├── Converts Cognos expression to DAX
│   └── Creates a measure in the Power BI model
└── Generates TMDL files with measure definitions
```

### Module Model File Generation

For module-based migrations:

```
generators/module_model_file_generator.py (line 104)
├── Loads the combined calculations.json
├── Maps calculations to appropriate tables
└── Generates measures in the Power BI data model
```

## Expression Conversion Process

1. **Extraction**: Cognos expressions are extracted as-is (e.g., `[Sales Query].[Revenue]`)
2. **Conversion**: During PBIT generation, expressions are converted to DAX:
   - Simple references: `[Sales Query].[Revenue]` → `SUM('Sales Query'[Revenue])`
   - Complex expressions: Processed by LLM service for accurate conversion
3. **Assignment**: Measures are assigned to appropriate tables based on query references

## Why Multiple Files?

This design supports two key scenarios:

1. **Modular Architecture**: Each report can be migrated independently without requiring the entire module context
2. **Aggregation Support**: Module migrations can aggregate calculations from multiple reports, providing a complete view of all measures

## File Locations Summary

| Migration Type | Calculations.json Location | Purpose |
|---------------|---------------------------|---------|
| Single Report | `output/<id>/report_<report_id>/extracted/calculations.json` | Report-specific calculations |
| Module Only | `output/<id>/extracted/calculations.json` | Module-level calculations |
| Module + Reports | `output/<id>/extracted/calculations.json` (combined) | Aggregated calculations from all reports |
| | `output/<id>/report_<report_id>/extracted/calculations.json` (individual) | Individual report calculations |

## Key Functions

- **Extraction**: `cognos_migrator.extractors.CalculationExtractor`
- **Collection**: `module_expression_extractor.collect_report_calculations()`
- **Consumption**: `model_file_generator._load_calculations()`
- **Conversion**: `model_file_generator._convert_expression_to_dax()`

## Notes

- The combined calculations.json file does not duplicate calculations; it merges unique calculations from all associated reports
- Each calculation retains its original context (query references) for proper table assignment
- The LLM service is used for complex expression conversions that cannot be handled by simple pattern matching