Excellent idea. Going back to first principles is a great way to build a solid foundation.

Power Query's M language is incredibly powerful. Thinking of it as a series of data transformation steps, rather than a single block of code, is the key to understanding it. Each step takes a table as input and produces a new table as output.

Here is a comprehensive guide to the most common and useful M-query commands, complete with scenarios and full query examples.

---

### **M-Query Command Guide for Data Modelers**

#### **Category 1: Getting Data (The Foundation)**

These commands are the starting point for almost every query.

**1.1. `Sql.Database` - Get data from a SQL Server database.**
*   **Scenario:** You need to connect to a SQL Server to get your source tables.
*   **Full Query:**
    ```m
    let
        // Connects to the "AnalyticsDB" database on the "ProdSQL01" server
        Source = Sql.Database("ProdSQL01", "AnalyticsDB"),

        // Navigates to the "Products" table within the "dbo" schema
        dbo_Products = Source{[Schema="dbo",Item="Products"]}[Data]
    in
        dbo_Products
    ```

**1.2. `Value.NativeQuery` - Execute a specific SQL statement.**
*   **Scenario:** You need to execute a pre-written, complex SQL query directly against the source database for performance reasons or to use a specific database feature. This is the foundation of your current migration script.
*   **Full Query:**
    ```m
    let
        Source = Sql.Database("ProdSQL01", "AnalyticsDB"),

        // Defines a specific SQL query to be executed
        My_SQL_Query = "
            SELECT
                ProductID,
                ProductName,
                Category
            FROM
                dbo.Products
            WHERE
                IsActive = 1
        ",

        // Executes the query, enabling query folding for performance
        ExecutedQuery = Value.NativeQuery(Source, My_SQL_Query, null, [EnableFolding=true])
    in
        ExecutedQuery
    ```

**1.3. `Excel.Workbook` - Get data from an Excel file.**
*   **Scenario:** You need to import a mapping table or dimension that is maintained by business users in an Excel spreadsheet.
*   **Full Query:**
    ```m
    let
        // Gets the content from a file located on a shared drive
        Source = Excel.Workbook(File.Contents("\\SharedDrive\Mappings\RegionMapping.xlsx"), null, true),

        // Navigates to the sheet named "Sheet1" inside the workbook
        Sheet1_Sheet = Source{[Item="Sheet1",Kind="Sheet"]}[Data],

        // Promotes the first row of the sheet to be the column headers
        #"Promoted Headers" = Table.PromoteHeaders(Sheet1_Sheet, [PromoteAllScalars=true])
    in
        #"Promoted Headers"
    ```

---

#### **Category 2: Shaping Tables (Columns and Rows)**

These commands are the workhorses of data transformation.

**2.1. `Table.SelectColumns` - Keep only the columns you need.**
*   **Scenario:** Your source table has 50 columns, but your dimension only needs 5. This reduces model size and improves performance.
*   **Full Query:**
    ```m
    let
        Source = Your_Initial_Query_That_Returns_A_Table,

        // Selects only the three specified columns from the source table
        ChosenColumns = Table.SelectColumns(Source, {"ProductID", "ProductName", "StandardCost"})
    in
        ChosenColumns
    ```

**2.2. `Table.RemoveColumns` - Get rid of columns you don't need.**
*   **Scenario:** It's easier to specify the 3 columns you want to remove than the 47 you want to keep.
*   **Full Query:**
    ```m
    let
        Source = Your_Initial_Query_That_Returns_A_Table,

        // Removes only the three specified columns
        RemovedColumns = Table.RemoveColumns(Source, {"ModifiedDate", "AuditorID", "LegacySystemID"})
    in
        RemovedColumns
    ```

**2.3. `Table.SelectRows` - Filter rows based on a condition (The M equivalent of a `WHERE` clause).**
*   **Scenario:** You need to create a new dimension of only "Active" customers from your main customer table.
*   **Full Query:**
    ```m
    let
        Source = Your_Customer_Table_Query,

        // The 'each' keyword iterates through every row of the table
        // This keeps only the rows where the "Status" column equals "Active"
        FilteredRows = Table.SelectRows(Source, each [Status] = "Active")
    in
        FilteredRows
    ```

**2.4. `Table.AddColumn` - Create a new calculated column.**
*   **Scenario:** You need to create a `FullName` column by combining `FirstName` and `LastName`.
*   **Full Query:**
    ```m
    let
        Source = Your_Customer_Table_Query,

        // Adds a new column named "FullName"
        // The formula combines the FirstName and LastName columns with a space
        AddedFullName = Table.AddColumn(Source, "FullName", each [FirstName] & " " & [LastName], type text)
    in
        AddedFullName
    ```

**2.5. `Table.Distinct` - Remove duplicate rows.**
*   **Scenario:** Your source data has duplicates, and you need to create a clean dimension table with a unique key. This is a core part of the solution to your "duplicate values" error.
*   **Full Query:**
    ```m
    let
        SourceWithDuplicates = Your_Source_Query_With_Duplicate_Product_Info,

        // Returns a table containing only the unique rows based on the "ProductID" column
        UniqueProducts = Table.Distinct(SourceWithDuplicates, {"ProductID"})
    in
        UniqueProducts
    ```

---

#### **Category 3: Combining Tables**

These commands allow you to combine data from multiple queries.

**3.1. `Table.NestedJoin` (or `Table.Join`) - The M equivalent of a SQL `JOIN`.**
*   **Scenario:** You need to combine two tables during the query phase. **Warning:** This should be used sparingly in a Power BI model. It's usually better to load separate tables and relate them in the model view. This is useful for creating a "flat" table for a specific, non-model use case.
*   **Full Query:**
    ```m
    let
        Products = Your_Products_Query,
        Categories = Your_Categories_Query,

        // Performs a Left Outer Join, matching rows where Products[CategoryID] equals Categories[CategoryID]
        JoinedTables = Table.NestedJoin(Products, {"CategoryID"}, Categories, {"CategoryID"}, "CategoriesData", JoinKind.LeftOuter),

        // Expands the joined data to bring in the CategoryName column
        ExpandedCategoryName = Table.ExpandTableColumn(JoinedTables, "CategoriesData", {"CategoryName"}, {"CategoryName"})
    in
        ExpandedCategoryName
    ```

**3.2. `Table.Combine` - Stack tables on top of each other (The M equivalent of `UNION ALL`).**
*   **Scenario:** You have sales data from two different years in two separate tables (`Sales_2023`, `Sales_2024`) and you want to combine them into a single `All_Sales` table.
*   **Full Query:**
    ```m
    let
        Sales2023 = Your_Query_For_2023_Sales,
        Sales2024 = Your_Query_For_2024_Sales,

        // Appends the rows from both tables into a single table
        // Note: Both tables must have the same column names for this to work cleanly
        CombinedSales = Table.Combine({Sales2023, Sales2024})
    in
        CombinedSales
    ```

---

#### **Category 4: Grouping and Aggregating**

**4.1. `Table.Group` - The M equivalent of SQL's `GROUP BY`.**
*   **Scenario:** You need to calculate the total sales for each product category.
*   **Full Query:**
    ```m
    let
        SourceSales = Your_Sales_Table_Query,

        // Groups the data by the "Category" column
        // For each group, it creates a new column "TotalSales" by summing the "LineTotal" values
        GroupedData = Table.Group(SourceSales, {"Category"}, {
            {"TotalSales", each List.Sum([LineTotal]), type number},
            {"TransactionCount", each Table.RowCount(_), Int64.Type}
        })
    in
        GroupedData
    ```