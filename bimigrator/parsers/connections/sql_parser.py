"""Parser for SQL connections in Tableau workbooks."""
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

from bimigrator.parsers.connections.base_connection import BaseConnectionParser
from bimigrator.config.data_classes import PowerBiPartition, PowerBiColumn
from bimigrator.common.tableau_helpers import generate_m_code


class SQLConnectionParser(BaseConnectionParser):
    """Parser for SQL connections in Tableau workbooks."""

    def can_handle(self, connection_node: ET.Element) -> bool:
        """Check if this parser can handle the given connection.
        
        Args:
            connection_node: Connection element from Tableau workbook
            
        Returns:
            True if this is a SQL connection, False otherwise
        """
        # List of SQL-based connection classes
        sql_classes = {'sqlserver', 'mysql', 'postgresql', 'oracle', 'dremio', 'snowflake'}
        
        # Check direct connection
        if connection_node.get('class') in sql_classes:
            return True
            
        # Check federated connection
        if connection_node.get('class') == 'federated':
            # First check if there's a SQL connection inside
            for named_conn in connection_node.findall('.//named-connection'):
                conn = named_conn.find('.//connection')
                if conn is not None and conn.get('class') in sql_classes:
                    return True
            
            # If no SQL connection found but it's still federated, handle it anyway
            # This ensures we handle federated connections even if we can't identify the specific type
            return True
            
        return False
        
    def extract_partition_info(
        self,
        connection_node: ET.Element,
        relation_node: ET.Element,
        table_name: str,
        columns: Optional[List[PowerBiColumn]] = None
    ) -> List[PowerBiPartition]:
        """Extract partition information from SQL connection.
        
        Args:
            connection_node: Connection element
            relation_node: Relation element
            table_name: Name of the table
            columns: Optional list of PowerBiColumn objects with type information
            
        Returns:
            List of PowerBiPartition objects
        """
        partitions = []
        
        # Get connection class and info
        class_type = connection_node.get('class')
        conn_info = {
            'class_type': class_type,
            'server': connection_node.get('server'),
            'database': connection_node.get('dbname'),
            'db_schema': connection_node.get('schema'),
            'table': None,
            'sql_query': None,
            'filename': None,
            'additional_properties': {}
        }
        
        # Handle federated connections
        if class_type == 'federated':
            for named_conn in connection_node.findall('.//named-connection'):
                conn = named_conn.find('.//connection')
                if conn is not None:
                    conn_class = conn.get('class')
                    if conn_class:
                        conn_info['class_type'] = conn_class
                        conn_info['server'] = conn.get('server')
                        conn_info['database'] = conn.get('dbname')
                        conn_info['db_schema'] = conn.get('schema')
                        conn_info['filename'] = conn.get('filename')
                        for key, value in conn.attrib.items():
                            conn_info['additional_properties'][key] = value
                        break
        
        # Generate a unique key for the relation to use for deduplication
        relation_key = self._generate_relation_key(relation_node, conn_info)
        conn_info['relation_key'] = relation_key
                        
        # Handle SQL queries in relations
        if relation_node.get('type') == 'text':
            sql_query = relation_node.text
            if sql_query:
                # Clean up the SQL query
                cleaned_sql = sql_query.strip().replace('&#13;', '\n').replace('&apos;', "'")
                conn_info['sql_query'] = cleaned_sql
                
                # Add SQL query to description for better traceability
                conn_info['additional_properties']['sql_description'] = f"SQL Query: {cleaned_sql[:100]}..."
        elif relation_node.get('type') == 'table':
            conn_info['table'] = relation_node.get('name')
        
        # Check for custom SQL in child elements
        custom_sql = relation_node.find('.//custom-sql')
        if custom_sql is not None and custom_sql.text:
            cleaned_sql = custom_sql.text.strip().replace('&#13;', '\n').replace('&apos;', "'")
            conn_info['sql_query'] = cleaned_sql
            conn_info['additional_properties']['sql_description'] = f"Custom SQL: {cleaned_sql[:100]}..."
            
        # Add column information
        if columns:
            conn_info['additional_properties']['columns'] = [
                {
                    'name': col.source_name,
                    'datatype': col.pbi_datatype
                }
                for col in columns
            ]
            
        # Generate M code
        m_code = generate_m_code(connection_node, relation_node, self.config)
        if m_code:
            # Create a unique partition name based on table name and relation key
            partition_name = f"{table_name}_{relation_key}" if relation_key else table_name
            
            # Create the partition with the SQL query included in the description
            description = f"SQL partition for table {table_name}"
            if conn_info.get('sql_query'):
                # Add truncated SQL query to description (first 100 chars)
                sql_preview = conn_info['sql_query'][:100] + "..." if len(conn_info['sql_query']) > 100 else conn_info['sql_query']
                description += f"\nSQL Query: {sql_preview}"
            
            partition = PowerBiPartition(
                name=table_name,  # Keep the table name for display purposes
                expression=m_code,
                source_type='m',
                description=description,
                # Add metadata to help with deduplication
                metadata={
                    'relation_key': relation_key,
                    'connection_class': conn_info['class_type'],
                    'server': conn_info.get('server'),
                    'database': conn_info.get('database'),
                    'schema': conn_info.get('db_schema'),
                    'has_sql_query': 'true' if conn_info.get('sql_query') else 'false'
                }
            )
            partitions.append(partition)
            
        return partitions
        
    def _generate_relation_key(self, relation_node: ET.Element, conn_info: Dict[str, Any]) -> str:
        """Generate a unique key for a relation to use for deduplication.
        
        Args:
            relation_node: Relation element
            conn_info: Connection information dictionary
            
        Returns:
            A string key that uniquely identifies this relation
        """
        # Start with relation name if available
        key_parts = []
        relation_name = relation_node.get('name', '')
        if relation_name:
            key_parts.append(relation_name)
        
        # Add table name if available
        table_name = relation_node.get('table', '')
        if table_name:
            key_parts.append(table_name)
            
        # For SQL queries, use a hash of the query
        if relation_node.get('type') == 'text' and relation_node.text:
            sql_query = relation_node.text.strip().replace('&#13;', '\n').replace('&apos;', "'")
            # Use first 50 chars of SQL as part of the key
            if sql_query:
                sql_part = sql_query[:50].replace(' ', '').replace('\n', '')
                key_parts.append(f"sql_{sql_part}")
        
        # Add connection info if available
        if conn_info.get('server'):
            key_parts.append(conn_info['server'])
        if conn_info.get('database'):
            key_parts.append(conn_info['database'])
        if conn_info.get('db_schema'):
            key_parts.append(conn_info['db_schema'])
            
        # Join all parts with underscore
        if key_parts:
            return '_'.join(key_parts).replace(' ', '_').lower()
        
        # Fallback to a generic key
        return f"relation_{id(relation_node)}"
        
    def extract_columns(
        self,
        connection_node: ET.Element,
        relation_node: ET.Element,
        columns_yaml_config: Dict[str, Any]
    ) -> List[PowerBiColumn]:
        """Extract columns from SQL connection.
        
        Args:
            connection_node: Connection element
            relation_node: Relation element
            columns_yaml_config: YAML configuration for columns
            
        Returns:
            List of PowerBiColumn objects
        """
        columns = []
        seen_col_names = set()
        
        # Get metadata-record columns
        metadata_records = connection_node.findall('.//metadata-record[@class="column"]')
        for meta_col in metadata_records:
            # Get column name
            remote_name = meta_col.find('remote-name')
            local_name = meta_col.find('local-name')
            
            if remote_name is not None and remote_name.text:
                col_name = remote_name.text
            elif local_name is not None and local_name.text:
                local_name_text = local_name.text
                if local_name_text.startswith('[') and local_name_text.endswith(']'):
                    col_name = local_name_text[1:-1]
                else:
                    col_name = local_name_text
            else:
                col_name = meta_col.get('caption') or meta_col.get('name')
                
            if not col_name or col_name in seen_col_names:
                continue
                
            # Get datatype
            local_type = meta_col.find('local-type')
            remote_type = meta_col.find('remote-type')
            
            if local_type is not None and local_type.text:
                twb_datatype = local_type.text
            elif remote_type is not None and remote_type.text:
                # Map remote-type number to string datatype
                remote_type_num = remote_type.text.strip()
                if remote_type_num in ['129', '130']:  # VARCHAR, WSTR
                    twb_datatype = 'string'
                elif remote_type_num in ['5', '6', '131']:  # FLOAT, DOUBLE, NUMERIC
                    twb_datatype = 'real'
                elif remote_type_num in ['3', '4', '20']:  # INT, LONG, BIGINT
                    twb_datatype = 'integer'
                elif remote_type_num in ['7', '135']:  # DATE, TIMESTAMP
                    twb_datatype = 'datetime'
                elif remote_type_num in ['11']:  # BOOLEAN
                    twb_datatype = 'boolean'
                else:
                    twb_datatype = 'string'
            else:
                twb_datatype = meta_col.get('type', 'string')
                
            pbi_datatype = self._map_datatype(twb_datatype)
            
            # Create column
            column = PowerBiColumn(
                name=col_name,
                source_name=col_name,
                pbi_datatype=pbi_datatype
            )
            columns.append(column)
            seen_col_names.add(col_name)
            
        return columns
        
    def _map_datatype(self, tableau_type: str) -> str:
        """Map Tableau datatypes to Power BI datatypes.
        
        Args:
            tableau_type: Tableau datatype string
            
        Returns:
            Power BI datatype string
        """
        tableau_to_tmdl_datatypes = self.config.get('tableau_datatype_to_tmdl', {})
        if not tableau_type or not isinstance(tableau_type, str):
            return 'string'
            
        tableau_type = tableau_type.lower()
        return tableau_to_tmdl_datatypes.get(tableau_type, 'string')
        
    def get_relation_tables(self, connection_node: ET.Element) -> List[Dict[str, Any]]:
        """Extract all tables from a connection's relations.
        
        Args:
            connection_node: Connection element
            
        Returns:
            List of dictionaries containing table information
        """
        tables = []
        
        # Find all relation elements
        relations = []
        
        # Try direct relation elements
        direct_relations = connection_node.findall('.//relation')
        if direct_relations:
            relations.extend(direct_relations)
        
        # Try with wildcard namespace
        for element in connection_node.findall('.//*'):
            if element.tag.endswith('relation') and element not in relations:
                relations.append(element)
        
        # Process each relation
        for relation in relations:
            relation_name = relation.get('name', '')
            relation_type = relation.get('type', '')
            
            table_info = {
                'name': relation_name,
                'type': relation_type,
                'connection_class': connection_node.get('class'),
                'server': connection_node.get('server'),
                'database': connection_node.get('dbname'),
                'schema': connection_node.get('schema')
            }
            
            # Extract SQL query if it's a text relation
            if relation_type == 'text' and relation.text:
                sql_query = relation.text.strip().replace('&#13;', '\n').replace('&apos;', "'")
                table_info['sql_query'] = sql_query
            
            # Handle table references
            if relation_type == 'table':
                table_info['table_ref'] = relation.get('table', '')
            
            # Generate a unique key for deduplication
            relation_key = self._generate_relation_key(relation, table_info)
            table_info['relation_key'] = relation_key
            
            tables.append(table_info)
        
        return tables
