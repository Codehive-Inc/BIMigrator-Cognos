"""Parser for extracting database information from Tableau Workbook (.twb) files.

This module provides functionality to parse Tableau Workbook (.twb) files and extract
database information needed to generate Power BI TMDL files. The main components are:

Classes:
    - DatabaseParser: Main parser class that handles database information extraction

Usage:
    parser = DatabaseParser('path/to/workbook.twb', config)
    database = parser.extract_database_info()

The parser extracts the following information:
    - Database name from:
        1. Datasource caption (<datasource caption='...'>) 
        2. Datasource name (<datasource name='...'>) if no caption
        3. Dashboard name (<dashboard name='...'>) if no names found
        4. Default to 'Model' if no names found
"""
import xml.etree.ElementTree as ET
from typing import Dict, Any, Any, Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.dataclasses import PowerBiDatabase

class DatabaseParser:
    """Parser for Tableau Workbook (.twb) files."""
    
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        """Initialize parser with TWB file path and config."""
        self.tree = ET.parse(twb_path)
        self.root = self.tree.getroot()
        self.namespaces = {'': self.root.tag.split('}')[0].strip('{')} if '}' in self.root.tag else {}
        self.twb_file = twb_path
        self.config = config
    
    def extract_database_info(self) -> PowerBiDatabase:
        """Extract database connection information from the TWB file.
        
        The method tries to find a suitable database name in the following order:
        1. Caption attribute of the first <datasource> element
        2. Name attribute of the first <datasource> element if no caption
        3. Name attribute of the first <dashboard> element if no datasource name
        4. Default to 'Model' if no names found
        
        Returns:
            PowerBiDatabase: Database configuration with extracted name
        """
        # Find datasource using xpath
        name = None
        datasources = self.root.findall('.//datasource')
        
        # Try to get caption from first datasource
        if datasources:
            datasource = datasources[0]
            name = datasource.get('caption')
            
            # If no caption, try name
            if not name:
                name = datasource.get('name')
        
        # If still no name, try dashboard name
        if not name:
            dashboards = self.root.findall('.//dashboard')
            if dashboards:
                dashboard = dashboards[0]
                name = dashboard.get('name')
        
        # Use default if still no name
        if not name:
            name = 'Model'

        return PowerBiDatabase(
            name=name
        )

    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all required information from TWB file.
        
        Returns:
            Dictionary containing all extracted information organized by template type
        """
        return {
            'PowerBiDatabase': self.extract_database_info()
        }


def parse_workbook(twb_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a Tableau Workbook file and extract all required information.
    
    Args:
        twb_path: Path to .twb file
        config: Configuration dictionary from YAML
    
    Returns:
        Dictionary containing all extracted information organized by template type
    """
    parser = TableauWorkbookParser(twb_path, config)
    return parser.extract_all()


def main():
    """Command line interface for TWB parser."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Extract information from Tableau Workbook files')
    parser.add_argument('twb_file', help='Path to .twb file')
    parser.add_argument('--output', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Parse workbook
    data = parse_workbook(args.twb_file)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
