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
                        for key, value in conn.attrib.items():
                            conn_info['additional_properties'][key] = value
                        break
                        
        # Handle SQL queries in relations
        if relation_node.get('type') == 'text':
            sql_query = relation_node.text
            if sql_query:
                conn_info['sql_query'] = sql_query.strip().replace('&#13;', '\n').replace('&apos;', "'")
        elif relation_node.get('type') == 'table':
            conn_info['table'] = relation_node.get('name')
            
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
            partition = PowerBiPartition(
                name=table_name,
                expression=m_code,
                source_type='m',
                description=f"SQL partition for table {table_name}"
            )
            partitions.append(partition)
            
        return partitions
        
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
