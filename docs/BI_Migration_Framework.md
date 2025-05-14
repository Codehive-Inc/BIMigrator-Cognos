# BI Platform Migration Framework

## 1. Architecture Overview

### 1.1 Core Components
- **Parser Module**: Extracts information from source BI platform
- **Transformation Module**: Converts source objects to target format
- **Generator Module**: Creates target platform files
- **Formula Conversion Service**: Handles expression/formula translations

### 1.2 Project Structure
```
BIMigrator/
├── config/
│   ├── mappings/            # Platform-specific mapping rules
│   └── data_classes.py      # Data models for each platform
├── src/
│   ├── parsers/            # Source platform parsers
│   ├── generators/         # Target platform generators
│   ├── transformation/     # Conversion logic
│   └── common/            # Shared utilities
├── templates/             # Target platform templates
└── docs/                 # Documentation
```

## 2. Migration Components

### 2.1 Data Model Migration
1. **Data Sources**
   - Connection types (Live/DirectQuery, Import/Extract)
   - Authentication methods
   - Custom SQL queries
   - Connection strings

2. **Tables and Relationships**
   - Table definitions and schemas
   - Relationships and cardinality
   - Join types and cross-filtering
   - Partitioning and incremental refresh

3. **Fields and Calculations**
   - Dimensions and measures
   - Calculated fields/columns
   - Data types and formats
   - Aggregations and calculations

### 2.2 Report Migration
1. **Visual Elements**
   - Chart types and mappings
   - Visual properties and formatting
   - Axes and legends
   - Colors and themes

2. **Interactivity**
   - Filters and slicers
   - Actions and navigation
   - Drill-through and drill-down
   - Bookmarks and selections

3. **Layout and Structure**
   - Pages and sections
   - Container layouts
   - Size and positioning
   - Responsiveness

## 3. Implementation Guide

### 3.1 Adding New Source Platform
1. **Create Parser**
   ```python
   class NewPlatformParser(BaseParser):
       def extract_all(self) -> Dict[str, Any]:
           return {
               'datasources': self.extract_datasources(),
               'tables': self.extract_tables(),
               'calculations': self.extract_calculations(),
               'visuals': self.extract_visuals()
           }
   ```

2. **Define Mappings**
   ```yaml
   NewPlatformMappings:
     source_xpath: //base_xpath
     field_mappings:
       name:
         source_xpath: xpath
         alternative_xpath: fallback_xpath
         default: default_value
   ```

3. **Create Data Classes**
   ```python
   @dataclass
   class NewPlatformModel:
       name: str
       tables: List[Table]
       relationships: List[Relationship]
   ```

### 3.2 Adding New Target Platform
1. **Create Generator**
   ```python
   class NewPlatformGenerator(BaseTemplateGenerator):
       def generate_all(self, data: Dict[str, Any]) -> List[Path]:
           return [
               self.generate_model(data),
               self.generate_reports(data),
               self.generate_datasources(data)
           ]
   ```

2. **Create Templates**
   ```
   templates/
   ├── model.template
   ├── report.template
   └── datasource.template
   ```

3. **Define Output Structure**
   ```
   output/
   ├── Model/
   │   ├── tables/
   │   └── relationships/
   └── Report/
       └── pages/
   ```

## 4. Formula Conversion

### 4.1 Architecture
1. **FastAPI Service**
   - Handles complex formula translations
   - Uses AI for pattern matching
   - Maintains function mappings

2. **Conversion Process**
   ```python
   payload = {
       'source_formula': formula,
       'source_context': context,
       'target_platform': target
   }
   ```

### 4.2 Function Mappings
```json
{
  "functionMappings": [
    {
      "sourceFunction": "SUM",
      "targetFunction": "SUM",
      "confidence": "High"
    },
    {
      "sourceFunction": "LOOKUP",
      "targetFunction": "CALCULATE",
      "confidence": "Medium",
      "notes": "Context dependent"
    }
  ]
}
```

## 5. Best Practices

### 5.1 Development
1. **Modular Design**
   - Separate parsers per platform
   - Reusable transformation logic
   - Template-based generation

2. **Error Handling**
   - Graceful fallbacks
   - Clear error messages
   - Default values

3. **Testing**
   - Unit tests for components
   - Integration tests for flows
   - Sample workbooks

### 5.2 Migration Process
1. **Pre-Migration**
   - Source analysis
   - Compatibility check
   - Feature mapping

2. **Execution**
   - Iterative conversion
   - Validation steps
   - Error logging

3. **Post-Migration**
   - Quality assurance
   - Performance testing
   - Documentation

## 6. Configuration

### 6.1 Mapping Configuration
```yaml
Mappings:
  ObjectTypes:
    - source: "Workbook"
      target: "Report"
    - source: "Worksheet"
      target: "Page"
  VisualTypes:
    - source: "Bar"
      target: ["ClusteredBar", "StackedBar"]
  Properties:
    - source: "Color"
      target: "Fill"
```

### 6.2 Platform Settings
```yaml
PlatformConfig:
  source:
    type: "Tableau"
    version: "2021.4"
  target:
    type: "PowerBI"
    version: "3.0"
  features:
    formula_conversion: true
    visual_migration: true
    data_model: true
```

## 7. Extensibility

### 7.1 Adding New Features
1. Update data classes
2. Create/modify parsers
3. Update generators
4. Add mapping configurations
5. Update templates

### 7.2 Custom Extensions
1. **Custom Parsers**
   - Inherit from BaseParser
   - Implement extract methods
   - Add specific logic

2. **Custom Generators**
   - Inherit from BaseGenerator
   - Add template mappings
   - Implement generate methods

## 8. Troubleshooting

### 8.1 Common Issues
1. **Formula Conversion**
   - Complex calculations
   - Platform-specific functions
   - Context differences

2. **Visual Migration**
   - Unsupported chart types
   - Custom visuals
   - Layout differences

### 8.2 Resolution Steps
1. Check mapping configurations
2. Review error logs
3. Consult function mappings
4. Update templates
5. Modify transformation logic
