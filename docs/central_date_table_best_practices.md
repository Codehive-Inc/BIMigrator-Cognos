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

## A Note on Variations: The Single Default Hierarchy Rule

A `variation` in Power BI is a powerful shortcut that provides a better user experience. It tells the report editor: "When a user drags this column into a visual, automatically use the hierarchy from the related dimension table (e.g., `CentralDateTable.'Date Hierarchy'`) as the default."

However, Power BI enforces a strict, model-wide rule: **A specific hierarchy in a shared dimension table can only be designated as the default `variation` for ONE column across the ENTIRE data model.**

### The Automated Solution

The BIMigrator-Cognos tool handles this limitation automatically and deterministically.

1.  **A Single Primary Table is Chosen**: The migrator identifies all tables with date columns and sorts them alphabetically. The **first table in this list** is designated as the primary fact table for date analysis.

2.  **Variation is Applied Once**: The `variation` block is added **only** to the primary date column of this single, primary table.

3.  **Other Tables**: All other tables will still have their active and inactive relationships to the `CentralDateTable`, and their automatically generated DAX measures will work perfectly. They simply will not have the `variation` notation.

### What This Means for Developers

*   **Relationships:** All active and inactive relationships will function as expected for all tables.
*   **User Experience:**
    *   When you drag the primary date column from the **primary table** (e.g., `Assistance[datecreated]`) into a visual, it will automatically expand to the Year, Quarter, Month, Day hierarchy.
    *   When you drag a primary date column from any **other table** (e.g., `Agency[datecreated]`) into a visual, it will appear as a raw `datetime` value. To analyze it by month or year, you must drag the `Month` or `Year` fields directly from the `CentralDateTable` into the visual, and it will work perfectly.

This approach ensures the model is always valid while retaining the vast majority of the time-intelligence functionality and user convenience.

## Configuration via `settings.json`

The behavior of the `CentralDateTable` can be controlled via the `settings.json` file in the root of the project. This allows you to choose the appropriate mode for your specific reporting needs without changing the code.

```json
{
  "date_table_mode": "visible"
}
```

### Available Modes

#### 1. `visible` (Default and Recommended)

This is the standard best practice for Power BI development.
- **The `CentralDateTable` is visible** in the Fields pane.
- **No `variation` blocks are created**.
- Report developers can build measures and slice data by dragging in columns from the visible `CentralDateTable`.

#### 2. `hidden`

This mode prioritizes the convenience of the `variation` shortcut at the cost of model flexibility.
- **The `CentralDateTable` is hidden** and uses the `showAsVariationsOnly` property.
- A **`variation` block is added** to the primary date column of the primary fact table.
- This allows the auto-expanding hierarchy to work on that one column, but the `CentralDateTable` itself cannot be used for general analysis. 