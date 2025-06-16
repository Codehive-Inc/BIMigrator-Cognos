# Report Parsing Process

## Overview

The report parsing process analyzes the Cognos report specification (XML) and extracts structured information about data items, calculations, filters, and visual elements.

## Process Flow

1. **Parse Report Specification XML**
   - Load XML using ElementTree or lxml
   - Extract report structure elements

2. **Extract Data Items**
   - Identify data items and their properties
   - Extract expressions and calculations
   - Map data types

3. **Extract Report Layout**
   - Identify pages and sections
   - Extract visual containers and their properties
   - Map visual types to Power BI equivalents

4. **Process Report Structure**
   - Create a structured representation of the report
   - Map Cognos concepts to Power BI concepts

## Key Components

### CognosReportSpecificationParser Class

The `CognosReportSpecificationParser` class in `report_parser.py` handles the parsing of Cognos report specifications:

```python
class CognosReportSpecificationParser:
    def __init__(self):
        # Initialize parser
        
    def parse_report_specification(self, xml_spec: str, metadata: Dict = None) -> CognosReportStructure:
        # Parse XML specification and return structured representation
        
    def _extract_data_items(self, root) -> List[Dict]:
        # Extract data items from XML
        
    def _extract_pages(self, root) -> List[Dict]:
        # Extract pages and their content
        
    def _extract_visuals(self, root) -> List[Dict]:
        # Extract visual elements
```

### Data Item Extraction

Data items are extracted from the report specification and include:

- Column references
- Calculations and expressions
- Formatting properties
- Data types

### Visual Element Extraction

Visual elements are extracted and mapped to Power BI equivalents:

- Tables and crosstabs
- Charts (bar, line, pie, etc.)
- Text blocks and images
- Filters and slicers

## Output Structure

The parsing process produces a structured `CognosReportStructure` object containing:

- Data items and their properties
- Report pages and their layout
- Visual elements and their configuration
- Relationships between data items and visuals

This structured representation is then used in the next steps of the migration process to generate the Power BI data model and report structure.
