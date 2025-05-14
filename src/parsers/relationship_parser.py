"""Parser for extracting relationships from Tableau workbooks."""
from typing import Dict, Any, List, Tuple
import xml.etree.ElementTree as ET
from config.data_classes import PowerBiRelationship
from .base_parser import BaseParser
from pathlib import Path
from typing import Union
import uuid

class RelationshipParser(BaseParser):
    """Parser for extracting relationships from Tableau workbooks."""
    
    def __init__(self, twb_path: str, config: Dict[str, Any]):
        """Initialize the parser.
        
        Args:
            twb_path: Path to the input TWB file
            config: Configuration dictionary
        """
        super().__init__(twb_path, config)
        self.relationship_config = config.get('PowerBiRelationship', {})
    
    def _get_sql_query_table_name(self, query_name: str) -> str:
        """Get the actual table name for a SQL query table.
        
        Args:
            query_name: Name of the SQL query table (e.g. 'Custom SQL Query')
            
        Returns:
            Actual table name from the SQL query
        """
        # Find the SQL query element
        xpath = f"//relation[@name='{query_name}'][@type='text']"
        query_elements = self._find_elements(xpath)
        if query_elements:
            # Get the SQL query text
            query_text = query_elements[0].text or ''
            # Look for FROM clause
            from_parts = query_text.lower().split(' from ')
            if len(from_parts) > 1:
                # Get the table name after FROM
                table_parts = from_parts[1].strip().split()
                if table_parts:
                    # Remove any schema prefix and keep just the table name
                    table_name = table_parts[0].split('.')[-1]
                    return table_name
        return query_name
    
    def _extract_table_name(self, expr: str) -> str:
        """Extract table name from a join expression.
        
        Args:
            expr: Expression like '[Table].[Column]'
            
        Returns:
            Table name without brackets
        """
        if not expr:
            return ''
        parts = expr.split('.')  # Split [Table].[Column]
        if len(parts) >= 1:
            table_name = parts[0].strip('[]')
            # If it's a SQL query table, get the actual table name
            if table_name.startswith('Custom SQL Query'):
                return self._get_sql_query_table_name(table_name)
            return table_name
        return ''
    
    def _extract_column_name(self, expr: str) -> str:
        """Extract column name from a join expression.
        
        Args:
            expr: Expression like '[Table].[Column]'
            
        Returns:
            Column name without brackets
        """
        if not expr:
            return ''
        parts = expr.split('.')  # Split [Table].[Column]
        if len(parts) >= 2:
            return parts[1].strip('[]')
        return ''
    
    def _get_join_info(self, join_element: ET.Element) -> Tuple[str, str, str, str]:
        """Get table and column info from a join relation.
        
        Args:
            join_element: The join relation element
            
        Returns:
            Tuple of (from_table, to_table, from_column, to_column)
        """
        # Look for join clause with equals expression
        print('Debug: Looking for join clause with equals expression...')
        equals_expr = join_element.find('.//clause[@type="join"]/expression[@op="="]')
        if equals_expr is not None:
            # Get the left and right expressions
            left_expr = equals_expr.find('./expression[1]')
            right_expr = equals_expr.find('./expression[2]')
            
            if left_expr is not None and right_expr is not None:
                left_op = left_expr.get('op', '')
                right_op = right_expr.get('op', '')
                print(f'Debug: Found expressions - left: {left_op}, right: {right_op}')
                
                from_table = self._extract_table_name(left_op)
                to_table = self._extract_table_name(right_op)
                from_column = self._extract_column_name(left_op)
                to_column = self._extract_column_name(right_op)
                
                if all([from_table, to_table, from_column, to_column]):
                    result = (from_table, to_table, from_column, to_column)
                    print(f'Debug: Found join info from expressions: {result}')
                    return result
        
        # If no join clause found, try legacy format
        print('Debug: Trying legacy format...')
        relations = join_element.findall('./connection/relation')
        if len(relations) >= 2:
            from_relation = relations[0]
            to_relation = relations[1]
            
            result = (
                from_relation.get('name', ''),
                to_relation.get('name', ''),
                from_relation.get('key', ''),
                to_relation.get('key', '')
            )
            print(f'Debug: Found join info from legacy format: {result}')
            return result
        
        print('Debug: No join information found')
        return ('', '', '', '')
    
    def extract_relationships(self) -> List[PowerBiRelationship]:
        """Extract all relationships from the workbook.
        
        Returns:
            List of PowerBiRelationship objects
        """
        relationships = []
        
        # Find all join relations using config XPath
        xpath = self.relationship_config.get('source_xpath', '//datasources/datasource/relation[@type="join"]')
        print(f'Debug: Using XPath: {xpath}')
        join_elements = self._find_elements(xpath)
        print(f'Debug: Found {len(join_elements)} join elements')
        
        for join_element in join_elements:
            print(f'Debug: Processing join element: {join_element.tag}')
            # Get join information
            from_table, to_table, from_column, to_column = self._get_join_info(join_element)
            print(f'Debug: Join info - from: {from_table}.{from_column} -> to: {to_table}.{to_column}')
            
            # Skip if we're missing any required information
            if not all([from_table, to_table, from_column, to_column]):
                print('Debug: Missing required join information, skipping')
                continue
            
            # Get is_active value using configured XPath
            is_active = self._get_mapping_value(
                self.relationship_config.get('is_active', {}),
                join_element,
                True  # Default to True
            )
            
            # Get cardinality using configured rules
            cardinality = self._get_mapping_value(
                self.relationship_config.get('cardinality', {}),
                join_element,
                'one'  # Default to one
            )
            
            # Get cross filter behavior using configured value
            cross_filter = self._get_mapping_value(
                self.relationship_config.get('cross_filter_behavior', {}),
                join_element,
                'bothDirections'  # Default to bothDirections
            )
            
            # Create PowerBiRelationship object
            relationship = PowerBiRelationship(
                from_table=from_table,
                to_table=to_table,
                from_column=from_column,
                to_column=to_column,
                cardinality=cardinality,
                cross_filter_behavior=cross_filter,
                is_active=is_active
            )
            relationships.append(relationship)
        
        # Save intermediate data
        self.save_intermediate({'relationships': [r.__dict__ for r in relationships]}, 'relationships')
        
        return relationships
