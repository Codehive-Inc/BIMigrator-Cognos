"""Parser for handling table relations and joins in Tableau workbooks."""
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

from bimigrator.common.logging import logger
from bimigrator.parsers.table_parser_base import TableParserBase


class TableRelationParser(TableParserBase):
    """Parser for handling table relations and joins in Tableau workbooks."""

    def _extract_nested_tables(self, join_element: ET.Element) -> List[ET.Element]:
        """Extract table relations from a join relation element.
        
        Args:
            join_element: The join relation element
            
        Returns:
            List of table relation elements
        """
        tables = []
        try:
            # Check if this is a join relation
            if join_element.get('type') == 'join':
                # Get clauses
                clauses = join_element.findall('.//clause')
                for clause in clauses:
                    # Extract expressions from clause
                    expressions = clause.findall('.//expression')
                    for expr in expressions:
                        # Look for table relations within expressions
                        relations = expr.findall('.//relation')
                        tables.extend(relations)
            else:
                # Single table relation
                tables.append(join_element)

        except Exception as e:
            logger.error(f"Error extracting nested tables: {str(e)}", exc_info=True)

        return tables

    def extract_table_relations(self, ds_element: ET.Element) -> List[ET.Element]:
        """Extract all table relations from a datasource element.
        
        Args:
            ds_element: The datasource element
            
        Returns:
            List of table relation elements
        """
        relations = []
        try:
            # Find the connection element
            connection = ds_element.find('.//connection')
            if connection is not None:
                # Handle federated datasources
                if connection.get('class') == 'federated':
                    # For federated datasources, try both encapsulated and non-encapsulated formats
                    relations.extend(connection.findall('.//relation'))
                    relations.extend(connection.findall('./_.fcp.ObjectModelEncapsulateLegacy.false...relation'))
                    relations.extend(connection.findall('./_.fcp.ObjectModelEncapsulateLegacy.true...relation'))
                else:
                    # For non-federated datasources, just look for regular relations
                    relations.extend(connection.findall('.//relation'))

                # Process any join relations to extract nested tables
                for relation in list(relations):  # Create a copy since we'll modify the list
                    if relation.get('type') == 'join':
                        # Remove the join relation and add its nested tables
                        relations.remove(relation)
                        nested_tables = self._extract_nested_tables(relation)
                        relations.extend(nested_tables)

        except Exception as e:
            logger.error(f"Error extracting table relations: {str(e)}", exc_info=True)

        return relations
