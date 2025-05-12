# Generators Documentation

## Overview
The generators package contains classes responsible for generating the Power BI TMDL file structure and templates. It consists of two main components:

1. `StructureGenerator`: Creates the directory structure for TMDL files
2. `TemplateGenerator`: Generates TMDL template files using configuration mappings

## StructureGenerator

### Purpose
Creates a standardized directory structure for TMDL files based on the input file name.

### Directory Structure
```
output/
└── {input_file_name}/
    ├── extracted/           # Intermediate JSON files
    └── pbit/               # Generated TMDL files
        ├── Model/
        │   ├── cultures/
        │   ├── relationships/
        │   └── tables/
        └── Report/
            └── sections/
```

### Key Methods
- `create_directory_structure()`: Creates all required directories
- `get_output_path()`: Resolves the output path for a given file

## TemplateGenerator

### Purpose
Generates TMDL files by applying configuration mappings to extracted data.

### Supported Templates
1. Database Template
   - Location: `pbit/Model/database.tmdl`
   - Contains database connection information

### Configuration
Templates use the mappings defined in `twb-to-pbi.yaml`:
- Source XPath expressions for data extraction
- Attribute mappings for field conversion
- Default values and fallbacks

### Key Methods
- `generate_database_template()`: Creates the database.tmdl file
- `_resolve_output_path()`: Determines output location for generated files
- `_render_template()`: Applies data to Handlebars templates
