# SQL Extraction and Join Derivation Guide

## Overview

This document provides a comprehensive guide for extracting SQL queries from Cognos Framework Manager packages and reports, understanding their relationships, and deriving join logic for Power BI migration. The SQL extraction process is fundamental to understanding the data model structure and business logic embedded in Cognos artifacts.

## Table of Contents

1. [Package-Based SQL Extraction](#package-based-sql-extraction)
2. [Report-Based SQL Extraction](#report-based-sql-extraction)
3. [Join Derivation Logic](#join-derivation-logic)
4. [Relationship Analysis](#relationship-analysis)
5. [Integration Between Package and Report Extraction](#integration-between-package-and-report-extraction)
6. [Best Practices and Migration Patterns](#best-practices-and-migration-patterns)

---

## Package-Based SQL Extraction

### What is Package-Based Extraction?

Package-based SQL extraction analyzes Cognos Framework Manager (FM) packages to identify:
- Base table definitions (Query Subjects)
- Relationship definitions between tables
- Calculation definitions
- Filter definitions
- Data source connections

### Key Components Extracted

#### 1. Query Subject Definitions

From the package XML, we extract `<querySubject>` elements that contain SQL definitions:

```xml
<querySubject status="needsReevaluation">
    <name locale="en">ITEM_SITE_EXTRACT</name>
    <definition>
        <dbQuery>
            <sources>
                <dataSourceRef>[].[dataSources].[ELECTRIC_GENERATION_WPTMATT]</dataSourceRef>
            </sources>
            <sql type="cognos">
                Select <column>*</column>
                from<table>[ELECTRIC_GENERATION_WPTMATT].ITEM_SITE_EXTRACT</table>
            </sql>
        </dbQuery>
    </definition>
</querySubject>
```

**Extracted SQL:**
```sql
SELECT * 
FROM [ELECTRIC_GENERATION_WPTMATT].ITEM_SITE_EXTRACT
```

#### 2. Relationship Definitions

Relationships are defined as `<relationship>` elements with join expressions:

```xml
<relationship status="valid">
    <name>ITEM_SITE_EXTRACT &lt;-&gt; PURCHASE_ORDER_LINE</name>
    <expression>
        <refobj>[Database_Layer].[PURCHASE_ORDER_LINE].[SITE_NUMBER]</refobj>=
        <refobj>[Database_Layer].[ITEM_SITE_EXTRACT].[SITE_NUMBER]</refobj>
        AND
        <refobj>[Database_Layer].[PURCHASE_ORDER_LINE].[ITEM_NUMBER]</refobj>=
        <refobj>[Database_Layer].[ITEM_SITE_EXTRACT].[ITEM_NUMBER]</refobj>
    </expression>
    <left>
        <refobj>[Database_Layer].[PURCHASE_ORDER_LINE]</refobj>
        <mincard>zero</mincard>
        <maxcard>many</maxcard>
    </left>
    <right>
        <refobj>[Database_Layer].[ITEM_SITE_EXTRACT]</refobj>
        <mincard>one</mincard>
        <maxcard>one</maxcard>
    </right>
</relationship>
```

**Derived Join Logic:**
```sql
-- Many-to-One relationship
PURCHASE_ORDER_LINE.SITE_NUMBER = ITEM_SITE_EXTRACT.SITE_NUMBER 
AND PURCHASE_ORDER_LINE.ITEM_NUMBER = ITEM_SITE_EXTRACT.ITEM_NUMBER
```

#### 3. Key and Index Definitions

```xml
<key>
    <name>ITEM_SITE_EXTRACTkey</name>
    <queryItems_collection>
        <refobj>[Database_Layer].[ITEM_SITE_EXTRACT].[SITE_NUMBER]</refobj>
        <refobj>[Database_Layer].[ITEM_SITE_EXTRACT].[ITEM_NUMBER]</refobj>
    </queryItems_collection>
</key>
```

**Key Information:**
- Primary Key: (SITE_NUMBER, ITEM_NUMBER)
- Composite key for unique identification

### Package Extraction Process

1. **Parse Package XML**: Extract all `<querySubject>` definitions
2. **Identify Data Sources**: Map data source references to actual database connections
3. **Extract Relationships**: Parse all `<relationship>` elements
4. **Build Table Catalog**: Create comprehensive list of all tables with their schemas
5. **Generate Join Matrix**: Create mapping of all possible joins between tables

---

## Report-Based SQL Extraction

### What is Report-Based Extraction?

Report-based SQL extraction analyzes Cognos report specifications to understand:
- Which tables/fields are actually used in practice
- Complex business logic and calculations
- Filter conditions and parameter usage
- Cross-table data access patterns

### Key Components Extracted

#### 1. Query Definitions

Reports contain `<query>` elements with field selections:

```xml
<query name="MaterialInquiryDetail">
    <source><model/></source>
    <selection>
        <dataItem aggregate="none" name="SITE_NUMBER" rollupAggregate="none">
            <expression>[Database_Layer].[ITEM_SITE_EXTRACT].[SITE_NUMBER]</expression>
        </dataItem>
        <dataItem aggregate="none" name="PO_NUMBER" rollupAggregate="none">
            <expression>[Database_Layer].[PURCHASE_ORDER_LINE].[PO_NUMBER]</expression>
        </dataItem>
        <!-- More fields... -->
    </selection>
</query>
```

**Inferred Multi-Table Usage:**
- Fields from `ITEM_SITE_EXTRACT`: SITE_NUMBER, ITEM_NUMBER, DESCRIPTION, etc.
- Fields from `PURCHASE_ORDER_LINE`: PO_NUMBER, PO_LINE_NUMBER, RELEASE_NUMBER, etc.

#### 2. Filter Conditions

```xml
<detailFilters>
    <detailFilter>
        <filterExpression>[SITE_NUMBER]= ?SiteNumber?</filterExpression>
    </detailFilter>
    <detailFilter use="optional">
        <filterExpression>[PO_NUMBER]=?PO_Number?</filterExpression>
    </detailFilter>
</detailFilters>
```

**Derived WHERE Conditions:**
```sql
WHERE SITE_NUMBER = @SiteNumber
    AND (PO_NUMBER = @PO_Number OR @PO_Number IS NULL)  -- Optional filter
```

#### 3. Calculated Fields

```xml
<dataItem aggregate="notApplicable" name="LOC_1" rollupAggregate="none">
    <expression>
        substring(rpad([PRIMARY_LOC], 12, ' '), 1,2) + ' ' +
        substring(rpad([PRIMARY_LOC], 12, ' '), 3,2) + ' ' +
        substring(rpad([PRIMARY_LOC], 12, ' '), 5,2)
    </expression>
</dataItem>
```

**Derived Calculated Column:**
```sql
SUBSTRING(RPAD(PRIMARY_LOC, 12, ' '), 1, 2) + ' ' +
SUBSTRING(RPAD(PRIMARY_LOC, 12, ' '), 3, 2) + ' ' +
SUBSTRING(RPAD(PRIMARY_LOC, 12, ' '), 5, 2) AS LOC_1
```

### Report Extraction Process

1. **Parse Report XML**: Extract all `<query>` definitions
2. **Identify Table Usage**: Determine which tables are accessed by each query
3. **Analyze Field Usage**: Map specific fields used from each table
4. **Extract Business Logic**: Capture calculated fields and complex expressions
5. **Document Filter Patterns**: Record parameter usage and filter conditions

---

## Join Derivation Logic

### How Joins are Derived

Since Cognos reports don't explicitly show JOIN syntax (Framework Manager handles this automatically), we must derive join logic through multiple methods:

#### Method 1: Package Relationship Analysis

**From Package Relationships:**
```xml
<relationship>
    <expression>
        [Table_A].[Key1] = [Table_B].[Key1] 
        AND [Table_A].[Key2] = [Table_B].[Key2]
    </expression>
    <left>
        <mincard>zero</mincard>
        <maxcard>many</maxcard>
    </left>
    <right>
        <mincard>one</mincard>
        <maxcard>one</maxcard>
    </right>
</relationship>
```

**Derived Join:**
```sql
-- Zero-to-Many suggests LEFT JOIN from right to left
LEFT JOIN Table_A ON Table_B.Key1 = Table_A.Key1 
                  AND Table_B.Key2 = Table_A.Key2
```

#### Method 2: Report Multi-Table Field Usage

**When a report uses fields from multiple tables:**
```xml
<!-- Fields from ITEM_SITE_EXTRACT -->
<expression>[Database_Layer].[ITEM_SITE_EXTRACT].[SITE_NUMBER]</expression>
<!-- Fields from PURCHASE_ORDER_LINE -->
<expression>[Database_Layer].[PURCHASE_ORDER_LINE].[PO_NUMBER]</expression>
```

**Inferred Join Pattern:**
```sql
-- Tables must be joined for the report to work
FROM ITEM_SITE_EXTRACT ise
LEFT JOIN PURCHASE_ORDER_LINE pol 
    ON ise.SITE_NUMBER = pol.SITE_NUMBER 
    AND ise.ITEM_NUMBER = pol.ITEM_NUMBER
```

#### Method 3: Filter Analysis for Join Type Determination

**Optional Filters Suggest LEFT JOIN:**
```xml
<detailFilter use="optional">
    <filterExpression>[PO_NUMBER]=?PO_Number?</filterExpression>
</detailFilter>
```

This suggests that records should be returned even when there's no matching `PO_NUMBER`, indicating a LEFT JOIN.

**Required Filters Suggest INNER JOIN:**
```xml
<detailFilter>
    <filterExpression>[SITE_NUMBER]= ?SiteNumber?</filterExpression>
</detailFilter>
```

Required filters on joined tables suggest INNER JOIN behavior.

### Join Type Decision Matrix

| Cardinality (Left-Right) | Optional Filters | Suggested Join Type |
|---------------------------|------------------|-------------------|
| One-to-Many              | No              | INNER JOIN        |
| One-to-Many              | Yes             | LEFT JOIN         |
| Many-to-One              | No              | INNER JOIN        |
| Many-to-One              | Yes             | RIGHT JOIN        |
| Many-to-Many             | No              | INNER JOIN        |
| Many-to-Many             | Yes             | FULL OUTER JOIN   |

---

## Relationship Analysis

### Types of Relationships Found

#### 1. Direct Foreign Key Relationships

**Package Definition:**
```xml
<relationship>
    <name>SITES &lt;-&gt; ITEM_SITE_EXTRACT</name>
    <expression>
        [Database_Layer].[SITES].[SITE_NUMBER] = 
        [Database_Layer].[ITEM_SITE_EXTRACT].[SITE_NUMBER]
    </expression>
</relationship>
```

**Power BI Relationship:**
- From: SITES[SITE_NUMBER]
- To: ITEM_SITE_EXTRACT[SITE_NUMBER]
- Cardinality: One-to-Many
- Cross Filter Direction: Single

#### 2. Composite Key Relationships

**Package Definition:**
```xml
<relationship>
    <expression>
        [Table_A].[Key1] = [Table_B].[Key1] 
        AND [Table_A].[Key2] = [Table_B].[Key2]
    </expression>
</relationship>
```

**Power BI Approach:**
Since Power BI doesn't support composite relationships directly:
1. Create a calculated column combining the keys
2. Use the combined column for the relationship
3. Or handle via DAX calculations using USERELATIONSHIP

#### 3. Self-Referencing Relationships

**Package Definition:**
```xml
<relationship>
    <name>ITEM_HIERARCHY</name>
    <expression>
        [Database_Layer].[ITEMS].[PARENT_ITEM] = 
        [Database_Layer].[ITEMS].[ITEM_NUMBER]
    </expression>
</relationship>
```

**Power BI Approach:**
- Use PATH() and PATHITEM() functions in DAX
- Create hierarchy columns using calculated columns

### Relationship Validation Rules

1. **Cardinality Validation**: Ensure derived cardinality matches actual data patterns
2. **Referential Integrity**: Verify that all foreign keys have corresponding primary keys
3. **Circular Reference Detection**: Identify and resolve circular relationship chains
4. **Cross-Filter Direction**: Determine optimal filter propagation direction

---

## Integration Between Package and Report Extraction

### Complementary Information

Package and report extraction provide complementary information:

| Aspect | Package Extraction | Report Extraction |
|--------|-------------------|------------------|
| **Table Definitions** | Complete schema | Used fields only |
| **Relationships** | All possible joins | Actually used joins |
| **Business Logic** | Model-level calculations | Report-specific logic |
| **Usage Patterns** | Potential usage | Actual usage |
| **Performance Impact** | Model complexity | Query complexity |

### Integration Process

#### 1. Cross-Reference Validation

```python
def validate_report_against_package(package_tables, report_queries):
    """Validate that report queries use tables defined in the package"""
    for query in report_queries:
        for table_ref in query.tables_used:
            if table_ref not in package_tables:
                log_warning(f"Report uses undefined table: {table_ref}")
```

#### 2. Join Usage Analysis

```python
def analyze_join_usage(package_relationships, report_table_combinations):
    """Determine which package relationships are actually used in reports"""
    used_relationships = []
    for relationship in package_relationships:
        tables_in_relationship = relationship.get_tables()
        for report_tables in report_table_combinations:
            if tables_in_relationship.issubset(report_tables):
                used_relationships.append(relationship)
    return used_relationships
```

#### 3. Optimization Opportunities

**Unused Relationships:**
- Identify package relationships not used by any reports
- Consider removing from Power BI model for simplicity

**Complex Join Patterns:**
- Identify reports using complex multi-table joins
- Consider creating data model optimizations

**Performance Bottlenecks:**
- Identify reports with many optional joins
- Consider pre-aggregated tables or calculated tables

### Integration Workflow

1. **Extract Package Structure**: Get complete data model definition
2. **Extract Report Usage**: Get actual field and table usage patterns
3. **Cross-Reference Analysis**: Validate report usage against package definitions
4. **Optimization Analysis**: Identify unused components and optimization opportunities
5. **Generate Integrated Model**: Create Power BI model incorporating both package structure and report usage patterns

---

## Best Practices and Migration Patterns

### SQL Extraction Best Practices

#### 1. Preserve Business Logic

**Cognos Calculation:**
```xml
<expression>
    IF([QTY_ON_HAND] < [MINIMUM]) THEN 'Reorder Required' 
    ELSE 'Stock OK'
</expression>
```

**Power BI DAX Equivalent:**
```dax
Stock Status = 
IF(
    ITEM_SITE_EXTRACT[QTY_ON_HAND] < ITEM_SITE_EXTRACT[MINIMUM],
    "Reorder Required",
    "Stock OK"
)
```

#### 2. Handle Complex Joins

**Cognos Multi-Table Query:**
```sql
-- Inferred from report field usage
SELECT ise.*, pol.*, mc.*
FROM ITEM_SITE_EXTRACT ise
LEFT JOIN PURCHASE_ORDER_LINE pol 
    ON ise.SITE_NUMBER = pol.SITE_NUMBER 
    AND ise.ITEM_NUMBER = pol.ITEM_NUMBER
LEFT JOIN MATERIAL_CHARGES mc 
    ON ise.SITE_NUMBER = mc.SITE_NUMBER 
    AND ise.ITEM_NUMBER = mc.ITEM_NUMBER
```

**Power BI Approach:**
- Load each table separately
- Create relationships in model view
- Use DAX for cross-table calculations

#### 3. Parameter Handling

**Cognos Parameters:**
```xml
<filterExpression>[SITE_NUMBER]= ?SiteNumber?</filterExpression>
```

**Power BI Approach:**
```dax
-- Create parameter table
Sites Parameter = DISTINCT(ITEM_SITE_EXTRACT[SITE_NUMBER])

-- Use in measure
Filtered Data = 
CALCULATE(
    [Total Quantity],
    ITEM_SITE_EXTRACT[SITE_NUMBER] = SELECTEDVALUE('Sites Parameter'[SITE_NUMBER])
)
```

### Migration Patterns

#### 1. One-to-One Table Migration

**Simple Case:**
```sql
-- Cognos Query Subject
SELECT * FROM [SCHEMA].TABLE_NAME
```

**Power BI M-Query:**
```m
let
    Source = Sql.Database("server", "database"),
    TableData = Source{[Schema="SCHEMA",Item="TABLE_NAME"]}[Data]
in
    TableData
```

#### 2. Complex Join Migration

**Cognos Multi-Table Report:**
- Extract individual table definitions from package
- Identify relationships from package relationships
- Validate join usage from report field usage
- Create separate M-queries for each table
- Define relationships in Power BI model

#### 3. Calculated Field Migration

**Cognos Report Calculation:**
```xml
<expression>
    substring(rpad([PRIMARY_LOC], 12, ' '), 1,2) + ' ' +
    substring(rpad([PRIMARY_LOC], 12, ' '), 3,2)
</expression>
```

**Power BI Calculated Column:**
```dax
Location Formatted = 
MID(REPT(ITEM_SITE_EXTRACT[PRIMARY_LOC] & " ", 12), 1, 2) & " " &
MID(REPT(ITEM_SITE_EXTRACT[PRIMARY_LOC] & " ", 12), 3, 2)
```

### Common Challenges and Solutions

#### 1. Circular Relationships

**Problem:** Package defines relationships that create circular references
**Solution:** 
- Use inactive relationships
- Implement USERELATIONSHIP in DAX
- Create role-playing dimensions

#### 2. Many-to-Many Relationships

**Problem:** Complex many-to-many joins not supported directly in Power BI
**Solution:**
- Create bridge tables
- Use DAX CROSSFILTER function
- Implement virtual relationships in DAX

#### 3. Complex Filtering Logic

**Problem:** Cognos reports with complex nested filter conditions
**Solution:**
- Implement as DAX measures
- Use filter context manipulation
- Create calculated tables for complex scenarios

### Validation and Testing

#### 1. Data Validation

```python
def validate_migrated_data(source_sql, powerbi_table):
    """Validate that migrated data matches source"""
    # Execute source SQL
    source_results = execute_sql(source_sql)
    
    # Get Power BI table data
    powerbi_results = get_powerbi_data(powerbi_table)
    
    # Compare row counts
    assert len(source_results) == len(powerbi_results)
    
    # Compare sample data
    validate_sample_data(source_results, powerbi_results)
```

#### 2. Relationship Validation

```python
def validate_relationships(package_relationships, powerbi_model):
    """Validate that Power BI relationships match package definitions"""
    for relationship in package_relationships:
        powerbi_rel = find_equivalent_relationship(relationship, powerbi_model)
        assert powerbi_rel is not None, f"Missing relationship: {relationship.name}"
        validate_cardinality(relationship, powerbi_rel)
```

#### 3. Performance Testing

```python
def performance_test_migration(original_queries, migrated_measures):
    """Compare performance of original vs migrated queries"""
    for original, migrated in zip(original_queries, migrated_measures):
        original_time = time_query_execution(original)
        migrated_time = time_dax_execution(migrated)
        
        performance_ratio = migrated_time / original_time
        log_performance_metrics(original, migrated, performance_ratio)
```

---

## Conclusion

SQL extraction and join derivation are critical components of successful Cognos to Power BI migration. By understanding both package-level definitions and report-level usage patterns, we can create accurate, performant, and maintainable Power BI data models that preserve the business logic and analytical capabilities of the original Cognos environment.

The key to successful migration lies in:
1. **Comprehensive extraction** of both structural and usage information
2. **Intelligent join derivation** based on multiple evidence sources
3. **Proper integration** of package and report analysis
4. **Adherence to Power BI best practices** while preserving business logic
5. **Thorough validation** of the migrated solution

This guide provides the foundation for implementing robust SQL extraction and join derivation capabilities in the BIMigrator-Cognos system. 