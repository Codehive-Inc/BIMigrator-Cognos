"""Parser for extracting information from Tableau Workbook (.twb) files.

This module provides functionality to parse Tableau Workbook (.twb) files and extract
information needed to generate Power BI TMDL files. The main components are:

Classes:
    - TableauWorkbookParser: Main parser class that handles TWB file parsing

Usage:
    parser = TableauWorkbookParser('path/to/workbook.twb', config)
    data = parser.extract_all()

The parser extracts the following information:
    - Database name from:
        1. Datasource caption (<datasource caption='...'>) 
        2. Datasource name (<datasource name='...'>) if no caption
        3. Dashboard name (<dashboard name='...'>) if no datasource name
        4. Default to 'Model' if no names found
    - Tables from <relation> elements
    - Relationships from <relation> join information
    - Expressions from calculated fields
"""
import dataclasses
import sys
import xml.etree.ElementTree as Et
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.data_classes import PowerBiDatabase, PowerBiColumn, PowerBiTable
from src.common.helpers import load_config


def dataclass_to_dict(obj):
    """Convert dataclass to dictionary recursively."""
    if dataclasses.is_dataclass(obj):
        return {field.name: dataclass_to_dict(getattr(obj, field.name))
                for field in dataclasses.fields(obj)}
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    return obj


class TableauWorkbookParser:
    """Parser for Tableau Workbook (.twb) files."""

    def __init__(self, twb_path: str, config_path: str):
        """Initialize parser with TWB file path and config."""
        self.tree = Et.parse(twb_path)
        self.root = self.tree.getroot()
        self.namespaces = {'': self.root.tag.split('}')[0].strip('{')} if '}' in self.root.tag else {}
        self.twb_file = twb_path
        self.config = load_config(config_path)

    def extract_tables(self) -> list[PowerBiTable]:
        """Extract PowerBiTable objects from TWB file using configuration paths.

        The method extracts tables from datasource relations and columns.

        Returns:
            List[PowerBiTable]: List of extracted PowerBiTable objects
        """
        # Get configuration paths from PowerBiTable section in the YAML config
        table_config = self.config.get('PowerBiTable', {})
        column_config = self.config.get('PowerBiColumn', {})

        tables = []

        # Find all datasources using the source_xpath from config
        datasource_xpath = table_config.get('source_xpath', './/datasource')
        # Handle absolute paths correctly by modifying for ElementTree API
        if datasource_xpath.startswith('//'):
            # Handle absolute path
            datasource_xpath = '.' + datasource_xpath
        datasources = self.root.findall(datasource_xpath)

        for datasource in datasources:
            # Find named-connection and extract table name using the path from config
            table_name_path = table_config.get('pbi_name', {}).get('source_xpath', '')

            # Parse the path to extract the element path and attribute
            # Path format is like './/named-connection/@caption'
            if '@' in table_name_path:
                # Split at the @ symbol to get the path and attribute
                element_path, attr_name = table_name_path.rsplit('@', 1)
                # Remove trailing slash if present to make valid XPath
                if element_path.endswith('/'):
                    element_path = element_path[:-1]
            else:
                element_path = table_name_path
                attr_name = None

            # Find the element using the path
            if element_path.startswith('.//') or element_path.startswith('./'):
                # Relative path from current datasource
                element = datasource.find(element_path)
            else:
                # Absolute path
                element = self.root.find(element_path)

            if element is not None:
                # Get the value (either attribute or text content)
                if attr_name:
                    table_name = element.get(attr_name)
                else:
                    table_name = element.text

                if not table_name:
                    continue

                # Get connection information for source_name
                # Find the connection element (either in named-connection or directly)
                connection = None
                named_conn = datasource.find('.//named-connection')
                if named_conn is not None:
                    connection = named_conn.find('.//connection')

                if connection is not None:
                    # Extract source information
                    source_file = connection.get('filename', '')
                    source_type = connection.get('class', 'excel-direct')
                    source_name = f"{source_type}:{source_file}" if source_file else source_type
                else:
                    # Use table name as fallback if connection not found
                    source_name = table_name

                # Create PowerBiTable
                pbi_table = PowerBiTable(
                    pbi_name=table_name,
                    source_name=source_name,
                    description=table_name,
                    is_hidden=datasource.get('hidden', 'false').lower() == 'true'
                )

                # Track columns to avoid duplicates
                processed_columns = set()

                # Look for relations with columns
                relations = datasource.findall('.//relation')
                for relation in relations:
                    # Extract columns from the relation's columns element
                    columns_element = relation.find('.//columns')
                    if columns_element is not None:
                        column_elements = columns_element.findall('./column')

                        for column in column_elements:
                            # Get column attributes directly
                            col_name = column.get('name')
                            if not col_name or col_name in processed_columns:
                                continue

                            # Mark this column as processed
                            processed_columns.add(col_name)

                            datatype = column.get('datatype', 'string')
                            format_string = column.get('format')
                            is_hidden = column.get('hidden', 'false').lower() == 'true'
                            source_column = column.get('name')

                            # Map Tableau datatypes to Power BI datatypes if needed
                            tableau_to_pbi = {
                                'integer': 'int64',
                                'real': 'double',
                                'string': 'string',
                                'date': 'dateTime',
                                'datetime': 'dateTime',
                                'boolean': 'boolean'
                            }
                            pbi_datatype = tableau_to_pbi.get(datatype, 'string')

                            # Create PowerBiColumn
                            pbi_column = PowerBiColumn(
                                pbi_name=col_name,
                                pbi_datatype=pbi_datatype,
                                source_name=col_name,
                                is_hidden=is_hidden,
                                format_string=format_string,
                                source_column=source_column
                            )

                            # Add column to table
                            pbi_table.columns.append(pbi_column)

                # Add table to list
                tables.append(pbi_table)

        return tables

    def extract_database_info(self) -> PowerBiDatabase:
        """Extract database name from the TWB file using configuration paths.

        The method uses configuration paths to locate database name:
        1. Database name from configured datasource paths
        2. Fallback to default values if paths not found

        Returns:
            PowerBiDatabase: Database configuration with extracted name
        """
        # Get configuration paths
        datasource_paths = self.config.get('DataSourcePaths', {})

        # Extract database name using configured paths
        name = None

        # Try to get name from configured datasource paths
        for path in datasource_paths.get('name_paths', []):
            elements = self.root.findall(path)
            if elements:
                name = elements[0].text
                break

        # If no name found, try default paths
        if not name:
            datasources = self.root.findall('.//datasource')
            if datasources:
                datasource = datasources[0]
                name = datasource.get('caption') or datasource.get('name')

        # Use default if still no name
        if not name:
            name = self.config.get('DefaultDatabaseName', 'Model')

        return PowerBiDatabase(
            name=name,
            compatibility_level=self.config.get('CompatibilityLevel', 1550)
        )

    def extract_all(self) -> Dict[str, Any]:
        """Extract all required information from TWB file.
        
        Returns:
            Dictionary containing all extracted information organized by template type
        """
        values = {
            'PowerBiDatabase': self.extract_database_info(),
            'PowerBiTables': self.extract_tables(),
        }
        return {key: dataclass_to_dict(value) for key, value in values.items()}


def parse_workbook(twb_path: str, config_path: str) -> Dict[str, Any]:
    """Parse a Tableau Workbook file and extract all required information.
    
    Args:
        twb_path: Path to .twb file
        config_path: Path to config JSON or YAML
    
    Returns:
        Dictionary containing all extracted information organized by template type
    """
    parser = TableauWorkbookParser(twb_path, config_path)
    return parser.extract_all()


def main():
    """Command line interface for TWB parser."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Extract information from Tableau Workbook files')
    parser.add_argument('twb_file', help='Path to .twb file')
    parser.add_argument('--config', help='Path to config.yaml file.')
    parser.add_argument('--output', help='Output JSON file path')

    args = parser.parse_args()

    # Parse workbook
    data = parse_workbook(args.twb_file, args.config)
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
