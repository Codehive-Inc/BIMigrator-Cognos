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
from typing import Dict, Any, Optional, List
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
    
    def _find_elements(self, xpath: str) -> List[ET.Element]:
        """Find elements using xpath, handling both absolute and relative paths."""
        if xpath.startswith('//'):
            xpath = '.' + xpath
        return self.root.findall(xpath, self.namespaces)
    
    def extract_database_info(self) -> PowerBiDatabase:
        """Extract database connection information from the TWB file.
        
        Uses the PowerBiDatabase mapping from config to find the source elements.
        The database name is extracted in the following order:
        1. Using source_xpath from config to find datasource caption
        2. Using alternative_xpath from config to find datasource name
        3. Default to 'Model' if no name found
        
        Returns:
            PowerBiDatabase: Database configuration with extracted name
        """
        # Get PowerBiDatabase mapping from config
        mapping = self.config.get('PowerBiDatabase', {})
        name = None
        
        # Try source_xpath for caption first
        name_mapping = mapping.get('name', {})
        source_xpath = name_mapping.get('source_xpath')
        if source_xpath:
            # Remove attribute part for finding elements
            base_xpath = source_xpath.split('@')[0].rstrip('/')
            elements = self._find_elements(base_xpath)
            if elements:
                # Get attribute name from xpath
                attr = source_xpath.split('@')[-1]
                name = elements[0].get(attr)
        
        # Try alternative_xpath for name if no caption found
        if not name:
            alt_xpath = name_mapping.get('alternative_xpath')
            if alt_xpath:
                # Remove attribute part for finding elements
                base_xpath = alt_xpath.split('@')[0].rstrip('/')
                elements = self._find_elements(base_xpath)
                if elements:
                    # Get attribute name from xpath
                    attr = alt_xpath.split('@')[-1]
                    name = elements[0].get(attr)
        
        # Use default if no name found
        if not name:
            name = name_mapping.get('default', 'Model')
        
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
