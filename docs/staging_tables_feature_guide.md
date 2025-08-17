# Staging Tables Feature Guide

## Overview

The Staging Tables feature automatically analyzes SQL joins in Cognos packages and reports to create optimized staging tables for Power BI semantic models. This feature helps implement Power BI best practices by:

- **Creating Star Schema Relationships**: Converting complex SQL joins into optimized dimension-fact relationships
- **Implementing Shared Keys**: Adding composite and surrogate keys for optimal relationship performance 
- **Optimizing Join Performance**: Reducing query complexity through pre-computed staging tables
- **Following Power BI Best Practices**: Adhering to VertiPaq engine optimization guidelines

## Key Components

### 1. SQL Join Analyzer (`sql_join_analyzer.py`)
- Parses Cognos package relationships and report SQL queries
- Extracts join patterns including composite keys and complex relationships
- Uses LLM service for advanced SQL analysis (optional)
- Identifies tables suitable for staging table optimization

### 2. Staging Table Analyzer (`staging_table_analyzer.py`)
- Analyzes join patterns to determine optimal staging table structure
- Creates staging table definitions with shared keys
- Classifies tables as facts or dimensions
- Generates performance optimization recommendations

### 3. Staging M-Query Converter (`staging_mquery_converter.py`)
- Generates optimized M-queries for staging tables
- Creates shared key columns using DAX formulas
- Uses LLM service for advanced M-query generation (optional)
- Handles composite key scenarios with surrogate keys

### 4. Staging Relationship Generator (`staging_relationship_generator.py`)
- Creates Power BI relationships between staging tables and fact tables
- Determines optimal cardinality and cross-filtering behavior
- Generates TMDL relationship definitions
- Handles relationship conflicts and circular references

### 5. Fact Table Updater (`fact_table_updater.py`)
- Updates existing fact table M-queries to include shared keys
- Preserves existing transformations while adding staging optimization
- Validates updated queries for correctness
- Creates backup of original queries

### 6. Staging Orchestrator (`staging_orchestrator.py`)
- Coordinates the complete staging table implementation process
- Validates staging table configurations
- Generates comprehensive documentation
- Provides implementation recommendations

## Configuration

### Settings.json Configuration

```json
{
  "staging_tables": {
    "enabled": false,
    "mode": "auto",
    "prefix": "Staging_",
    "auto_create_shared_keys": true,
    "join_analysis": {
      "use_llm": true,
      "min_join_confidence": 0.8,
      "composite_key_handling": "create_surrogate"
    }
  }
}
```

### Configuration Options

| Setting | Options | Description |
|---------|---------|-------------|
| `enabled` | `true`/`false` | Enable or disable staging table creation |
| `mode` | `"auto"`, `"manual"`, `"off"` | How staging tables are created |
| `prefix` | string | Prefix for staging table names |
| `auto_create_shared_keys` | `true`/`false` | Automatically create shared key columns |
| `use_llm` | `true`/`false` | Use LLM service for advanced analysis |
| `min_join_confidence` | 0.0-1.0 | Minimum confidence for join pattern detection |
| `composite_key_handling` | `"create_surrogate"`, `"concatenate"` | How to handle composite keys |

## Usage

### 1. Enable Staging Tables

Update your `settings.json`:

```json
{
  "staging_tables": {
    "enabled": true,
    "mode": "auto"
  }
}
```

### 2. Run Package Migration

The staging table functionality is automatically integrated with package migration:

```python
from cognos_migrator.migrations.package import integrate_staging_tables_with_package_migration

results = integrate_staging_tables_with_package_migration(
    package_file_path="path/to/package.xml",
    output_path="output/directory",
    settings=your_settings
)
```

### 3. Review Results

The system will generate:
- **Staging table TMDL files** in `staging_tables/` directory
- **Updated fact table M-queries** with shared keys
- **Relationship definitions** in TMDL format
- **Comprehensive documentation** explaining the implementation

## Example Output

### Generated Staging Table

```tmdl
table Staging_Orders_Customers
    lineageTag: staging-orders-customers

    column OrderID
        dataType: string
        sourceColumn: OrderID
        isKey
        lineageTag: staging-orderid

    column CustomerKey
        dataType: string
        sourceColumn: CustomerKey
        isKey
        lineageTag: staging-customerkey

    partition Staging_Orders_Customers = m
        mode: import
        source =
            let
                Source = Sql.Database("server", "database"),
                Orders = Source{[Schema="dbo",Item="Orders"]}[Data],
                Customers = Source{[Schema="dbo",Item="Customers"]}[Data],
                JoinedData = Table.NestedJoin(Orders, {"CustomerID"}, Customers, {"CustomerID"}, "Customer", JoinKind.Inner),
                AddSharedKey = Table.AddColumn(JoinedData, "CustomerKey", each [CustomerID], type text),
                Result = AddSharedKey
            in
                Result
```

### Generated Relationships

```tmdl
relationship 'Staging_Orders_Customers_to_Orders_Staging' = {
    fromTable: Staging_Orders_Customers
    fromColumn: CustomerKey
    toTable: Orders
    toColumn: CustomerKey
    cardinality: oneToMany
    crossFilteringBehavior: oneDirection
    isActive: true
    annotations: [
        Annotation(Name="StagingRelationship", Value="true"),
        Annotation(Name="RelationshipType", Value="staging_to_fact")
    ]
}
```

## Best Practices

### When to Use Staging Tables

✅ **Good candidates:**
- Tables with complex multi-column joins
- Frequently joined tables in reports
- Tables with composite key relationships
- Performance-critical data models

❌ **Avoid staging tables for:**
- Simple single-table queries
- Rarely accessed lookup tables
- Already optimized star schema models

### Performance Considerations

1. **Monitor Model Size**: Staging tables add to overall model size
2. **Refresh Performance**: Additional tables require more refresh time
3. **Memory Usage**: More tables use more memory during processing
4. **Relationship Complexity**: Too many relationships can impact performance

### Migration Strategy

1. **Start Small**: Enable staging tables for a subset of complex joins
2. **Test Performance**: Compare query performance before and after
3. **Monitor Refresh**: Ensure refresh times remain acceptable
4. **User Feedback**: Validate that reports work correctly with new structure

## Troubleshooting

### Common Issues

**Staging tables not being created:**
- Check that `staging_tables.enabled` is `true` in settings
- Verify that the package contains complex join relationships
- Ensure minimum confidence thresholds are appropriate

**M-query generation failures:**
- Check LLM service connectivity if enabled
- Review source table definitions for completeness
- Validate that shared key formulas are syntactically correct

**Relationship conflicts:**
- Review existing relationships for conflicts
- Check for circular relationship patterns
- Consider deactivating conflicting relationships

### Validation Steps

1. **Check Generated Files**: Verify TMDL files are created correctly
2. **Validate M-Queries**: Test M-queries in Power Query Editor
3. **Test Relationships**: Ensure relationships work in Power BI Desktop
4. **Performance Testing**: Compare query performance metrics

## Advanced Configuration

### Custom Join Analysis

For advanced scenarios, you can customize join analysis:

```json
{
  "staging_tables": {
    "join_analysis": {
      "custom_patterns": {
        "fact_indicators": ["amount", "quantity", "count", "value"],
        "dimension_indicators": ["name", "description", "category", "type"]
      },
      "relationship_rules": {
        "prefer_left_joins": true,
        "composite_key_threshold": 2
      }
    }
  }
}
```

### LLM Service Integration

When using LLM service for advanced analysis:

```json
{
  "staging_tables": {
    "join_analysis": {
      "use_llm": true,
      "llm_confidence_threshold": 0.85,
      "llm_timeout": 30,
      "fallback_to_template": true
    }
  }
}
```

## API Reference

### Core Classes

#### `StagingTableOrchestrator`
Main orchestrator class that coordinates staging table implementation.

```python
orchestrator = StagingTableOrchestrator(llm_service_client=None)
results = orchestrator.implement_staging_tables(
    package_info=package_data,
    report_queries=report_queries,
    data_model=current_model,
    output_path=output_directory,
    settings=staging_settings
)
```

#### `SQLJoinAnalyzer`
Analyzes SQL patterns and relationships.

```python
analyzer = SQLJoinAnalyzer(llm_service_client=llm_client)
join_patterns = analyzer.analyze_package_joins(package_info)
```

#### `StagingMQueryConverter`
Generates M-queries for staging tables.

```python
converter = StagingMQueryConverter(llm_service_client=llm_client)
m_query = converter.convert_staging_table_to_m_query(
    staging_definition=staging_table,
    shared_keys=shared_keys,
    connection_info=db_connection,
    settings=conversion_settings
)
```

## Migration Guide

### From Complex SQL to Staging Tables

**Before (Complex SQL Join):**
```sql
SELECT o.OrderID, o.OrderDate, c.CustomerName, p.ProductName, od.Quantity
FROM Orders o
INNER JOIN Customers c ON o.CustomerID = c.CustomerID
INNER JOIN OrderDetails od ON o.OrderID = od.OrderID
INNER JOIN Products p ON od.ProductID = p.ProductID
WHERE o.OrderDate >= '2023-01-01'
```

**After (Staging Table + Star Schema):**
- **Staging Table**: `Staging_Orders_Details` (combines Orders + OrderDetails)
- **Relationships**: 
  - `Customers` (1) → `Staging_Orders_Details` (*)
  - `Products` (1) → `Staging_Orders_Details` (*) 
- **Benefits**: Better performance, cleaner DAX, star schema compliance

### Implementation Checklist

- [ ] Enable staging tables in settings.json
- [ ] Run package migration with staging enabled
- [ ] Review generated staging tables and relationships
- [ ] Test Power BI model functionality
- [ ] Validate query performance
- [ ] Update documentation and training materials
- [ ] Deploy to production environment

## Support and Maintenance

### Monitoring

- **Refresh Performance**: Monitor data refresh times
- **Query Performance**: Track DAX query execution times
- **Model Size**: Monitor overall model size growth
- **User Experience**: Collect feedback on report performance

### Updates

- **Schema Changes**: Update staging tables when source schema changes
- **Relationship Optimization**: Periodically review relationship performance
- **Settings Tuning**: Adjust confidence thresholds based on results

For additional support, refer to the generated documentation in your output directory or consult the Power BI best practices documentation. 