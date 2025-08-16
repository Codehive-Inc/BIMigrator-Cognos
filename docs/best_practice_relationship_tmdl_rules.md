# Rules for Generating Power BI Relationships TMDL Files

This document outlines the rules and best practices for generating proper `relationships.tmdl` files for Power BI based on analysis of the Tableau migration implementation.

## 1. Relationship Identifier Format

### Rule 1.1: Use UUIDs for Relationship IDs
- Generate a unique UUID for each relationship using `uuid.uuid4()`
- Example: `relationship c6015d5c-359d-4daf-bc9d-9a3be6e5b80b`
- Do not use descriptive names like `Relationship_TableA_TableB`

### Rule 1.2: Relationship Declaration Format
```
relationship [UUID]
    [properties]
```

## 2. Table and Column Reference Format

### Rule 2.1: Table Name Format
- Enclose table names in single quotes
- Example: `'TableName'`

### Rule 2.2: Column Reference Format
- Format: `'TableName'.ColumnName`
- Tables are enclosed in single quotes, columns are not
- Example: `fromColumn: 'Custom SQL Query'.asup_date`

## 3. Cardinality Properties

### Rule 3.1: Use Proper Cardinality Direction
- Use `fromCardinality` when specifying the cardinality of the "from" table
- Use `toCardinality` when specifying the cardinality of the "to" table
- Do not use both in the same relationship

### Rule 3.2: Cardinality Values
- Valid values are `one` or `many`
- Example: `fromCardinality: one` or `toCardinality: many`

## 4. Cross-Filtering Behavior

### Rule 4.1: Property Name
- Use `crossFilteringBehavior` (not `cross_filter_behavior` or other variants)

### Rule 4.2: Valid Values
- `BothDirections` - Filter in both directions (equivalent to "both")
- `OneDirection` - Filter in one direction only (equivalent to "one")
- `Automatic` - Let Power BI determine the behavior

### Rule 4.3: Format
- Example: `crossFilteringBehavior: BothDirections`

## 5. Active Status

### Rule 5.1: Property Name
- Use `isActive` (not `is_active` or other variants)

### Rule 5.2: Value Format
- Use lowercase `true` or `false`
- Example: `isActive: true`

## 6. Optional Properties

### Rule 6.1: Date Behavior
- Include `joinOnDateBehavior` only for date-based relationships
- Example: `joinOnDateBehavior: datePartOnly`

### Rule 6.2: Property Inclusion
- Only include properties that have values
- Do not include properties with null or default values

## 7. Property Indentation and Formatting

### Rule 7.1: Indentation
- Use tabs or consistent spaces for indentation
- All properties should be at the same indentation level

### Rule 7.2: Property Order
- Recommended order:
  1. `joinOnDateBehavior` (if applicable)
  2. `toCardinality` or `fromCardinality`
  3. `fromColumn`
  4. `toColumn`
  5. `crossFilteringBehavior`
  6. `isActive`

## 8. Example Relationships

### Example 1: Basic Relationship
```
relationship 468c3e90-fea1-424e-9426-caf0249940ab
	fromColumn: 'Custom SQL Query'.Tab_module
	toColumn: 'Custom SQL Query2'.OBJ_SMF_TABLES
	crossFilteringBehavior: OneDirection
	fromCardinality: one
	isActive: true
```

### Example 2: Relationship with To-Cardinality
```
relationship 2b76d3f4-1f3e-cc2c-39a8-f518304bc5f2
	toCardinality: many
	fromColumn: 'I_D_OFS_DOM_RESOURCE_HIERARCHY'.RESOURCE_ID
	toColumn: 'C_DOM_ACTIVITY_DETAIL_DTL_METER'.RESOURCE_ID
```

### Example 3: Date-Based Relationship
```
relationship 7054b222-f2b8-46f7-8026-5d9b2ce889d6
	joinOnDateBehavior: datePartOnly
	fromColumn: 'A_F_OFS_DOM_AUTO_ROUTING'.AUTO_ROUTED_TO_DATE
	toColumn: 'LocalDateTable_9f42c05f-3025-4592-b928-d85151e148cd'.Date
```

## 9. Implementation Considerations

### Rule 9.1: Data Model
- Use a proper data model class (e.g., `PowerBiRelationship`) with all necessary fields
- Include UUID generation in the model creation process

### Rule 9.2: Template Generation
- Use a template engine (e.g., Jinja2) for consistent formatting
- Ensure the template handles all required and optional properties

### Rule 9.3: Deduplication
- Implement deduplication to avoid duplicate relationships
- Use a unique key based on from/to tables and columns

## 10. Common Issues and Solutions

### Issue 10.1: Duplicate Relationships
- **Problem**: Multiple identical relationships in the output file
- **Solution**: Implement deduplication based on from/to tables and columns

### Issue 10.2: Missing or Incorrect UUIDs
- **Problem**: Relationships have descriptive IDs instead of UUIDs
- **Solution**: Generate UUIDs during relationship creation

### Issue 10.3: Incorrect Cardinality Direction
- **Problem**: Using wrong cardinality property (from vs. to)
- **Solution**: Determine the correct direction based on relationship analysis

### Issue 10.4: Incorrect Table/Column Formatting
- **Problem**: Missing quotes around table names or incorrect separators
- **Solution**: Use consistent formatting in templates
