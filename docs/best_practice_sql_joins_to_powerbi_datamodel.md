# Guide: Translating SQL Joins to Power BI Data Models

This document provides a comprehensive guide for converting Cognos reports based on SQL queries into modern Power BI semantic models. The core principle is to shift from the query-based, monolithic approach of traditional reporting to a flexible, high-performance data model using a **Star Schema**.

## The Golden Rule: Model, Don't Merge

In SQL, joins are used to combine, filter, and shape data into a single, flat result set for a specific report. In Power BI, this is an anti-pattern. Instead of replicating SQL joins in Power Query to create one large table, the best practice is to:

1.  **Load Tables Separately**: Load each source table from your SQL query as an independent table in Power BI.
2.  **Identify Facts and Dimensions**: Classify your tables.
    *   **Fact Tables**: Contain transactional data and numeric values to be aggregated (e.g., `MATERIAL_CHARGES`, `INVOICES`).
    *   **Dimension Tables**: Contain descriptive attributes used for filtering and grouping (e.g., `SUPPLIERS`, `PRODUCTS`).
3.  **Create Relationships**: Use Power BI's Model View to define relationships between the tables. These relationships allow data to be "joined" dynamically at query time when a user interacts with a report.

**Why is this better?**
*   **Performance**: Power BI's VertiPaq engine is highly optimized for star schemas.
*   **Flexibility**: The model can answer many business questions, not just the one the original SQL query was written for.
*   **Simplicity**: DAX calculations are simpler and more intuitive on a well-structured model.
*   **Maintainability**: The model is easier to understand and extend.

---

## Part 1: Handling Standard SQL Join Types

This section covers how to model the logical intent of each standard SQL join.

### 1. INNER JOIN & 2. LEFT OUTER JOIN

An `INNER JOIN` returns only rows where the key exists in both tables. A `LEFT JOIN` returns all rows from the left table and matched rows from the right. In Power BI, both are modeled identically; the visual behavior determines the outcome.

**SQL Example:**
```sql
-- INNER JOIN
SELECT p.ProductName, s.SaleAmount FROM Products p
INNER JOIN Sales s ON p.ProductKey = s.ProductKey

-- LEFT JOIN
SELECT p.ProductName, s.SaleAmount FROM Products p
LEFT JOIN Sales s ON p.ProductKey = s.ProductKey
```

**Power BI Model:**

#### M-Query (`Products` and `Sales` tables)
You load each table from its source. The M-query is simply the source and transformation steps for each table independently. For example:

```m
// M-Query for 'Products' table
let
    Source = Csv.Document(File.Contents("C:\data\products.csv"), [Delimiter=",", Encoding=1252]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedType = Table.TransformColumnTypes(PromotedHeaders,{{"ProductKey", Int64.Type}, {"ProductName", type text}})
in
    ChangedType
```
```m
// M-Query for 'Sales' table
let
    Source = Csv.Document(File.Contents("C:\data\sales.csv"), [Delimiter=",", Encoding=1252]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedType = Table.TransformColumnTypes(PromotedHeaders,{{"SalesKey", Int64.Type}, {"ProductKey", Int64.Type}, {"SaleAmount", Currency.Type}})
in
    ChangedType
```

#### Table TMDL (`/tables/Products.tmdl` and `/tables/Sales.tmdl`)
```tmdl
// tables/Products.tmdl
table Products
    lineageTag: f4a7c1b1-1a2b-3c4d-5e6f-7a8b9c0d1e2f

    column ProductKey
        dataType: int64
        isKey
        sourceColumn: ProductKey
        lineageTag: ...

    column ProductName
        dataType: string
        sourceColumn: ProductName
        lineageTag: ...

    partition Products = m
        mode: import
        source = #"M-Query for 'Products' table"
```
```tmdl
// tables/Sales.tmdl
table Sales
    lineageTag: a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6

    column SalesKey
        dataType: int64
        isKey
        sourceColumn: SalesKey
        lineageTag: ...

    column ProductKey
        dataType: int64
        sourceColumn: ProductKey
        lineageTag: ...

    column SaleAmount
        dataType: decimal
        formatString: "$#,0.00"
        sourceColumn: SaleAmount
        lineageTag: ...

    partition Sales = m
        mode: import
        source = #"M-Query for 'Sales' table"
```

#### Relationships TMDL (`relationships.tmdl`)
```tmdl
// relationships.tmdl
relationship 'Products to Sales'
    fromTable: Products
    fromColumn: ProductKey
    toTable: Sales
    toColumn: ProductKey
    cardinality: oneToMany
```

**Resulting Behavior:**
*   **INNER JOIN**: When you place `ProductName` and `SUM(SaleAmount)` in a visual, only products with sales will appear.
*   **LEFT JOIN**: When you place `ProductName` in a visual, all products appear. When you add `SUM(SaleAmount)`, products with no sales will show `(Blank)`.

---
### 3. RIGHT OUTER JOIN

A `RIGHT JOIN` is a `LEFT JOIN` in reverse. You model it the same way. The visual you build determines the result.

---
### 4. FULL OUTER JOIN

A `FULL OUTER JOIN` returns all rows from both tables. This requires creating a central, shared dimension table containing all unique keys from both tables.

**SQL Example:**
```sql
SELECT p.ProductName, s.SaleAmount FROM Products p
FULL OUTER JOIN Sales s ON p.ProductKey = s.ProductKey
```

**Power BI Model:**

#### M-Query (New `Dim_Products` table)
This query combines the keys from both `Products` and `Sales` to create a complete dimension.

```m
// M-Query for 'Dim_Products' table
let
    // Get keys from the Products table
    ProductKeys = Table.Distinct(Table.SelectColumns(Products, {"ProductKey", "ProductName"})),

    // Get keys from the Sales table that might not be in Products
    SalesKeys = Table.Distinct(Table.SelectColumns(Sales, {"ProductKey"})),

    // Combine, get unique list, and remove nulls
    Combined = Table.Combine({ProductKeys, SalesKeys}),
    UniqueKeys = Table.Distinct(Combined, {"ProductKey"}),
    FilteredRows = Table.SelectRows(UniqueKeys, each ([ProductKey] <> null))
in
    FilteredRows
```
*Note: You would then merge this key list back against your original `Products` table to bring in `ProductName` and other attributes.*

#### Table TMDL (`/tables/Dim_Products.tmdl`)
```tmdl
// tables/Dim_Products.tmdl
table Dim_Products
    lineageTag: ...

    column ProductKey
        dataType: int64
        isKey
        sourceColumn: ProductKey
        lineageTag: ...

    column ProductName
        dataType: string
        sourceColumn: ProductName
        lineageTag: ...

    partition Dim_Products = m
        mode: import
        source = #"M-Query for 'Dim_Products' table"
```

#### Relationships TMDL (`relationships.tmdl`)
You relate the new dimension to **both** original tables, which now act as fact tables. The original relationship is removed.

```tmdl
// relationships.tmdl

// This relationship connects the new dimension to the Sales fact table
relationship 'Dim_Products to Sales'
    fromTable: Dim_Products
    fromColumn: ProductKey
    toTable: Sales
    toColumn: ProductKey
    cardinality: oneToMany

// This relationship connects the new dimension to the Products source table
// The relationship should be INACTIVE to avoid ambiguity if Products has measures.
// If Products is purely a lookup, this can be active.
relationship 'Dim_Products to Products'
    fromTable: Dim_Products
    fromColumn: ProductKey
    toTable: Products
    toColumn: ProductKey
    cardinality: oneToOne
    isActive: false
```

---
### 5. CROSS JOIN

A `CROSS JOIN` (Cartesian product) should **not** be modeled with relationships. Load the tables independently and handle the logic in DAX.

**SQL Example:**
```sql
SELECT p.ProductName, d.CalendarYear FROM Products p, Dim_Date d
```

**Power BI Model:**

#### M-Query, Table TMDL
Load `Products` and `Dim_Date` as independent tables.

#### Relationships TMDL (`relationships.tmdl`)
```tmdl
// relationships.tmdl
// NO RELATIONSHIP is created between Products and Dim_Date for a CROSS JOIN scenario.
```

#### DAX Measure
Use DAX to create the Cartesian product logic inside a measure.
```dax
Sales All Combinations =
CALCULATE(
    [Total Sales],
    CROSSJOIN(
        ALL( 'Products'[ProductName] ),
        ALL( 'Dim_Date'[CalendarYear] )
    )
)
```

---
## Part 2: Handling Complex Join Patterns

### 1. Joins on Multiple Columns (Composite Keys)

Create a single surrogate key column in Power Query for the relationship.

**SQL Example:**
```sql
SELECT ... FROM PURCHASE_ORDER_LINE pol
LEFT JOIN MATERIAL_CHARGES mc
    ON pol.SITE_NUMBER = mc.SITE_NUMBER
    AND pol.ITEM_NUMBER = mc.ITEM_NUMBER
```

**Power BI Model:**

#### M-Query (Adding keys and creating the dimension)

1.  **Add Custom Column to `PURCHASE_ORDER_LINE`**:
    ```m
    // Add to existing query for PURCHASE_ORDER_LINE
    AddCompositeKey = Table.AddColumn(PreviousStep, "SiteItemKey", each [SITE_NUMBER] & "|" & [ITEM_NUMBER], type text)
    ```

2.  **Add Custom Column to `MATERIAL_CHARGES`**:
    ```m
    // Add to existing query for MATERIAL_CHARGES
    AddCompositeKey = Table.AddColumn(PreviousStep, "SiteItemKey", each [SITE_NUMBER] & "|" & [ITEM_NUMBER], type text)
    ```

3.  **Create `Dim_Site_Items` Dimension**:
    ```m
    // M-Query for new 'Dim_Site_Items' table
    let
        Items_From_Charges = Table.SelectColumns(MATERIAL_CHARGES,{"SiteItemKey"}),
        Items_From_Lines = Table.SelectColumns(PURCHASE_ORDER_LINE, {"SiteItemKey"}),
        CombinedItems = Table.Combine({Items_From_Charges, Items_From_Lines}),
        UniqueItemPairs = Table.Distinct(CombinedItems, {"SiteItemKey"}),
        FilteredRows = Table.SelectRows(UniqueItemPairs, each [SiteItemKey] <> null)
    in
        FilteredRows
    ```

#### Table TMDL
You would have TMDL files for `PURCHASE_ORDER_LINE` and `MATERIAL_CHARGES` (both now including the `SiteItemKey` column), and a new file for `Dim_Site_Items`.

```tmdl
// tables/Dim_Site_Items.tmdl
table Dim_Site_Items
    lineageTag: ...

    column SiteItemKey
        dataType: string
        isKey
        sourceColumn: SiteItemKey
        lineageTag: ...

    partition Dim_Site_Items = m
        mode: import
        source = #"M-Query for new 'Dim_Site_Items' table"
```

#### Relationships TMDL (`relationships.tmdl`)
```tmdl
relationship 'Dim_Site_Items to PURCHASE_ORDER_LINE'
    fromTable: Dim_Site_Items
    fromColumn: SiteItemKey
    toTable: PURCHASE_ORDER_LINE
    toColumn: SiteItemKey
    cardinality: oneToMany

relationship 'Dim_Site_Items to MATERIAL_CHARGES'
    fromTable: Dim_Site_Items
    fromColumn: SiteItemKey
    toTable: MATERIAL_CHARGES
    toColumn: SiteItemKey
    cardinality: oneToMany
```

---
### 2. Multiple Joins (Chained Joins)

This is a classic star schema scenario. Create multiple shared dimensions.

**SQL Example:**
```sql
SELECT ...
FROM PURCHASE_ORDER_LINE pol
LEFT JOIN MATERIAL_CHARGES mc ON pol.ItemKey = mc.ItemKey
LEFT JOIN INVOICES inv ON pol.PO_Number = inv.PO_Number
LEFT JOIN SUPPLIERS sup ON pol.SupplierID = sup.SupplierID
```

**Power BI Model:**

#### M-Query
You would create two new dimension tables using the same pattern as the composite key example:
*   **`Dim_Items`**: Unique list of `ItemKey` from `PURCHASE_ORDER_LINE` and `MATERIAL_CHARGES`.
*   **`Dim_POs`**: Unique list of `PO_Number` from `PURCHASE_ORDER_LINE` and `INVOICES`.
Your `SUPPLIERS` table already acts as a dimension (`Dim_Suppliers`).

#### Table TMDL
You will have TMDL files for your three fact tables (`PURCHASE_ORDER_LINE`, `MATERIAL_CHARGES`, `INVOICES`) and your three dimension tables (`Dim_Items`, `Dim_POs`, `Dim_Suppliers`).

#### Relationships TMDL (`relationships.tmdl`)
This defines the full star schema.
```tmdl
// --- Item Relationships ---
relationship 'Dim_Items to PURCHASE_ORDER_LINE'
    fromTable: Dim_Items
    fromColumn: ItemKey
    toTable: PURCHASE_ORDER_LINE
    toColumn: ItemKey
    cardinality: oneToMany

relationship 'Dim_Items to MATERIAL_CHARGES'
    fromTable: Dim_Items
    fromColumn: ItemKey
    toTable: MATERIAL_CHARGES
    toColumn: ItemKey
    cardinality: oneToMany

// --- Purchase Order Relationships ---
relationship 'Dim_POs to PURCHASE_ORDER_LINE'
    fromTable: Dim_POs
    fromColumn: PO_Number
    toTable: PURCHASE_ORDER_LINE
    toColumn: PO_Number
    cardinality: oneToMany

relationship 'Dim_POs to INVOICES'
    fromTable: Dim_POs
    fromColumn: PO_Number
    toTable: INVOICES
    toColumn: PO_Number
    cardinality: oneToMany

// --- Supplier Relationship ---
relationship 'Dim_Suppliers to PURCHASE_ORDER_LINE'
    fromTable: Dim_Suppliers
    fromColumn: SupplierID
    toTable: PURCHASE_ORDER_LINE
    toColumn: SupplierID
    cardinality: oneToMany
```
This model is vastly superior to a single merged table. It allows you to analyze invoice data by supplier, even though they are not directly joined in the SQL query. The relationships flow through the shared dimensions. 