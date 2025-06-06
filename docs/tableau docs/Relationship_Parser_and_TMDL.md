# Relationship Parser and TMDL Generation

This document explains how the BIMigrator handles relationship extraction from Tableau workbooks and generates corresponding TMDL files for Power BI.

## Relationship Parser

The relationship parser (`RelationshipParser`) is responsible for extracting table relationships from Tableau workbooks and converting them to Power BI's relationship format.

### Key Components

1. **Configuration (twb-to-pbi.yaml)**
   ```yaml
   PowerBiRelationship:
     source_xpath: //datasources/datasource/_.fcp.ObjectModelEncapsulateLegacy.false...relation[@type='join'] | 
                  //datasources/datasource/_.fcp.ObjectModelEncapsulateLegacy.true...relation[@type='join'] | 
                  //datasources/datasource/relation[@type='join']
   ```
   - Handles both legacy and modern Tableau formats
   - Configurable properties for cardinality, cross-filtering, etc.
   - XPath-based extraction of relationship components

2. **Relationship Extraction Process**
   - Finds all join relations using configured XPath
   - Extracts relationship information:
     - From/To table names
     - From/To column names
     - Relationship properties (cardinality, cross-filtering, etc.)
   - Handles special cases like SQL query tables

3. **Special Handling**
   - SQL Query Tables: Extracts actual table names from query text
   - Legacy Format: Supports older Tableau workbook formats
   - Modern Format: Handles newer join clause expressions

### Example Output

A typical TMDL relationship output looks like:
```
relationship 
    fromTable: CustomTable1
    fromColumn: Column1
    toTable: CustomTable2
    toColumn: Column2
    cardinality: manyToOne
    crossFilteringBehavior: oneWay
    isActive: true
```

## TMDL File Generation

### Structure
1. **Model Directory**
   - `model.tmdl`: Main model file
   - `relationships.tmdl`: Contains all relationship definitions
   - `tables/`: Individual table TMDL files

2. **Relationship TMDL**
   - Generated from extracted relationships
   - Each relationship includes:
     - Table and column mappings
     - Cardinality settings
     - Cross-filtering behavior
     - Active state

### Generation Process

1. **Extraction**
   - Parser processes Tableau workbook XML
   - Identifies all join relationships
   - Validates required information

2. **Transformation**
   - Converts Tableau join types to Power BI cardinality
   - Maps cross-filtering behavior
   - Handles table name resolution

3. **TMDL Generation**
   - Creates relationships.tmdl file
   - Includes all valid relationships
   - Maintains proper TMDL formatting

### Best Practices

1. **Relationship Configuration**
   - Use clear, unique table names
   - Set appropriate cardinality
   - Configure cross-filtering based on requirements

2. **Error Handling**
   - Skip invalid relationships
   - Log missing information
   - Provide clear error messages

3. **Performance**
   - Efficient XPath queries
   - Proper caching of parsed data
   - Minimal file I/O operations

## Common Issues and Solutions

1. **Table Name Resolution**
   - Issue: SQL query tables have generic names
   - Solution: Extract actual table names from SQL queries

2. **Legacy Format Support**
   - Issue: Different XML structures in old workbooks
   - Solution: Multiple XPath patterns and format detection

3. **Missing Information**
   - Issue: Incomplete relationship definitions
   - Solution: Skip invalid relationships, log warnings

## Future Improvements

1. **Enhanced Validation**
   - Additional checks for relationship validity
   - Better error reporting

2. **Performance Optimization**
   - Cached table name resolution
   - Batch processing of relationships

3. **Additional Features**
   - Support for more relationship types
   - Advanced cardinality detection
   - Custom relationship properties
