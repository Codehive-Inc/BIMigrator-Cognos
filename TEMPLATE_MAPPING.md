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
{{#each entities}}
  {{key}} → LinguisticEntity.key
  {{binding}} → EntityBinding
{{/each}}
```
