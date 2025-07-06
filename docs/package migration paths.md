# Cognos Package XML Extraction Paths

This document outlines the key elements to extract from Cognos FM Model XML files and their XPath locations. These elements are used during the migration process to create Power BI data models.

## Key Elements and Extraction Paths
### 1. Package Name (from Project Name)

- **Element**: `<project><name>`
- **Path**: `./bmt:name` (relative to the root `<project>`)
- **Extraction Code**: 
  ```python
  package_name_elem = root.find('./bmt:name', ns)
  package_name = package_name_elem.text if package_name_elem is not None else 'Unknown Package'
  ```

### 2. Physical Data Source Connection

- **Element**: `<dataSources><dataSource>` (There can be multiple, but typically one primary one for a package).
- **Path**: `./bmt:dataSources/bmt:dataSource`
- **Inside `<dataSource>`**:
  - **CM Data Source Name**: `<cmDataSource>`
    - **Path**: `./bmt:cmDataSource` (relative to `<dataSource>`)
  - **Schema Name**: `<schema>`
    - **Path**: `./bmt:schema` (relative to `<dataSource>`)
- **Extraction**: Find the `<dataSource>` element(s) and extract the text from `<cmDataSource>` and `<schema>`. This maps to the `cognos_connection_name` and helps you link to your `connection_mappings` JSON section.

### 3. Namespaces (Layers)

- **Element**: `<namespace>`
- **Paths**:
  - **Root Namespace** (often the package name implicitly): `./bmt:namespace`
  - **"Database Layer" Namespace**: `./bmt:namespace/bmt:namespace[bmt:name='Database Layer']`
  - **"Presentation Layer" Namespace**: `./bmt:namespace/bmt:namespace[bmt:name='Presentation Layer']`
- **Extraction**: Identify these namespaces to iterate through their contents separately.

### 4. Query Subjects (Tables/Views)

- **Element**: `<querySubject>`
- **Paths** (relative to the relevant Namespace element - Database or Presentation):
  - **All Query Subjects**: `./bmt:querySubject`
- **Inside `<querySubject>`**:
  - **Query Subject Name**: `<name>`
    - **Path**: `./bmt:name` (relative to `<querySubject>`)
  - **Query Subject Status**: `@status` (attribute)
    - **Path**: `. ` (get attribute status)
  - **For Database Layer QS Definition**: `<definition><dbQuery>`
    - **Path**: `./bmt:definition/bmt:dbQuery` (relative to `<querySubject>`)
    - **Source SQL**: `<sql type="cognos">`
      - **Path**: `./bmt:sql` (relative to `<dbQuery>`)
    - **Table Type**: `<tableType>`
      - **Path**: `./bmt:tableType` (relative to `<dbQuery>`)
    - **Source Data Source Ref**: `<sources><dataSourceRef>`
      - **Path**: `./bmt:sources/bmt:dataSourceRef` (relative to `<dbQuery>`)
  - **For Presentation Layer QS Definition**: `<definition><modelQuery>`
    - **Path**: `./bmt:definition/bmt:modelQuery` (relative to `<querySubject>`)
    - **Model Query SQL**: `<sql type="cognos">`
      - **Path**: `./bmt:sql` (relative to `<modelQuery>`)
- **Extraction**: Iterate through query subjects in the Database and Presentation layers. Extract name and definition details. Use the definition (especially `dbQuery` for Database Layer) to identify the physical source table/view (`physical_schema`, `physical_table`, `source_type`).

### 5. Query Items (Columns/Fields)

- **Element**: `<queryItem>`
- **Path** (relative to its parent `<querySubject>`): `./bmt:queryItem`
- **Inside `<queryItem>`**:
  - **Query Item Name**: `<name>`
    - **Path**: `./bmt:name` (relative to `<queryItem>`)
  - **Query Item External Name**: `<externalName>` (Often the physical column name)
    - **Path**: `./bmt:externalName` (relative to `<queryItem>`)
  - **Query Item Expression**: `<expression>`
    - **Path**: `./bmt:expression` (relative to `<queryItem>`)
  - **Query Item Usage**: `<usage>`
    - **Path**: `./bmt:usage` (relative to `<queryItem>`)
  - **Query Item Datatype**: `<datatype>`
    - **Path**: `./bmt:datatype` (relative to `<queryItem>`)
  - **Query Item Regular Aggregate**: `<regularAggregate>`
    - **Path**: `./bmt:regularAggregate` (relative to `<queryItem>`) (Check if exists)
  - **Query Item Nullable**: `<nullable>`
    - **Path**: `./bmt:nullable` (relative to `<queryItem>`) (Check if exists)
- **Extraction**: Iterate through query items within each relevant query subject. Extract name, usage, datatype, aggregate, nullability, and expression. Analyze the expression to classify as source column reference or calculation.

### 6. Relationships

- **Element**: `<relationship>`
- **Paths** (relative to the relevant Namespace element - Database or Presentation): `./bmt:relationship`
- **Inside `<relationship>`**:
  - **Relationship Name**: `<name>`
    - **Path**: `./bmt:name` (relative to `<relationship>`)
  - **Relationship Expression (Join Condition)**: `<expression>`
    - **Path**: `./bmt:expression` (relative to `<relationship>`) (You'll need to parse this expression to find the joining `<refobj>`s).
  - **Left/Right Side**: `<left>`, `<right>`
    - **Paths**: `./bmt:left`, `./bmt:right` (relative to `<relationship>`)
  - **Inside `<left>` / `<right>`**:
    - **Referenced Query Subject**: `<refobj>`
      - **Path**: `./bmt:refobj` (relative to `<left>` / `<right>`) (Get text content, this is the Cognos QS name).
    - **Cardinality**: `<mincard>`, `<maxcard>`
      - **Paths**: `./bmt:mincard`, `./bmt:maxcard` (relative to `<left>` / `<right>`)
- **Extraction**: Iterate through relationships in the Database and Presentation layers. Extract name, expression, and left/right details (Query Subject names, cardinalities). Parse the expression to find the joining query items (`<refobj>` text content within the expression string).

### 7. Calculations (Model Level)

- **Identified by**: examining `<queryItem>` elements (Paths from #5) where the `<expression>` element's text is not simply a `<refobj>` to another item, but contains functions, operators, or literals.

### 8. Filters (Model Level)

- **Element**: `<filter>` (Often found within `<querySubject>` or `<namespace>`)
- **Path** (example, relative to a Query Subject): `./bmt:filter`
- **Inside `<filter>`**:
  - **Filter Name**: `<name>`
  - **Filter Expression**: `<expression>`

## Example Usage in Migration

When migrating a Cognos FM Model package, the system extracts these elements to build a structured representation of the data model. This is then transformed into the appropriate Power BI model structure.

### Command to Migrate an FM Model Package

```python
from cognos_migrator.migrations.module import migrate_module_with_explicit_session

result = migrate_module_with_explicit_session(
    module_id="./examples/packages/FM Models/Energy_Share.xml",
    output_path="./output/output_energy_share_test",
    cognos_url="http://your-cognos-server:9300/api/v1",
    session_key="CAM your-session-key"
)
```

### Enhanced M-Query Generation

During migration, the enhanced M-Query generator uses the extracted information to create optimized Power BI queries with:

1. Proper source references
2. Appropriate join conditions
3. Calculated columns and measures
4. Filter conditions
5. Documentation comments
