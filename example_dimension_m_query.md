# Example M-Query for Dim_PURCHASE_ORDER_DESCRIPTIONS_PURCHASE_ORDER_LINE

Based on the successful implementation, here's what the M-query should look like for the dimension table:

```powerquery
let
    // Get data from PURCHASE_ORDER_DESCRIPTIONS
    Data_From_PURCHASE_ORDER_DESCRIPTIONS = Table.SelectColumns(PURCHASE_ORDER_DESCRIPTIONS, {"PO_NUMBER", "RELEASE_NUMBER", "PO_LINE_NUMBER", "SITE_NUMBER"}),
    // Get data from PURCHASE_ORDER_LINE
    Data_From_PURCHASE_ORDER_LINE = Table.SelectColumns(PURCHASE_ORDER_LINE, {"PO_NUMBER", "RELEASE_NUMBER", "PO_LINE_NUMBER", "SITE_NUMBER"}),
    // Combine data from all source tables
    CombinedData = Table.Combine({Data_From_PURCHASE_ORDER_DESCRIPTIONS, Data_From_PURCHASE_ORDER_LINE}),
    // Get unique combinations of dimension keys
    UniqueRows = Table.Distinct(CombinedData, {"PO_NUMBER", "RELEASE_NUMBER", "PO_LINE_NUMBER", "SITE_NUMBER"}),
    // Create composite key for relationships
    AddCompositeKey = Table.AddColumn(UniqueRows, "PO_NUMBER_RELEASE_NUMBER_PO_LINE_NUMBER_SITE_NUMBER_Key", each Text.Combine({[PO_NUMBER], [RELEASE_NUMBER], [PO_LINE_NUMBER], [SITE_NUMBER]}, "|"), type text),
    // Filter out rows with null or empty composite keys
    FilteredRows = Table.SelectRows(AddCompositeKey, each [PO_NUMBER_RELEASE_NUMBER_PO_LINE_NUMBER_SITE_NUMBER_Key] <> null and [PO_NUMBER_RELEASE_NUMBER_PO_LINE_NUMBER_SITE_NUMBER_Key] <> "")
in
    FilteredRows
```

## Summary

✅ **Successfully implemented proper Star Schema with dimension tables:**

1. **8 Dimension Tables Created** (replacing staging tables):
   - `Dim_PURCHASE_ORDER_DESCRIPTIONS_PURCHASE_ORDER_LINE` - 4 columns + composite key
   - `Dim_ITEM_SITE_EXTRACT_STORAGE_LOCATION` - 2 columns + composite key
   - `Dim_ITEM_SITE_EXTRACT_PURCHASE_ORDER_LINE` - 2 columns + composite key
   - And 5 more dimension tables...

2. **Proper Composite Key Relationships**:
   - Single composite key columns instead of multiple column relationships
   - One-to-many cardinality from dimension to fact tables
   - OneDirection cross-filtering (ideal for star schema performance)
   - Example: `PO_NUMBER_RELEASE_NUMBER_PO_LINE_NUMBER_SITE_NUMBER_Key`

3. **Enhanced Power BI Model Structure**:
   - **Fact Tables**: PURCHASE_ORDER_LINE, MATERIAL_CHARGES, etc. (business events)
   - **Dimension Tables**: Dim_* tables (who, what, where, when lookups)
   - **Clean Relationships**: Single composite key joins instead of composite relationships

4. **Benefits Achieved**:
   - ✅ No more composite key relationships (Power BI performance bottleneck)
   - ✅ Proper star schema design (gold standard for Power BI)
   - ✅ Single composite key columns for efficient joins
   - ✅ Clean dimension tables for easy filtering and grouping
   - ✅ Automatic M-query generation for dimension tables

The implementation successfully transforms the complex composite key relationships from Cognos into a clean, efficient Power BI star schema model! 