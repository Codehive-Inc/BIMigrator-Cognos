# Parser Documentation

## Overview
The parser module implements a modular architecture for extracting information from Tableau Workbook (TWB) files. It consists of a base parser that provides common functionality and specialized parsers for specific data types.

## Architecture

### BaseParser
The foundation class that provides common XML parsing functionality:
- XML file loading and parsing
- XPath query execution
- Element and attribute extraction
- Configuration mapping handling
- Template method pattern for extensibility

### Specialized Parsers

#### DatabaseParser
Specializes in database information extraction:
- Inherits core functionality from BaseParser
- Focuses on database-specific parsing
- Implements database-specific mapping logic

#### Future Parsers
The architecture is designed to be extended with additional parsers:
- ModelParser (planned)
- TableParser (planned)
- VisualizationParser (planned)

## Configuration
All parsers use mappings from `twb-to-pbi.yaml`. Each mapping follows a standard structure:

```yaml
PowerBiComponent:
  source_xpath: //base_xpath  # Base XPath for the component
  field_name:                # Field to extract
    source_xpath: xpath      # Primary XPath
    alternative_xpath: xpath # Fallback XPath
    default: value          # Default value
```

### Example: Database Mapping
```yaml
PowerBiDatabase:
  source_xpath: //workbook
  name:
    source_xpath: .//datasources/datasource/@caption
    alternative_xpath: .//datasources/datasource/@name
    default: Model
```

## Key Features

### Template Method Pattern
- BaseParser defines the parsing workflow
- Specialized parsers implement specific extraction logic
- Consistent parsing behavior across all parsers

### Hierarchical Resolution
All parsers follow a standard resolution strategy:
1. Primary XPath query
2. Alternative XPath fallback
3. Default value if no match

### XML Parsing (via BaseParser)
- Element and attribute selection
- Relative and absolute XPath support
- Automatic namespace management
- Configurable mapping resolution

### Error Handling
- Graceful fallback mechanisms
- Clear error messages
- Default value support
- XML validation

## Usage

### BaseParser
```python
class CustomParser(BaseParser):
    def extract_info(self):
        mapping = self.config['CustomComponent']
        return self._get_mapping_value(mapping, None, 'default')
```

### DatabaseParser
```python
from src.parsers.database_parser import DatabaseParser

# Initialize parser
parser = DatabaseParser(twb_path, config)

# Extract database info
database = parser.extract_database_info()
print(f"Database name: {database.name}")
```

## Methods

### BaseParser

#### `__init__(twb_path: Path, config: Dict[str, Any])`
Initializes the base parser:
- Loads XML file
- Sets up configuration
- Initializes XML namespaces

#### `_get_mapping_value(mapping: Dict[str, Any], element: Optional[ET.Element], default: Any) -> Any`
Resolves values from configuration mappings:
- Handles primary and alternative XPaths
- Manages default values
- Supports attribute extraction

#### `_find_elements(xpath: str) -> List[ET.Element]`
Executes XPath queries:
- Handles relative/absolute paths
- Manages XML namespaces
- Returns matching elements

### DatabaseParser

#### `__init__(twb_path: Path, config: Dict[str, Any])`
Initializes the database parser:
- Calls BaseParser initialization
- Sets up database-specific configuration

#### `extract_database_info() -> PowerBiDatabase`
Extracts database information:
- Uses configuration mappings
- Returns PowerBiDatabase object

## Extension

### Adding New Parsers
1. Create a new parser class inheriting from BaseParser
2. Add component mappings to twb-to-pbi.yaml
3. Implement specific extraction methods
4. Utilize BaseParser's functionality

### Adding New Fields
1. Add field mappings to twb-to-pbi.yaml
2. Update relevant dataclass
3. Implement extraction in parser if needed

## Benefits
- Modular and maintainable code
- Consistent parsing behavior
- Easy to extend and modify
- Clear separation of concerns
- Reusable parsing logic
- Type safety through dataclasses

## Return Types

### PowerBiDatabase
```python
@dataclass
class PowerBiDatabase:
    name: str  # Name of the database
```

### Future Types
```python
@dataclass
class PowerBiModel:
    name: str
    tables: List[PowerBiTable]

@dataclass
class PowerBiTable:
    name: str
    columns: List[PowerBiColumn]
```
