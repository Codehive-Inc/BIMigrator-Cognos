# Cognos Report Specification Processing Flow

This document outlines the high-level process flow for how the BIMigrator-Cognos tool processes Cognos report specifications and transforms them into Power BI artifacts.

## 1. Entry Point

The migration process begins when a user initiates the migration of a Cognos report through the command-line interface:

```bash
python -m cognos_migrator.cli migrate-report --report-id <report_id>
```

This command triggers the `migrate_report` method in the `CognosMigrator` class (`cognos_migrator/migrator.py`), which orchestrates the entire migration process.

## 2. Report Extraction

### 2.1 API Connection
- The `CognosClient` (`cognos_migrator/client.py`) connects to the Cognos Analytics REST API using the configured credentials
- The client authenticates and establishes a session with the Cognos server

### 2.2 Report Retrieval
- The `get_report` method (`cognos_migrator/client.py`) fetches the report by its ID
- This retrieves basic report metadata, including name and ID

### 2.3 Specification Extraction
- The `get_report_specification` method (`cognos_migrator/client.py`) retrieves the complete XML specification of the report
- This XML contains all report elements, including layouts, data items, queries, and expressions

### 2.4 Data Source Extraction
- The `get_report_data_sources` method (`cognos_migrator/client.py`) identifies all data sources used by the report
- This includes database connections, query subjects, and data modules

### 2.5 Saving Extracted Data
- The `_save_extracted_data` method (`cognos_migrator/migrator.py`) saves the raw extracted data to the output directory:
  - `report_specification.xml`: The complete XML specification
  - `report_metadata.json`: Metadata about the report from the API
  - `report_details.json`: Basic report details (ID, name, path, type)
  - `cognos_report.json`: Serialized CognosReport object (internal representation)

## 3. Report Parsing

### 3.1 XML Parsing
- The `CognosReportSpecificationParser` (`cognos_migrator/report_parser.py`) parses the XML specification using ElementTree
- The parser creates a structured representation of the report
- Intermediate file: `parsed_structure.json` - Contains the parsed report structure before conversion

### 3.2 Page Extraction
- The `_extract_pages_from_xml` method (`cognos_migrator/report_parser.py`) identifies all report pages/layouts
- Each page is converted to a `ReportPage` object
- Intermediate file: `report_pages.json` - Contains the extracted pages and their properties

### 3.3 Visual Element Extraction
- The `_extract_visuals_from_xml_layout` method (`cognos_migrator/report_parser.py`) identifies all visual elements (tables, charts, etc.)
- Each visual is converted to a `CognosVisual` object
- Intermediate file: `report_visuals.json` - Contains all visual elements with their properties and positions

### 3.4 Data Item Extraction
- The `_extract_fields_from_xml` method (`cognos_migrator/report_parser.py`) identifies all data items and query items
- Each data item is parsed to extract:
  - Name and display name
  - Data type and format
  - Source table/query
  - Aggregation method
  - Expression/formula
- Intermediate file: `data_items.json` - Contains all extracted data items and their properties

### 3.5 Parameter Extraction
- The `_extract_parameters_from_xml` method (`cognos_migrator/report_parser.py`) identifies all report parameters
- Parameter definitions, default values, and prompt texts are extracted
- Intermediate file: `report_parameters.json` - Contains all extracted parameters and their properties

### 3.6 Structure Creation
- All extracted elements are assembled into a `CognosReportStructure` object (`cognos_migrator/report_parser.py`)
- This represents the complete logical structure of the Cognos report
- Intermediate file: `report_structure.json` - Contains the complete structured representation of the report

## 4. Data Model Generation

### 4.1 Table Creation
- The `_create_data_model` method (`cognos_migrator/migrator.py`) creates a Power BI data model
- Tables are created based on data sources identified in the report
- Intermediate file: `tables_definition.json` - Contains the initial table definitions

### 4.2 Column Creation
- Columns are created based on data items found in the report
- Data types, formats, and descriptions are preserved
- Intermediate file: `columns_definition.json` - Contains all column definitions with their properties

### 4.3 Measure Creation
- Measures are created based on calculated items in the report
- Cognos expressions are converted to DAX expressions
- Intermediate file: `measures_definition.json` - Contains all measure definitions with their DAX expressions

### 4.4 Relationship Creation
- Relationships between tables are identified based on the report structure
- These are converted to Power BI table relationships
- Intermediate file: `relationships_definition.json` - Contains all relationship definitions

### 4.5 CPF Enhancement (Optional)
- If a Cognos Framework Manager (CPF) file is provided:
  - Additional metadata is extracted from the CPF file by `CPFExtractor` (`cognos_migrator/cpf_extractor.py`)
  - The data model is enhanced with descriptions, hierarchies, and relationships
  - Intermediate file: `cpf_metadata.json` - Contains metadata extracted from the CPF file
  - Intermediate file: `enhanced_model.json` - Contains the data model after CPF enhancement

## 5. M-Query Generation

### 5.1 Context Extraction
- The `_extract_relevant_report_spec` method (`cognos_migrator/generators/generators.py`) extracts parts of the XML specification relevant to each table
- This provides context for generating accurate M-queries
- Intermediate file: `table_context_{table_name}.json` - Contains extracted context for each table

### 5.2 LLM-Based Generation
- If LLM service is enabled:
  - The extracted context is sent to the LLM service via `LLMServiceClient` (`cognos_migrator/llm_service.py`)
  - The LLM generates M-queries based on the Cognos report specification
  - The generated queries are validated and cleaned
  - Intermediate file: `llm_requests_{table_name}.json` - Contains the requests sent to the LLM service
  - Intermediate file: `llm_responses_{table_name}.json` - Contains the raw responses from the LLM service

### 5.3 Fallback Generation
- If LLM service is disabled or fails:
  - Basic M-queries are generated using templates by `_generate_basic_m_query` (`cognos_migrator/generators/generators.py`)
  - These connect to the same data sources as the original report
  - Intermediate file: `fallback_queries.json` - Contains the fallback M-queries generated

### 5.4 Query Formatting
- All generated M-queries are formatted according to Power BI standards by `_format_m_query` (`cognos_migrator/generators/generators.py`)
- Comments and documentation are added to explain the query structure
- Intermediate file: `formatted_queries.json` - Contains all formatted M-queries ready for inclusion in the Power BI project

## 6. Power BI Project Generation

### 6.1 Directory Structure Creation
- The `PowerBIProjectGenerator` (`cognos_migrator/generators/generators.py`) creates the directory structure for the Power BI project
- This follows the TMDL (Tabular Model Definition Language) format
- Intermediate file: `project_structure.json` - Contains the planned directory structure

### 6.2 Model Files Generation
- The data model is written to TMDL files by `_generate_model_files` (`cognos_migrator/generators/generators.py`):
  - `database.tmdl`: Database definition (generated by `_generate_database_file`)
  - `model.tmdl`: Model definition (generated by `_generate_model_file`)
  - Table files: One file per table with columns and M-query (generated by `_generate_table_files`)
  - `relationships.tmdl`: Table relationships (generated by `_generate_relationships_file`)
  - `expressions.tmdl`: DAX measures and calculated columns (generated by `_generate_expressions_file`)
- Intermediate file: `model_files_manifest.json` - Contains a list of all generated model files

### 6.3 Report Files Generation
- The report visuals are written to report files by `_generate_report_files` (`cognos_migrator/generators/generators.py`):
  - `report.json`: Report definition
  - `sections.json`: Report pages/sections
  - `visualContainers.json`: Visual elements
  - `filters.json`: Report and page filters
- Intermediate file: `report_files_manifest.json` - Contains a list of all generated report files

### 6.4 PBIT File Generation
- All generated files are packaged into a Power BI Template (.pbit) file by `_package_pbit_file` (`cognos_migrator/generators/generators.py`)
- This file can be opened directly in Power BI Desktop
- Intermediate file: `pbit_manifest.json` - Contains the manifest of all files included in the PBIT package

## 7. Documentation Generation

### 7.1 Migration Report
- A migration report is generated by `_generate_migration_report` (`cognos_migrator/migrator.py`) documenting:
  - Original Cognos report structure
  - Generated Power BI artifacts
  - Any warnings or issues encountered
- Output file: `migration_report.md` - Contains the complete migration report in markdown format
- Output file: `migration_report.html` - Contains the migration report in HTML format (if HTML output is enabled)

### 7.2 Technical Documentation
- Technical documentation is generated by `_generate_technical_documentation` (`cognos_migrator/generators/documentation.py`) for the migrated report:
  - Data model diagram
  - Table and column listings
  - M-query documentation
  - DAX expression documentation
- Output file: `technical_documentation.md` - Contains the technical documentation in markdown format
- Output file: `data_model_diagram.svg` - Visual representation of the data model

## 8. Output Organization

### 8.1 Extracted Folder
- Contains the raw extracted data from Cognos:
  - `report_specification.xml` - The complete XML specification
  - `report_metadata.json` - Metadata about the report from the API
  - `report_details.json` - Basic report details (ID, name, path, type)
  - `cognos_report.json` - Serialized CognosReport object
  - Detailed intermediate JSON files for investigation:
    - `report_queries.json` - All queries with their items and filters
    - `report_data_items.json` - All data items/columns with expressions and formats
    - `report_expressions.json` - All expressions with their parent context
    - `report_parameters.json` - All parameters with their properties
    - `report_filters.json` - All filters with their expressions
    - `report_layout.json` - Layout information including pages and visuals

### 8.2 Model Folder
- Contains the Power BI data model files in TMDL format:
  - `database.tmdl` - Database definition
  - `model.tmdl` - Model definition
  - `tables/` - Directory containing table definitions
  - `relationships.tmdl` - Table relationships
  - `expressions.tmdl` - DAX measures and calculated columns

### 8.3 Report Folder
- Contains the Power BI report definition files:
  - `report.json` - Report definition
  - `sections.json` - Report pages/sections
  - `visualContainers.json` - Visual elements
  - `filters.json` - Report and page filters
  - `config.json` - Report configuration

### 8.4 PBIT File
- The complete Power BI Template file ready for use
- File: `<report_name>.pbit` - Can be opened directly in Power BI Desktop

### 8.5 Documentation
- Migration report and technical documentation:
  - `migration_report.md/.html` - Migration process summary
  - `technical_documentation.md` - Technical details of the migrated report
  - `data_model_diagram.svg` - Visual representation of the data model
  - `column_mappings.csv` - Mapping between Cognos and Power BI columns

This process flow ensures that all aspects of the Cognos report are properly extracted, transformed, and used to create an equivalent Power BI project with tables, columns, measures, and visuals. The intermediate JSON files provide transparency and debugging capabilities throughout the migration process.
