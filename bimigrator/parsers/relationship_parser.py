"""Parser for extracting relationships from Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple

from bimigrator.config.data_classes import PowerBiRelationship
from bimigrator.parsers.base_parser import BaseParser


class RelationshipParser(BaseParser):
    """Parser for extracting relationships from Tableau workbooks."""

    def __init__(self, twb_path: str, config: Dict[str, Any], output_dir: str = 'output'):
        """Initialize the parser.
        
        Args:
            twb_path: Path to the input TWB file
            config: Configuration dictionary
        """
        super().__init__(twb_path, config, output_dir)
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
                table_name = self._get_sql_query_table_name(table_name)
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
        seen_relationships = set()  # Track unique relationships

        # Find all datasources
        datasources = self.root.findall('.//datasource')
        print(f'Debug: Found {len(datasources)} datasources')

        for ds_element in datasources:
            # Get datasource name
            ds_name = ds_element.get('name', '')
            print(f'Debug: Processing datasource: {ds_name}')

            try:
                # Find connection element
                connection = ds_element.find('.//connection')
                if connection is None:
                    continue

                # Find relation elements
                relations = connection.findall('.//relation')
                if not relations:
                    # Try with wildcard namespace
                    for element in connection.findall('.//*'):
                        if element.tag.endswith('relation'):
                            relations.append(element)

                # Process each relation
                for relation in relations:
                    print(f'Debug: Processing relation: {relation.attrib}')
                    
                    # Check for join clauses
                    join_clauses = relation.findall('.//clause[@type="join"]')
                    for join_clause in join_clauses:
                        equals_expr = join_clause.find('.//expression[@op="="]')
                        if equals_expr is not None:
                            # Get left and right expressions
                            left_expr = equals_expr.find('./expression[1]')
                            right_expr = equals_expr.find('./expression[2]')
                            
                            if left_expr is not None and right_expr is not None:
                                left_op = left_expr.get('op', '')
                                right_op = right_expr.get('op', '')
                                
                                # Extract table and column names
                                from_table = self._extract_table_name(left_op)
                                to_table = self._extract_table_name(right_op)
                                from_column = self._extract_column_name(left_op)
                                to_column = self._extract_column_name(right_op)
                                
                                if all([from_table, to_table, from_column, to_column]):
                                    # Create unique key for this relationship
                                    rel_key = f"{from_table}:{from_column}:{to_table}:{to_column}"
                                    
                                    # Only add if we haven't seen this relationship before
                                    if rel_key not in seen_relationships:
                                        seen_relationships.add(rel_key)
                                        
                                        # Create relationship object
                                        relationship = PowerBiRelationship(
                                            from_table=from_table,
                                            to_table=to_table,
                                            from_column=from_column,
                                            to_column=to_column,
                                            cardinality="manyToOne",  # Default to many-to-one
                                            cross_filter_behavior="oneWay",  # Default to one-way
                                            is_active=True
                                        )
                                        relationships.append(relationship)
                                        print(f'Debug: Found relationship: {from_table}.{from_column} -> {to_table}.{to_column}')

            except Exception as e:
                print(f'Error processing datasource {ds_name}: {str(e)}')
                continue

        # Save relationships to intermediate file
        if relationships:
            self.save_intermediate({'relationships': [r.__dict__ for r in relationships]}, 'relationships')
            print(f'Debug: Saved {len(relationships)} relationships')

        return relationships
