"""Parser for extracting partition information from Tableau workbooks."""
import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

from bimigrator.common.logging import logger
from bimigrator.config.data_classes import PowerBiColumn, PowerBiPartition
from bimigrator.parsers.table_parser_base import TableParserBase


class TablePartitionParser(TableParserBase):
    """Parser for extracting partition information from Tableau workbooks."""
    
    def extract_partitions_for_table(self, table_name: str) -> List[PowerBiPartition]:
        """Extract partition information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of PowerBiPartition objects
        """
        partitions = []
        try:
            # Find the main datasource element with connection information
            for ds_element in self.root.findall('.//datasource'):
                if ds_element.get('caption') == 'RO VIN Entry' or ds_element.get('name') == 'federated.1luf0dm0s4az7214qsvnz0flwlm6':
                    # This is the main federated datasource with connection information
                    connection = ds_element.find('.//connection')
                    if connection is not None:
                        # Find the named connection with the actual connection details
                        named_connection = None
                        named_connections = connection.find('.//named-connections')
                        if named_connections is not None:
                            # Get the first named connection
                            named_connection = named_connections.find('.//connection')
                        
                        # Use either the named connection or the main connection
                        conn = named_connection if named_connection is not None else connection
                        
                        # Create a partition for the table based on the connection
                        server = conn.get('server', '10.78.194.25')
                        schema = conn.get('schema', 'DBSRW_SYS')
                        service = conn.get('service', 'OPDBSRW')
                        
                        # Create M code expression for the partition
                        m_code = f"""
                let Source = Oracle.Database(Server = "{server}:1521 / {service}", [HierarchicalNavigation = true]), #"Naviguated to Schema" = Source{{[Schema = "{schema}",Kind = "Schema"]}}[Data], #"Filtered Rows" = Table.SelectRows(#"Naviguated to Schema", each true) in #"Filtered Rows"
                """
                        
                        # Create partition object
                        partition = PowerBiPartition(
                            name=table_name,
                            source_type="m",
                            expression=m_code.strip()
                        )
                        partitions.append(partition)
                        break
        except Exception as e:
            logger.error(f"Error extracting partitions for table {table_name}: {str(e)}", exc_info=True)
        
        return partitions

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
