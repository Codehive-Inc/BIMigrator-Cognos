# Generators Documentation

## Overview
The generators package contains a modular architecture for generating Power BI TMDL files. It follows a hierarchical structure with base and specialized generators:

1. `BaseTemplateGenerator`: Core template rendering functionality
2. Specialized Generators:
   - `DatabaseTemplateGenerator`: Database TMDL files
   - `ModelTemplateGenerator`: Model and table TMDL files
3. `TemplateGenerator`: Main coordinator for all generators

## Directory Structure
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

## BaseTemplateGenerator

### Purpose
Provides core template functionality shared across all generators.

### Key Features
- Template loading and compilation
- File generation utilities
- Configuration management
- Path resolution

### Key Methods
- `render_template()`: Renders a template with context
- `generate_file()`: Generates a file from a template
- `_load_template_mappings()`: Loads template configuration

## Specialized Generators

### DatabaseTemplateGenerator

#### Purpose
Generates database-specific TMDL files.

#### Key Methods
- `generate_database_tmdl()`: Creates database.tmdl file

### ModelTemplateGenerator

#### Purpose
Generates model and table TMDL files.

#### Key Methods
- `generate_model_tmdl()`: Creates model.tmdl file

## TemplateGenerator

### Purpose
Coordinates the generation of all TMDL files using specialized generators.

### Key Features
- Manages specialized generators
- Handles high-level file generation
- Provides unified interface

### Key Methods
- `generate_all()`: Generates all TMDL files

## Configuration
All generators use mappings defined in `twb-to-pbi.yaml`:
- Template paths and output locations
- Source XPath expressions
- Attribute mappings
- Default values and fallbacks

## Usage Example
```python
# Initialize generator
generator = TemplateGenerator(config_path, input_path)

# Generate all files
generated_files = generator.generate_all(config_data, output_dir)
```
