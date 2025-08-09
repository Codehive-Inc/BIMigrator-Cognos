# Best Practices for Date Tables and Time Intelligence in BIMigrator-Cognos

This document outlines the best practice for handling date tables, relationships, and time-intelligence functions within the BIMigrator-Cognos project. The system has been updated to follow a modern, efficient approach that aligns with Power BI development standards.

## The Central Date Table Strategy

Instead of creating multiple, separate "local" date tables for each fact table, the migrator now implements a **single, central date table** for the entire data model. This table is named `CentralDateTable` by default.

This approach provides several key benefits:
- **Consistency**: All time-based analysis is filtered through one consistent source of date information.
- **Reduced Model Size**: Eliminates redundant date tables, keeping the model lean and performant.
- **Simplified Management**: All date and time logic is managed in one place.

## Active vs. Inactive Relationships

When a source table contains multiple date columns (e.g., `OrderDate`, `ShipDate`, `DueDate`), a relationship is created between *each* of these columns and the `CentralDateTable`. However, to avoid ambiguity in the data model, only **one of these relationships can be active at a time**.

The system handles this automatically as follows:

1.  **Primary Date Column (Active Relationship)**: The first date column, when sorted alphabetically and case-insensitively (e.g., `datecreated` before `LastUpdated`), is designated as the primary date column. It receives an **active relationship** to the `CentralDateTable`. This is the default relationship that will be used in most visuals and calculations. In the TMDL file, this is indicated with a `variation` block.

2.  **Secondary Date Columns (Inactive Relationships)**: All other date columns in the table receive **inactive relationships** to the `CentralDateTable`. These relationships do not affect visuals by default but can be activated on-demand within specific DAX measures.

## Activating Relationships with USERELATIONSHIP

The power of inactive relationships comes from the `USERELATIONSHIP` DAX function. This function allows you to temporarily activate an inactive relationship for the duration of a specific calculation, without changing the default behavior of the model.

### Automatic Measure Generation

To promote this best practice and provide immediate utility, the BIMigrator-Cognos tool **automatically generates a sample DAX measure** for each inactive relationship it creates.

For example, if the `Agency` table has an inactive relationship on its `LastUpdated` column, the following measure will be automatically added to the `Agency` table's definition:

```dax
measure 'Count of Rows by LastUpdated' = ```
        CALCULATE(
            COUNTROWS('Agency'),
            USERELATIONSHIP('CentralDateTable'[Date], 'Agency'[LastUpdated])
        )
```
```
This provides a ready-to-use example that developers can either use directly or adapt for more complex calculations, demonstrating how to slice the data by a non-default date field. This saves time and enforces the correct DAX pattern for handling multiple date fields. 