# Documentation for `settings.json`

The `settings.json` file is a crucial configuration file that controls key aspects of the Cognos to Power BI migration process. It allows you to define global settings that affect how data models are generated, ensuring consistency and adherence to best practices across all migrations.

## How These Settings Enable Power BI Best Practices

Properly configuring this file is essential for a successful migration, as it directly influences the structure and efficiency of the final Power BI data model. Here’s how each setting helps you align with best practices:

-   **Enforces a Star Schema:** By using the `table_filtering` options, you can create a lean, report-specific data model that avoids the complexity of a monolithic, "one-size-fits-all" model. This encourages a **star schema** design, which is the gold standard for Power BI, as it improves performance, simplifies DAX calculations, and makes the model more intuitive for end-users.
-   **Promotes a Centralized Date Table:** The `date_table_mode` and `always_include` settings work together to ensure that your model includes a single, authoritative date dimension. This is a cornerstone of Power BI development that enables powerful time-intelligence calculations and consistent date-based filtering across all of your reports.
-   **Reduces Model Size and Complexity:** By filtering out unused tables, you significantly reduce the size of your Power BI model. This leads to faster data refreshes, quicker report rendering, and a more manageable dataset for developers and analysts.

## File Structure

The `settings.json` file has the following structure:

```json
{
  "date_table_mode": "visible",
  "table_filtering": {
    "mode": "direct",
    "always_include": [
      "CentralDateTable"
    ]
  }
}
```

### `date_table_mode`

This setting controls the behavior of the central date table that is automatically generated during the migration.

-   **`"visible"` (Default & Recommended):** When set to `visible`, a `CentralDateTable` is created and included in the final Power BI data model. This is the recommended setting for most scenarios, as it aligns with the Power BI best practice of having a single, dedicated date dimension for all time-based analysis.
-   **`"hidden"`:** If you do not want to include the central date table in the model, you can set this value to `hidden`. This is useful for specific cases where a date dimension is not required or is handled differently.

### `table_filtering`

This section governs how the migration tool filters tables from the Cognos Framework Manager package, which is especially important when migrating reports along with a package.

-   **`"mode"`:** This setting defines the filtering strategy.
    -   **`"direct"` (Recommended for report-centric migrations):** In this mode, the tool will only include tables in the final data model that are directly referenced by the reports being migrated. This creates a lean, optimized star schema that is tailored to the specific needs of your reports, which is a key Power BI best practice.
    -   **`"discover"`:** When set to `"discover"`, the tool will include not only the directly referenced tables but also any tables that are related to them in the Cognos package. This can be useful when you want to bring in a broader data context, but it may lead to a larger, more complex model.
    -   **`"include-all"`:** This mode disables table filtering and includes all tables from the Framework Manager package. This is useful for a full package migration where you intend to replicate the entire Cognos model in Power BI, but it may not result in an optimized model.

-   **`"always_include"`:** This is a list of table names that should always be included in the final data model, regardless of the filtering `mode`. This is the perfect place to specify tables that are essential for your data model but may not be directly referenced in every report.
    -   **`"CentralDateTable"`:** As shown in the example, it is a best practice to always include the `CentralDateTable` to ensure that your data model has a consistent and authoritative time dimension.

By properly configuring the `settings.json` file, you can ensure that your migrations are efficient, consistent, and produce well-structured Power BI data models that follow industry best practices. 