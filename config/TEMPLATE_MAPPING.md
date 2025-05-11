# Template to Configuration Mapping

This document shows how template files map to YAML configurations, dataclasses, and target output structure based on the Adventure Works DW 2020 example.

## Core Files

### Model Definition
- **Template**: `/templates/model.tmdl`
- **Target**: `Model/model.tmdl`
- **YAML Config**: `PowerBiModel`
- **Dataclass**: `PowerBiModel`
- **Purpose**: Root model configuration including culture, data access, query order, and table references

### Database Configuration
- **Template**: `/templates/database.tmdl`
- **Target**: `Model/database.tmdl`
- **YAML Config**: `PowerBiDatabase`
- **Dataclass**: `PowerBiDatabase`
- **Purpose**: Database connection settings

### DAX Expressions
- **Template**: `/templates/expressions.tmdl`
- **Target**: `Model/expressions.tmdl`
- **YAML Config**: `PowerBiExpressions`
- **Dataclass**: `PowerBiExpression`, `PowerBiExpressions`
- **Purpose**: DAX calculations and measures

## Data Objects

### Tables
- **Template**: `/templates/Table.tmdl`
- **Target**: `Model/tables/<table_name>.tmdl`
- **YAML Config**: `PowerBiTable`
- **Dataclass**: `PowerBiTable`, `PowerBiColumn`
- **Purpose**: Table definitions with columns, data types, and formatting

### Relationships
- **Template**: `/templates/relationship.tmdl`
- **Target**: `Model/relationships/<id>.tmdl`
- **YAML Config**: `PowerBiRelationship`
- **Dataclass**: `PowerBiRelationship`
- **Purpose**: Table relationships with cardinality and filtering behavior

### Culture Settings
- **Template**: `/templates/en-US.tmdl`
- **Target**: `Model/cultures/<culture_code>.tmdl`
- **YAML Config**: `PowerBiCulture`
- **Dataclass**: `CultureInfo`
- **Purpose**: Localization and linguistic metadata

## Report Files

### Report Configuration
- **Template**: `/templates/report.config.json`
- **Target**: `Report/config.json`
- **YAML Config**: `PowerBiReportConfig`
- **Dataclass**: `PowerBiReportConfig`
- **Purpose**: Theme settings, section index, and data source settings

### Report Metadata
- **Template**: `/templates/report.metadata.json`
- **Target**: `Report/metadata.json`
- **YAML Config**: `PowerBiReportMetadata`
- **Dataclass**: `PowerBiReportMetadata`
- **Purpose**: Report metadata including name, description, owner, and timestamps

### Report Settings
- **Template**: `/templates/report.settings.json`
- **Target**: `Report/settings.json`
- **YAML Config**: `PowerBiReportSettings`
- **Dataclass**: `PowerBiReportSettings`, `PowerBiVisualSettings`, `PowerBiFilterSettings`, `PowerBiInteractionSettings`
- **Purpose**: Visual, filter, and interaction settings

### Report Layout
- **Template**: `/templates/diagram.layout.json`
- **Target**: `Report/layout.json`
- **YAML Config**: `PowerBiDiagramLayout`
- **Dataclass**: `PowerBiDiagramLayout`, `PowerBiTableLayout`, `PowerBiTablePosition`
- **Purpose**: Table positions in diagram view

### Report Definition
- **Template**: `/templates/report.json`
- **Target**: `Report/report.json`
- **YAML Config**: `PowerBiReport`
- **Dataclass**: `PowerBiReport`, `PowerBiResourcePackage`, `PowerBiResourceItem`
- **Purpose**: Main report definition with resource packages

### Report Section
- **Template**: `/templates/report.section.json`
- **Target**: `Report/sections/<name>.json`
- **YAML Config**: `PowerBiReportSection`
- **Dataclass**: `PowerBiReportSection`
- **Purpose**: Report page/section with filters and visuals

## Example Output Structure

```
Model/
├── model.tmdl                      # Core model settings
├── database.tmdl                   # Database connection
├── expressions.tmdl                # DAX expressions
├── tables/
│   ├── Customer.tmdl              # Customer dimension
│   ├── Date.tmdl                  # Date dimension
│   ├── Product.tmdl               # Product dimension
│   ├── Sales.tmdl                 # Sales fact table
│   └── Sales Territory.tmdl       # Territory dimension
├── relationships/
│   ├── c4007daa.tmdl             # Sales -> Territory
│   ├── fe440ad4.tmdl             # Sales -> Product
│   └── 3921d624.tmdl             # Sales -> Customer
└── cultures/
    └── en-US.tmdl                # English culture settings

Report/
├── config.json                    # Report configuration
├── metadata.json                  # Report metadata
├── settings.json                  # Report settings
├── layout.json                    # Diagram layout
├── report.json                    # Main report definition
└── sections/                      # Report pages/sections
    ├── Overview.json
    ├── Sales Analysis.json
    └── Customer Details.json
```

## Template Variables

### model.tmdl
```
{{model_name}} → PowerBiModel.model_name
{{culture}} → PowerBiModel.culture
{{query_order}} → PowerBiModel.query_order
{{tables}} → PowerBiModel.tables
```

### database.tmdl
```
{{name}} → PowerBiDatabase.name
{{connection_string}} → PowerBiDatabase.connection_string
```

### expressions.tmdl
```
{{#each expressions}}
  {{name}} → PowerBiExpression.name
  {{expression}} → PowerBiExpression.expression
{{/each}}
```

### Table.tmdl
```
{{name}} → PowerBiTable.name
{{lineage_tag}} → PowerBiTable.lineage_tag
{{#each columns}}
  {{name}} → PowerBiColumn.name
  {{datatype}} → PowerBiColumn.datatype
  {{format_string}} → PowerBiColumn.format_string
{{/each}}
```

### relationship.tmdl
```
{{id}} → PowerBiRelationship.id
{{from_table}} → PowerBiRelationship.from_table
{{to_table}} → PowerBiRelationship.to_table
{{cross_filter_behavior}} → PowerBiRelationship.cross_filter_behavior
```

This document shows how template files map to YAML configurations, dataclasses, and target output structure.

## Model Definition

- **Template**: `/templates/model.tmdl`
- **Target**: `<output_dir>/Model/model.tmdl`
- **YAML Config**: `PowerBiModel` in `config/twb-to-pbi.yaml`
- **Dataclass**: `PowerBiModel` in `config/dataclasses.py`
- **Purpose**: Defines the root model configuration including culture, data access, and query order

## Tables

- **Template**: `/templates/Table.tmdl`
- **Target**: `<output_dir>/Model/tables/<table_name>.tmdl`
- **YAML Config**: `PowerBiTable` in `config/twb-to-pbi.yaml`
- **Dataclass**: `PowerBiTable` and `PowerBiColumn` in `config/dataclasses.py`
- **Purpose**: Defines table structure, columns, and their properties

## Relationships

- **Template**: `/templates/relationship.tmdl`
- **Target**: `<output_dir>/Model/relationships/<relationship_name>.tmdl`
- **YAML Config**: `PowerBiRelationship` in `config/twb-to-pbi.yaml`
- **Dataclass**: `PowerBiRelationship` in `config/dataclasses.py`
- **Purpose**: Defines relationships between tables including cardinality and filtering

## Culture

- **Template**: `/templates/en-US.tmdl`
- **Target**: `<output_dir>/Model/cultures/<culture_code>.tmdl`
- **YAML Config**: `PowerBiCulture` in `config/twb-to-pbi.yaml`
- **Dataclass**: `CultureInfo` and related classes in `config/dataclasses.py`
- **Purpose**: Defines linguistic metadata for localization

## Example Output Structure

```
<output_dir>/
└── Model/
    ├── model.tmdl                     # From model.tmdl template
    ├── tables/
    │   ├── Customer.tmdl             # From Table.tmdl template
    │   ├── Orders.tmdl              
    │   └── Products.tmdl
    ├── relationships/
    │   ├── Customer_Orders.tmdl      # From relationship.tmdl template
    │   └── Orders_Products.tmdl
    └── cultures/
        ├── en-US.tmdl               # From en-US.tmdl template
        └── es-ES.tmdl               # Same template, different culture

```

## Template Variables

### model.tmdl
```
{{model_name}} → PowerBiModel.model_name
{{culture}} → PowerBiModel.culture
{{query_order_list}} → PowerBiModel.query_order
```

### Table.tmdl
```
{{table_name}} → PowerBiTable.name
{{#each columns}}
  {{name}} → PowerBiColumn.name
  {{datatype}} → PowerBiColumn.datatype
  {{format_string}} → PowerBiColumn.format_string
{{/each}}
```

### relationship.tmdl
```
{{from_table}} → PowerBiRelationship.from_table
{{to_table}} → PowerBiRelationship.to_table
{{cross_filter_behavior}} → PowerBiRelationship.cross_filter_behavior
```

### en-US.tmdl
```
{{culture}} → CultureInfo.culture
{{linguistic_metadata}} → CultureInfo.linguistic_metadata
```

### report.config.json
```
{{version}} → PowerBiReportConfig.version
{{theme_name}} → PowerBiReportConfig.theme.name
{{theme_version}} → PowerBiReportConfig.theme.version
{{theme_type}} → PowerBiReportConfig.theme.type
{{active_section_index}} → PowerBiReportConfig.active_section_index
{{default_drill_filter}} → PowerBiReportConfig.default_drill_filter
{{is_cross_highlighting_disabled}} → PowerBiReportConfig.slow_data_source_settings.is_cross_highlighting_disabled
{{is_slicer_selections_enabled}} → PowerBiReportConfig.slow_data_source_settings.is_slicer_selections_enabled
{{is_filter_selections_enabled}} → PowerBiReportConfig.slow_data_source_settings.is_filter_selections_enabled
{{is_field_well_enabled}} → PowerBiReportConfig.slow_data_source_settings.is_field_well_enabled
{{is_apply_all_enabled}} → PowerBiReportConfig.slow_data_source_settings.is_apply_all_enabled
{{use_new_filter_pane}} → PowerBiReportConfig.settings.use_new_filter_pane
{{allow_change_filter_types}} → PowerBiReportConfig.settings.allow_change_filter_types
```

### report.metadata.json
```
{{version}} → PowerBiReportMetadata.version
{{created_date_time}} → PowerBiReportMetadata.metadata.created_date_time
{{modified_date_time}} → PowerBiReportMetadata.metadata.modified_date_time
{{created_by}} → PowerBiReportMetadata.metadata.created_by
{{modified_by}} → PowerBiReportMetadata.metadata.modified_by
{{name}} → PowerBiReportMetadata.metadata.name
{{description}} → PowerBiReportMetadata.metadata.description
{{owner}} → PowerBiReportMetadata.metadata.owner
{{created}} → PowerBiReportMetadata.metadata.created
{{modified}} → PowerBiReportMetadata.metadata.modified
{{#each custom_metadata}}
  {{key}} → PowerBiReportMetadata.metadata.custom_metadata[key]
  {{value}} → PowerBiReportMetadata.metadata.custom_metadata[value]
{{/each}}
{{#each tags}}
  {{this}} → PowerBiReportMetadata.metadata.tags[]
{{/each}}
```

### report.settings.json
```
{{version}} → PowerBiReportSettings.version
{{default_visual_style}} → PowerBiReportSettings.visual_settings.default_visual_style
{{show_data_labels}} → PowerBiReportSettings.visual_settings.show_data_labels
{{persistent_filters}} → PowerBiReportSettings.filter_settings.persistent_filters
{{filter_pane_enabled}} → PowerBiReportSettings.filter_settings.filter_pane_enabled
{{drill_enabled}} → PowerBiReportSettings.interaction_settings.drill_enabled
{{cross_filtering_enabled}} → PowerBiReportSettings.interaction_settings.cross_filtering_enabled
```

### diagram.layout.json
```
{{version}} → PowerBiDiagramLayout.version
{{#each tables}}
  {{id}} → PowerBiTableLayout.id
  {{x}} → PowerBiTableLayout.position.x
  {{y}} → PowerBiTableLayout.position.y
{{/each}}
```

### report.json
```
{{report_id}} → PowerBiReport.id
{{layout_optimization}} → PowerBiReport.layout_optimization
{{#each shared_resources}}
  {{name}} → PowerBiResourceItem.name
  {{path}} → PowerBiResourceItem.path
  {{type}} → PowerBiResourceItem.type
{{/each}}
```

### report.section.json
```
{{name}} → PowerBiReportSection.name
{{display_name}} → PowerBiReportSection.display_name
{{#each filters}}
  {{type}} → PowerBiReportSection.filters[].type
  {{table}} → PowerBiReportSection.filters[].target.table
  {{column}} → PowerBiReportSection.filters[].target.column
  {{value}} → PowerBiReportSection.filters[].value
{{/each}}
{{#each visuals}}
  {{id}} → PowerBiReportSection.config.objects.visuals[].id
  {{type}} → PowerBiReportSection.config.objects.visuals[].type
  {{properties}} → PowerBiReportSection.config.objects.visuals[].properties
{{/each}}
{{width}} → PowerBiReportSection.config.layout.width
{{height}} → PowerBiReportSection.config.layout.height
{{display_option}} → PowerBiReportSection.config.layout.display_option
```

### culture.tmdl
```
{{culture}} → CultureInfo.culture
{{linguistic_metadata}} → CultureInfo.linguistic_metadata
```

### relationship.tmdl
```
{{id}} → PowerBiRelationship.id
{{from_table}} → PowerBiRelationship.from_table
{{to_table}} → PowerBiRelationship.to_table
{{cross_filter_behavior}} → PowerBiRelationship.cross_filter_behavior
```
