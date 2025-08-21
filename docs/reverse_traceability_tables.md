# Reverse Traceability: PBIT Content → Extracted Files

Simple 3-column mapping from PBIT content to extracted files.

## Direct Content Mapping

| PBIT Content | Specific Element/Content | Extracted File |
|--------------|-------------------------|----------------|
| **Model Files** | | |
| `Model/database.tmdl` | Connection strings, data source config | `database.json` |
| `Model/model.tmdl` | Table references, model metadata | `model.json` |
| `Model/relationships.tmdl` | Relationship definitions, cardinality | `relationships.json`, `sql_relationships.json` |
| `Model/cultures/en-US.tmdl` | Culture settings, date formats | `culture.json` |
| **Table Files** | | |
| `Model/tables/ITEM_SITE_EXTRACT.tmdl` | Columns, data types, M-Query | `table_ITEM_SITE_EXTRACT.json` |
| `Model/tables/MANUFACTURER.tmdl` | Columns, data types, M-Query | `table_MANUFACTURER.json` |
| `Model/tables/MATERIAL_CHARGES.tmdl` | Columns, data types, M-Query | `table_MATERIAL_CHARGES.json` |
| `Model/tables/PURCHASE_ORDER_LINE.tmdl` | Columns, data types, M-Query | `table_PURCHASE_ORDER_LINE.json` |
| `Model/tables/PURCHASE_ORDER_RECEIPT.tmdl` | Columns, data types, M-Query | `table_PURCHASE_ORDER_RECEIPT.json` |
| `Model/tables/STORAGE_LOCATION.tmdl` | Columns, data types, M-Query | `table_STORAGE_LOCATION.json` |
| `Model/tables/PURCHASE_ORDER_DESCRIPTIONS.tmdl` | Columns, data types, M-Query | `table_PURCHASE_ORDER_DESCRIPTIONS.json` |
| `Model/tables/CentralDateTable.tmdl` | Date columns, hierarchies | `table_CentralDateTable.json` |
| **Dimension Tables** | | |
| `Model/tables/Dim_ITEM_SITE_EXTRACT_MANUFACTURER.tmdl` | Join columns, merged data | `table_Dim_ITEM_SITE_EXTRACT_MANUFACTURER.json` |
| `Model/tables/Dim_ITEM_SITE_EXTRACT_MATERIAL_CHARGES.tmdl` | Join columns, merged data | `table_Dim_ITEM_SITE_EXTRACT_MATERIAL_CHARGES.json` |
| `Model/tables/Dim_PURCHASE_ORDER_LINE_MATERIAL_CHARGES.tmdl` | Join columns, merged data | `table_Dim_PURCHASE_ORDER_LINE_MATERIAL_CHARGES.json` |
| **Report Files** | | |
| `Report/report.json` | Report metadata, resource packages | `report.json`, `report_metadata.json` |
| `Report/config.json` | Report configuration settings | `report_config.json` |
| `ReportMetadata.json` | Report name, author, created date | `report_metadata.json` |
| `ReportSettings.json` | Report display settings | `report_settings.json` |
| `DiagramLayout.json` | Model diagram positions | `layout.json` |
| **Report Sections** | | |
| `Report/sections/000_*/section.json` | Page layout, visual positions | `section_0.json` |
| `Report/sections/000_*/config.json` | Page configuration | `section_0.json` |
| `Report/sections/000_*/filters.json` | Page-level filters | `filters.json` |
| **Visual Containers** | | |
| `Report/sections/*/visualContainers/*/visualContainer.json` | Visual type, properties | `report_data_items.json` |
| `Report/sections/*/visualContainers/*/query.json` | DAX queries, column bindings | `report_queries.json` |
| `Report/sections/*/visualContainers/*/dataTransforms.json` | Data transformations, aggregations | `report_data_items.json` |
| `Report/sections/*/visualContainers/*/filters.json` | Visual-specific filters | `filters.json` |
| `Report/sections/*/visualContainers/*/config.json` | Visual configuration | Generated from templates |
| **Column-Level Content** | | |
| `column 'SITE_NUMBER'` in table TMDL | Column name, data type, source | `table_*.json` → `columns[].source_name` |
| `sourceColumn: SITE_NUMBER` in table TMDL | Source column mapping | `table_*.json` → `columns[].source_column` |
| `dataType: string` in table TMDL | Data type definition | `table_*.json` → `columns[].datatype` |
| **M-Query Content** | | |
| M-Query expressions in table TMDL | SQL source, transformations | `table_*.json` → `m_query` property |
| Table source connections | Data source connections | `database.json` |
| **Calculated Content** | | |
| `measure 'Total Amount'` in table TMDL | DAX measure expressions | `calculations.json` → `calculations[].DAXExpression` |
| Calculated columns in table TMDL | DAX column formulas | `calculations.json` → `calculations[].FormulaDax` |
| **Relationship Content** | | |
| `fromColumn: Table1.Column1` | Relationship from column | `sql_relationships.json` → `from_column` |
| `toColumn: Table2.Column2` | Relationship to column | `sql_relationships.json` → `to_column` |
| `manyToOne: true` | Relationship cardinality | `sql_relationships.json` → `cardinality` |
| **Slicer Content** | | |
| Slicer visual containers | Slicer configuration, data bindings | `report_data_items.json` filtered by slicer items |
| Slicer data transforms | Column selections, filter logic | `report_data_items.json` → slicer-specific items |
