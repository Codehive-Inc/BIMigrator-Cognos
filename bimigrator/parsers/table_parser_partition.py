"""Parser for extracting partition information from Tableau workbooks."""
import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiColumn, PowerBiPartition
from bimigrator.parsers.table_parser_base import TableParserBase


class PartitionParser(TableParserBase):
    """Parser for extracting partition information from Tableau workbooks."""

    def _extract_partition_info(
            self,
            ds_element: ET.Element,
            table_name: str,
            columns: Optional[List[PowerBiColumn]] = None
    ) -> List[PowerBiPartition]:
        """Extract partition information from a datasource element.
        
        Args:
            ds_element: Datasource element
            table_name: Name of the table
            columns: Optional list of PowerBiColumn objects with type information

        Returns:
            List of PowerBiPartition objects
        """
        partitions = []
        try:
            # Find the connection element
            connection = ds_element.find('.//connection')
            if connection is not None:
                # Log connection details
                conn_details = {
                    'class': connection.get('class'),
                    'server': connection.get('server'),
                    'database': connection.get('dbname'),
                    'schema': connection.get('schema'),
                    'username': connection.get('username'),
                    'port': connection.get('port'),
                    'authentication': connection.get('authentication'),
                    'table_name': table_name
                }
                
                # Save connection details to extracted folder
                os.makedirs(self.intermediate_dir, exist_ok=True)
                partitions_file = os.path.join(self.intermediate_dir, 'partitions.json')
                
                existing_data = {}
                if os.path.exists(partitions_file):
                    with open(partitions_file, 'r') as f:
                        existing_data = json.load(f)
                
                if 'connections' not in existing_data:
                    existing_data['connections'] = []
                existing_data['connections'].append(conn_details)
                
                with open(partitions_file, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                
                logger.info(f"Connection details for table {table_name}: {json.dumps(conn_details, indent=2)}")
                
                # Get the appropriate connection parser
                parser = self.connection_factory.get_parser(connection)

                # Find relation elements - try both with and without namespaces
                relations = connection.findall('.//relation')

                # If no relations found, try with wildcard namespace
                if not relations:
                    for element in connection.findall('.//*'):
                        if element.tag.endswith('relation'):
                            relations.append(element)

                # Process each relation and log
                for relation in relations:
                    logger.info(f"Processing relation for table {table_name}: {relation.attrib}")
                    new_partitions = parser.extract_partition_info(connection, relation, table_name, columns)
                    logger.info(f"Generated {len(new_partitions)} partitions for relation")
                    partitions.extend(new_partitions)

        except Exception as e:
            logger.error(f"Error extracting partition info: {str(e)}", exc_info=True)

        return partitions
