# Cognos to Power BI Migration: Extraction to Output File Mapping

This document provides a comprehensive mapping of the migration process from Cognos source files through intermediate extracted files to final Power BI output files.

## Migration Types Overview

The migration system supports three main migration paths:

1. **Report Migration** (`report.py`) - Migrates individual Cognos reports
2. **Module Migration** (`module.py`) - Migrates Cognos modules (data models)  
3. **Package Migration** (`package.py`) - Migrates Framework Manager packages with optional reports

## File Structure Overview

```
output_directory/
├── extracted/           # Intermediate files from extraction
│   ├── *.json          # Structured data from Cognos sources
│   └── *.xml           # Formatted source XML files
└── pbit/               # Final Power BI Template files
    ├── Model/          # Data model TMDL files
    ├── Report/         # Report layout and config files
    └── *.json          # Project metadata files
```

## 1. Report Migration Flow

### Source: Cognos Report XML or Report ID

**Extractors Used:**
- `QueryExtractor` - Extracts report queries
- `DataItemExtractor` - Extracts data items and expressions
- `ParameterExtractor` - Extracts report parameters
- `FilterExtractor` - Extracts report filters
- `LayoutExtractor` - Extracts visual layout information

### Intermediate Files in `extracted/` folder:

| File | Content | Source Extractor |
|------|---------|------------------|
| `report_specification.xml` | Original report XML | Direct copy |
| `report_specification_formatted.xml` | Formatted report XML | XML formatter |
| `report_data_items.json` | Column references and expressions | `DataItemExtractor` |
| `report_queries.json` | Query definitions | `QueryExtractor` |
| `report_parameters.json` | Report parameters | `ParameterExtractor` |
| `report_filters.json` | Applied filters | `FilterExtractor` |
| `report_layout.json` | Visual layout structure | `LayoutExtractor` |
| `report_metadata.json` | Report metadata | Various extractors |
| `calculations.json` | DAX calculations for measures | `DataItemExtractor` + LLM |
| `table_*.json` | Table schema definitions | Table generators |
| `cognos_report.json` | Complete report structure | Consolidated extractor |
| `culture.json` | Localization settings | Configuration |
| `database.json` | Database connection info | Configuration |
| `model.json` | Data model definition | Model consolidator |

### Final Files in `pbit/` folder:

| File | Content | Generated From | Template Used |
|------|---------|----------------|---------------|
| `Model/database.tmdl` | Database configuration | `database.json` | `database.tmdl` |
| `Model/model.tmdl` | Model definition with table refs | `model.json` | `model.tmdl` |
| `Model/tables/*.tmdl` | Individual table definitions | `table_*.json` | `Table.tmdl` |
| `Model/cultures/en-US.tmdl` | Culture settings | `culture.json` | `culture.tmdl` |
| `Report/report.json` | Report configuration | `cognos_report.json` | `report.json` |
| `Report/config.json` | Report config | Report structure | `report.config.json` |
| `Report/sections/*/section.json` | Page definitions | `report_layout.json` | `report.section.json` |
| `Report/sections/*/config.json` | Page configuration | Layout data | Auto-generated |
| `Report/sections/*/filters.json` | Page filters | `report_filters.json` | Auto-generated |
| `ReportMetadata.json` | Report metadata | `report_metadata.json` | `report.metadata.json` |
| `ReportSettings.json` | Report settings | Configuration | Auto-generated |
| `DiagramLayout.json` | Model diagram layout | Auto-generated | `diagram.layout.json` |

## 2. Module Migration Flow

### Source: Cognos Module ID

**Extractors Used:**
- `ModuleDataItemExtractor` - Extracts module data items
- `ModuleExpressionExtractor` - Extracts module expressions
- `ModuleRelationshipExtractor` - Extracts relationships
- `ModuleCalculationExtractor` - Extracts calculations
- `ModuleHierarchyExtractor` - Extracts hierarchies

### Intermediate Files in `extracted/` folder:

| File | Content | Source Extractor |
|------|---------|------------------|
| `module_specification.xml` | Original module XML | Direct copy |
| `module_specification_formatted.xml` | Formatted module XML | XML formatter |
| `module_data_items.json` | Module data items | `ModuleDataItemExtractor` |
| `module_expressions.json` | Module expressions | `ModuleExpressionExtractor` |
| `module_relationships.json` | Module relationships | `ModuleRelationshipExtractor` |
| `module_calculations.json` | Module calculations | `ModuleCalculationExtractor` |
| `module_hierarchies.json` | Module hierarchies | `ModuleHierarchyExtractor` |
| `table_*.json` | Generated table schemas | Table generators |
| `calculations.json` | DAX calculations | LLM conversion |
| `culture.json` | Localization settings | Configuration |
| `database.json` | Database connection | Configuration |
| `model.json` | Complete data model | Model consolidator |

### Final Files in `pbit/` folder:

Similar to report migration but focused on data model files:
- `Model/` folder with TMDL files for tables, relationships, measures
- Basic report structure (single page)
- No complex report layouts or visuals

## 3. Package Migration Flow

### Source: Framework Manager Package XML (.xml)

**Extractors Used:**
- `PackageStructureExtractor` - Extracts package structure
- `PackageQuerySubjectExtractor` - Extracts query subjects (tables)
- `PackageRelationshipExtractor` - Extracts relationships
- `PackageCalculationExtractor` - Extracts calculations
- `PackageFilterExtractor` - Extracts filters
- `SQLRelationshipExtractor` - Extracts SQL-based relationships

### Intermediate Files in `extracted/` folder:

| File | Content | Source Extractor |
|------|---------|------------------|
| `package.xml` | Original package XML | Direct copy |
| `package_formatted.xml` | Formatted package XML | XML formatter |
| `package_info.json` | Package metadata | `PackageStructureExtractor` |
| `package_structure.json` | Package structure | `PackageStructureExtractor` |
| `query_subjects.json` | Table definitions | `PackageQuerySubjectExtractor` |
| `package_relationships.json` | Table relationships | `PackageRelationshipExtractor` |
| `package_calculations.json` | Package calculations | `PackageCalculationExtractor` |
| `package_filters.json` | Package filters | `PackageFilterExtractor` |
| `sql_relationships.json` | SQL relationships | `SQLRelationshipExtractor` |
| `table_*.json` | Individual table schemas | Table generators |
| `calculations.json` | DAX calculations | LLM conversion |
| `database.json` | Database config | Configuration |
| `model.json` | Complete data model | Model consolidator |

### Final Files in `pbit/` folder:

Package migrations create comprehensive data models:
- Complete `Model/` folder with all TMDL files
- `Model/relationships.tmdl` - All table relationships
- `Model/expressions.tmdl` - Global expressions
- Basic report structure
- Enhanced with M-Query generation for complex data sources

## 4. Shared Model Migration (Package + Reports)

### Source: Package XML + Report IDs/Files

This is the most complex migration combining package and report migrations.

### Process Flow:

1. **Intermediate Report Migrations** - Each report migrated individually to `intermediate_reports/` folder
2. **Table Analysis** - Required tables identified from all reports
3. **Package Extraction** - Package extracted with filtering for required tables only
4. **Model Consolidation** - Package model merged with report-specific columns
5. **Calculation Merging** - All calculations consolidated from intermediate reports
6. **Report Consolidation** - All report pages merged into final unified report

### Key Files:

```
output_directory/
├── intermediate_reports/    # Temporary individual report migrations
│   ├── report1/
│   ├── report2/
│   └── ...
├── extracted/              # Final consolidated extraction
│   ├── calculations.json   # Merged from all intermediate reports
│   ├── package_*.json     # Filtered package data
│   └── table_*.json       # Enhanced with report columns
└── pbit/                  # Final unified Power BI template
    ├── Model/             # Complete data model
    └── Report/            # All report pages consolidated
        └── sections/      # Pages from all source reports
```

## Key Transformation Points

### 1. Cognos Expressions → DAX Formulas
- **Source**: Cognos expressions in data items and calculations
- **Intermediate**: Raw expressions in JSON files
- **Final**: DAX formulas in TMDL calculated columns and measures
- **Converter**: LLM-powered DAX conversion service

### 2. Cognos Queries → M-Query
- **Source**: Cognos SQL and query expressions
- **Intermediate**: Query structures in JSON
- **Final**: M-Query expressions in table TMDL files
- **Converter**: M-Query converter (Package vs Module specific)

### 3. Layout Structure → Power BI Visuals
- **Source**: Cognos report layout XML
- **Intermediate**: Parsed layout JSON
- **Final**: Power BI visual containers in section JSON
- **Generator**: Visual container generator

### 4. Relationships → TMDL Relationships
- **Source**: Cognos joins and relationships
- **Intermediate**: Relationship JSON definitions
- **Final**: TMDL relationship definitions
- **Generator**: Relationship generator with cardinality detection

## Template System

The migration uses a Handlebars-based template system:

- **Templates Location**: `cognos_migrator/templates/`
- **Template Engine**: `TemplateEngine` class
- **Key Templates**:
  - `Table.tmdl` - Converts `table_*.json` to TMDL table definitions
  - `model.tmdl` - Creates model structure from `model.json`
  - `relationship.tmdl` - Creates relationships from relationship data
  - `report.json` - Creates report configuration
  - Various section and visual templates

## Configuration and Settings

Migration behavior is controlled by:

- **`settings.json`** - Global migration settings
- **Table Filtering** - Controls which tables are included
- **LLM Service** - Enables/disables DAX conversion
- **Template Directory** - Location of TMDL templates

This mapping ensures traceability from any Cognos source element through the extraction and generation process to the final Power BI output file.
