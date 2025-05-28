"""Parser for extracting partition information from Tableau workbooks."""
import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Set

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
        processed_datasources: Set[str] = set()
        
        try:
            # Find all datasource elements
            for ds_element in self.root.findall('.//datasource'):
                ds_name = ds_element.get('name', '')
                ds_caption = ds_element.get('caption', '')
                
                # Skip already processed datasources
                if ds_name in processed_datasources:
                    continue
                processed_datasources.add(ds_name)
                
                # Log the datasource being processed
                logger.info(f"Processing datasource for partitions: {ds_caption or ds_name}")
                
                # Extract partition information for this datasource
                ds_partitions = self._extract_partition_info(ds_element, table_name)
                
                # Add partitions if any were found
                if ds_partitions:
                    partitions.extend(ds_partitions)
                    logger.info(f"Found {len(ds_partitions)} partitions for table {table_name} in datasource {ds_caption or ds_name}")
                
        except Exception as e:
            logger.error(f"Error extracting partitions for table {table_name}: {str(e)}", exc_info=True)
        
        # Log the total number of partitions found
        logger.info(f"Total partitions found for table {table_name}: {len(partitions)}")
        
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
                # Extract SQL queries from all relation elements
                sql_queries = self._extract_sql_queries(connection)
                
                # Log connection details with SQL queries
                conn_details = {
                    'class': connection.get('class'),
                    'server': connection.get('server'),
                    'database': connection.get('dbname'),
                    'schema': connection.get('schema'),
                    'username': connection.get('username'),
                    'port': connection.get('port'),
                    'authentication': connection.get('authentication'),
                    'table_name': table_name,
                    'sql_queries': sql_queries
                }
                
                # Save enhanced connection details to extracted folder
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
        
    def _extract_sql_queries(self, connection: ET.Element) -> List[Dict[str, str]]:
        """Extract SQL queries from all relation elements in a connection.
        
        Args:
            connection: Connection element
            
        Returns:
            List of dictionaries containing relation name and SQL query
        """
        sql_queries = []
        
        try:
            # Find all relation elements
            relations = []
            
            # Try direct relation elements
            direct_relations = connection.findall('.//relation')
            if direct_relations:
                relations.extend(direct_relations)
            
            # Try with wildcard namespace
            for element in connection.findall('.//*'):
                if element.tag.endswith('relation') and element not in relations:
                    relations.append(element)
            
            # Process each relation
            for relation in relations:
                relation_name = relation.get('name', '')
                relation_type = relation.get('type', '')
                
                # Extract SQL query if it's a text relation
                if relation_type == 'text' and relation.text:
                    sql_query = relation.text.strip()
                    # Clean up the SQL query
                    sql_query = sql_query.replace('&#13;', '\n').replace('&apos;', "'")
                    
                    sql_queries.append({
                        'name': relation_name,
                        'type': relation_type,
                        'sql_query': sql_query
                    })
                    logger.info(f"Extracted SQL query from relation {relation_name}")
                
                # Handle custom SQL queries in child elements
                custom_sql = relation.find('.//custom-sql')
                if custom_sql is not None and custom_sql.text:
                    sql_query = custom_sql.text.strip()
                    # Clean up the SQL query
                    sql_query = sql_query.replace('&#13;', '\n').replace('&apos;', "'")
                    
                    sql_queries.append({
                        'name': relation_name,
                        'type': 'custom-sql',
                        'sql_query': sql_query
                    })
                    logger.info(f"Extracted custom SQL query from relation {relation_name}")
        
        except Exception as e:
            logger.error(f"Error extracting SQL queries: {str(e)}", exc_info=True)
        
        return sql_queries
