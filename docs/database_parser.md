# Database Parser Documentation

## Overview
The `DatabaseParser` class is responsible for extracting database information from Tableau Workbook (TWB) files. It uses XML parsing and configuration mappings to convert Tableau database configurations into Power BI compatible formats.

## Configuration
The parser uses the `PowerBiDatabase` mapping from `twb-to-pbi.yaml`:

```yaml
PowerBiDatabase:
  source_xpath: //workbook
  name:
    source_xpath: .//datasources/datasource/@caption
    alternative_xpath: .//datasources/datasource/@name
    default: Model
```

## Features

### Database Name Resolution
The parser extracts the database name in the following order:
1. Using `source_xpath` to find datasource caption
2. Using `alternative_xpath` to find datasource name
3. Falling back to the default value ('Model')

### XML Parsing
- Handles both element and attribute selection
- Supports relative and absolute XPath expressions
- Manages XML namespaces automatically

## Usage

```python
from src.parsers.database_parser import DatabaseParser

# Initialize parser with TWB file and config
parser = DatabaseParser(twb_path, config)

# Extract database info
database = parser.extract_database_info()
print(f"Database name: {database.name}")
```

## Methods

### `__init__(twb_path: Path, config: Dict[str, Any])`
Initializes the parser with:
- `twb_path`: Path to the Tableau Workbook file
- `config`: Configuration dictionary from twb-to-pbi.yaml

### `_find_elements(xpath: str) -> List[ET.Element]`
Internal method to find XML elements:
- Handles both absolute and relative XPath expressions
- Automatically prepends '.' to absolute paths
- Uses configured namespaces

### `extract_database_info() -> PowerBiDatabase`
Main method to extract database information:
- Uses configured XPath expressions
- Follows the name resolution order
- Returns a PowerBiDatabase object

## Return Types

### PowerBiDatabase
```python
@dataclass
class PowerBiDatabase:
    name: str  # Name of the database
```
